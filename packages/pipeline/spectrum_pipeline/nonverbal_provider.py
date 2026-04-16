from __future__ import annotations

import re
from typing import Iterable

from spectrum_core.models import DiarizationSummary, EvidenceRef, NonverbalCue, ProsodyTrack, QualitySummary, WordTimestamp

LAUGH_PATTERN = re.compile(r"\b(?:ha){2,}\b|\b(?:haha|hehe|lol|lmao|laugh(?:ing)?)\b", re.IGNORECASE)
BACKCHANNEL_PATTERN = re.compile(r"^(?:yeah|yep|right|ok|okay|sure|mm+|mhm+|uh-huh|uh huh|hmm+)$", re.IGNORECASE)
SIGH_PATTERN = re.compile(r"\b(?:sigh|phew|whew|huh)\b", re.IGNORECASE)
COUGH_PATTERN = re.compile(r"\b(?:cough|ahem|clears throat)\b", re.IGNORECASE)


def _speaker_at_timestamp(diarization: DiarizationSummary, timestamp_ms: int) -> str | None:
    for segment in diarization.segments:
        if segment.start_ms <= timestamp_ms <= segment.end_ms:
            return segment.speaker_id
    return None


def _has_word_nearby(words: Iterable[WordTimestamp], timestamp_ms: int, *, window_ms: int = 240) -> bool:
    return any(word.start_ms - window_ms <= timestamp_ms <= word.end_ms + window_ms for word in words)


def detect_textual_vocal_cues(
    *,
    job_id: str,
    turns,
    words: list[WordTimestamp],
    diarization: DiarizationSummary,
    strong_diarization: bool,
    source_type: str,
) -> list[NonverbalCue]:
    cues: list[NonverbalCue] = []
    for turn in turns:
        text = turn.text.strip()
        lowered = text.lower()
        start_ms = turn.start_ms
        end_ms = turn.end_ms
        speaker_id = turn.speaker_id if strong_diarization else None
        explainability = ["textual_proxy"]

        if LAUGH_PATTERN.search(lowered):
            cues.append(
                NonverbalCue(
                    cue_id=f"{job_id}-laugh-{turn.turn_id}",
                    type="laugh",
                    family="vocal_sound",
                    label="laugh",
                    start_ms=start_ms,
                    end_ms=end_ms,
                    confidence=0.72 if strong_diarization else 0.52,
                    source="heuristic",
                    display_state="visible" if strong_diarization else "muted",
                    attribution_state="strong" if speaker_id else "unassigned",
                    speaker_id=speaker_id,
                    evidence_refs=[EvidenceRef(kind="turn", ref_id=turn.turn_id, label="textual_laughter_pattern")],
                    explainability_mask=list(explainability),
                )
            )
        if BACKCHANNEL_PATTERN.match(lowered) and (end_ms - start_ms) <= 1400:
            cues.append(
                NonverbalCue(
                    cue_id=f"{job_id}-backchannel-{turn.turn_id}",
                    type="backchannel",
                    family="conversational",
                    label="backchannel",
                    start_ms=start_ms,
                    end_ms=end_ms,
                    confidence=0.68 if strong_diarization else 0.5,
                    source="heuristic",
                    display_state="visible" if strong_diarization or source_type != "direct_audio_file" else "muted",
                    attribution_state="strong" if speaker_id else ("muted" if source_type != "direct_audio_file" else "unassigned"),
                    speaker_id=speaker_id,
                    evidence_refs=[EvidenceRef(kind="turn", ref_id=turn.turn_id, label="short_acknowledgement_turn")],
                    explainability_mask=list(explainability),
                )
            )
        if SIGH_PATTERN.search(lowered):
            cues.append(
                NonverbalCue(
                    cue_id=f"{job_id}-sigh-{turn.turn_id}",
                    type="breath_or_sigh",
                    family="vocal_sound",
                    label="breath or sigh",
                    start_ms=start_ms,
                    end_ms=end_ms,
                    confidence=0.64 if strong_diarization else 0.48,
                    source="heuristic",
                    display_state="muted" if source_type == "direct_audio_file" and not strong_diarization else "visible",
                    attribution_state="strong" if speaker_id else ("muted" if source_type != "direct_audio_file" else "unassigned"),
                    speaker_id=speaker_id,
                    evidence_refs=[EvidenceRef(kind="turn", ref_id=turn.turn_id, label="textual_sigh_pattern")],
                    explainability_mask=list(explainability),
                )
            )
        if COUGH_PATTERN.search(lowered):
            cues.append(
                NonverbalCue(
                    cue_id=f"{job_id}-cough-{turn.turn_id}",
                    type="cough_or_throat_clear",
                    family="vocal_sound",
                    label="cough or throat clear",
                    start_ms=start_ms,
                    end_ms=end_ms,
                    confidence=0.66 if strong_diarization else 0.48,
                    source="heuristic",
                    display_state="muted" if source_type == "direct_audio_file" and not strong_diarization else "visible",
                    attribution_state="strong" if speaker_id else ("muted" if source_type != "direct_audio_file" else "unassigned"),
                    speaker_id=speaker_id,
                    evidence_refs=[EvidenceRef(kind="turn", ref_id=turn.turn_id, label="textual_cough_pattern")],
                    explainability_mask=list(explainability),
                )
            )
    return cues


def detect_energy_vocal_cues(
    *,
    job_id: str,
    prosody_tracks: list[ProsodyTrack],
    words: list[WordTimestamp],
    diarization: DiarizationSummary,
    strong_diarization: bool,
    quality: QualitySummary,
    source_type: str,
) -> list[NonverbalCue]:
    cues: list[NonverbalCue] = []
    energy_track = next((track for track in prosody_tracks if track.key == "energy_rms"), None)
    if not energy_track:
        return cues

    last_burst_ms = -10_000
    for previous, current in zip(energy_track.samples, energy_track.samples[1:]):
        if current.timestamp_ms - last_burst_ms < 700:
            continue
        if current.value <= max(previous.value * 1.65, 0.09):
            continue
        if _has_word_nearby(words, current.timestamp_ms):
            continue

        speaker_id = _speaker_at_timestamp(diarization, current.timestamp_ms) if strong_diarization else None
        explainability = ["heuristic_vocal_burst"]
        display_state = "visible" if strong_diarization or source_type != "direct_audio_file" else "muted"
        confidence = 0.62 if strong_diarization else 0.46
        cue_type = "vocal_burst"
        cue_label = "vocal burst"

        if quality.avg_snr_db is not None and quality.avg_snr_db < 10:
            confidence = max(0.38, confidence - 0.08)
            explainability.append("low_snr")
        if previous.value < 0.03 and current.value > 0.12:
            cue_type = "cough_or_throat_clear"
            cue_label = "cough or throat clear"
            explainability.append("energy_transient")

        cues.append(
            NonverbalCue(
                cue_id=f"{job_id}-{cue_type}-{current.timestamp_ms}",
                type=cue_type,
                family="vocal_sound",
                label=cue_label,
                start_ms=max(0, current.timestamp_ms - 120),
                end_ms=current.timestamp_ms + 180,
                confidence=confidence,
                source="heuristic",
                display_state=display_state,
                attribution_state="strong" if speaker_id else ("muted" if source_type != "direct_audio_file" else "unassigned"),
                speaker_id=speaker_id,
                evidence_refs=[EvidenceRef(kind="prosody_track", ref_id="energy_rms", label="Energy transient")],
                explainability_mask=sorted(set(explainability)),
            )
        )
        last_burst_ms = current.timestamp_ms
    return cues
