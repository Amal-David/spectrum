from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spectrum_core.models import DiarizationSummary, EvidenceRef, NonverbalCue, ProsodyTrack, QualitySummary, WordTimestamp


def load_acoustic_cue_cache(cache_path: Path) -> tuple[str, list[NonverbalCue]] | None:
    if not cache_path.exists():
        return None
    try:
        payload = json.loads(cache_path.read_text())
    except json.JSONDecodeError:
        return None
    provider_key = str(payload.get("provider_key") or "")
    if not provider_key:
        return None
    return provider_key, [NonverbalCue.model_validate(item) for item in payload.get("cues", [])]


def save_acoustic_cue_cache(cache_path: Path, provider_key: str, cues: list[NonverbalCue]) -> None:
    cache_path.write_text(
        json.dumps(
            {
                "provider_key": provider_key,
                "cues": [cue.model_dump(mode="json") for cue in cues],
            },
            indent=2,
        )
        + "\n"
    )


def _speaker_at_timestamp(diarization: DiarizationSummary, timestamp_ms: int) -> str | None:
    for segment in diarization.segments:
        if segment.start_ms <= timestamp_ms <= segment.end_ms and segment.confidence >= 0.7:
            return segment.speaker_id
    return None


def _has_word_nearby(words: list[WordTimestamp], start_ms: int, end_ms: int, *, window_ms: int = 200) -> bool:
    return any(word.start_ms - window_ms <= end_ms and word.end_ms + window_ms >= start_ms for word in words)


def _cluster_energy_samples(samples: list[tuple[int, float]], *, threshold: float, gap_ms: int = 320) -> list[list[tuple[int, float]]]:
    clusters: list[list[tuple[int, float]]] = []
    current: list[tuple[int, float]] = []
    for timestamp_ms, value in samples:
        if value < threshold:
            continue
        if current and timestamp_ms - current[-1][0] > gap_ms:
            clusters.append(current)
            current = []
        current.append((timestamp_ms, value))
    if current:
        clusters.append(current)
    return clusters


def detect_acoustic_vocal_cues(
    *,
    job_id: str,
    prosody_tracks: list[ProsodyTrack],
    words: list[WordTimestamp],
    diarization: DiarizationSummary,
    quality: QualitySummary,
    source_type: str,
    provider_key: str,
    model_backed: bool,
) -> list[NonverbalCue]:
    energy_track = next((track for track in prosody_tracks if track.key == "energy_rms"), None)
    pitch_track = next((track for track in prosody_tracks if track.key == "pitch_hz"), None)
    if not energy_track or not energy_track.samples:
        return []

    strong_diarization = diarization.readiness_state == "ready"
    pitch_lookup = {sample.timestamp_ms: sample.value for sample in pitch_track.samples} if pitch_track else {}
    threshold = 0.11 if model_backed else 0.13
    clusters = _cluster_energy_samples([(sample.timestamp_ms, sample.value) for sample in energy_track.samples], threshold=threshold)
    cues: list[NonverbalCue] = []
    last_cue_end = -10_000
    for index, cluster in enumerate(clusters):
        start_ms = max(0, cluster[0][0] - 90)
        end_ms = cluster[-1][0] + 160
        if start_ms - last_cue_end < 420:
            continue
        if _has_word_nearby(words, start_ms, end_ms):
            continue

        duration_ms = max(120, end_ms - start_ms)
        peak = max(value for _, value in cluster)
        pitch_values = [pitch_lookup.get(timestamp_ms, 0.0) for timestamp_ms, _ in cluster if pitch_lookup.get(timestamp_ms)]
        pitch_span = (max(pitch_values) - min(pitch_values)) if len(pitch_values) > 1 else 0.0

        cue_type = "vocal_burst"
        cue_label = "vocal burst"
        explainability = ["acoustic_proxy"]
        if duration_ms >= 360 and len(cluster) >= 3 and pitch_span >= 45:
            cue_type = "laugh"
            cue_label = "laugh"
            explainability.append("clustered_bursts")
        elif duration_ms >= 520 and peak < 0.22:
            cue_type = "breath_or_sigh"
            cue_label = "breath or sigh"
            explainability.append("long_low_energy_burst")
        elif duration_ms <= 300 and peak >= 0.2:
            cue_type = "cough_or_throat_clear"
            cue_label = "cough or throat clear"
            explainability.append("sharp_transient")

        confidence = 0.74 if model_backed else 0.56
        if quality.avg_snr_db is not None and quality.avg_snr_db < 10:
            confidence = max(0.4, confidence - 0.1)
            explainability.append("low_snr")
        if quality.noise_ratio > 0.35:
            confidence = max(0.38, confidence - 0.08)
            explainability.append("high_noise_ratio")

        speaker_id = _speaker_at_timestamp(diarization, cluster[0][0]) if strong_diarization else None
        if speaker_id:
            attribution_state = "strong"
            display_state = "visible"
        elif source_type == "direct_audio_file":
            attribution_state = "unassigned"
            display_state = "muted"
        else:
            attribution_state = "muted"
            display_state = "visible"

        cues.append(
            NonverbalCue(
                cue_id=f"{job_id}-{cue_type}-acoustic-{index}",
                type=cue_type,
                family="vocal_sound",
                label=cue_label,
                start_ms=start_ms,
                end_ms=end_ms,
                confidence=confidence,
                source="model" if model_backed else "heuristic",
                display_state=display_state,
                attribution_state=attribution_state,
                speaker_id=speaker_id,
                evidence_refs=[EvidenceRef(kind="prosody_track", ref_id="energy_rms", label="Acoustic burst")],
                explainability_mask=sorted(set(explainability + ([provider_key] if model_backed else []))),
            )
        )
        last_cue_end = end_ms
    return cues
