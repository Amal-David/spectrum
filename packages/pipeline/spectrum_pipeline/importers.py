from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path
from typing import Any

from spectrum_core.constants import DEMO_PACK_PATH, REPO_ROOT
from spectrum_core.datasets import list_dataset_records, list_materialized_records
from spectrum_core.models import (
    ArtifactPaths,
    DatasetReference,
    Diagnostics,
    EventModel,
    EvidenceRef,
    QualitySummary,
    QuestionAnalyticsRow,
    SessionBundle,
    SessionResult,
    SpeakerSummary,
    SpectrogramArtifact,
    TurnModel,
    WaveformArtifact,
)
from spectrum_core.registry import build_adapter_inventory

from .service import (
    ProcessSessionOptions,
    SessionStore,
    build_content,
    build_diarization,
    build_environment,
    build_metrics,
    build_nonverbal_cues,
    build_profile,
    build_speaker_role_summary,
    build_session_bundle,
    build_signals,
    build_stage_status,
    build_timeline_tracks,
    create_session_result,
    apply_speaker_roles,
    persist_session_artifacts,
)

DEMO_PACK_ROOT = "voice_analytics_demo_pack"
CURATED_DATASET_IDS = [
    "indic_audio_natural_conversations_sample",
    "meld",
    "voxconverse",
    "podcast_fillers_processed",
    "ami_corpus",
    "ravdess_speech_16k",
]


def import_demo_pack(zip_path: Path = DEMO_PACK_PATH) -> list[SessionBundle]:
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)

    store = SessionStore()
    sessions: list[dict[str, Any]] = []
    speakers_by_session: dict[str, list[SpeakerSummary]] = {}
    turns_by_session: dict[str, list[TurnModel]] = {}
    events_by_session: dict[str, list[EventModel]] = {}
    questions_by_session: dict[str, list[QuestionAnalyticsRow]] = {}

    with zipfile.ZipFile(zip_path) as archive:
        sessions = json.loads(_read_zip_text(archive, f"{DEMO_PACK_ROOT}/data/sessions.json"))

        for row in _read_zip_csv(archive, f"{DEMO_PACK_ROOT}/data/speakers.csv"):
            speakers_by_session.setdefault(row["session_id"], []).append(
                SpeakerSummary(
                    speaker_id=row["speaker_id"],
                    role=row["role"],
                    talk_ratio=float(row["talk_ratio"]),
                    avg_turn_ms=float(row["avg_turn_ms"]),
                    interruption_count=int(row["interruptions"]),
                    overlap_ms=0.0,
                    wpm=float(row["wpm"]),
                )
            )

        for row in _read_zip_csv(archive, f"{DEMO_PACK_ROOT}/data/turns.csv"):
            turns_by_session.setdefault(row["session_id"], []).append(
                TurnModel(
                    turn_id=row["turn_id"],
                    speaker_id=row["speaker_id"],
                    start_ms=int(float(row["start_ms"])),
                    end_ms=int(float(row["end_ms"])),
                    text=row["text"],
                    response_latency_ms=int(float(row["response_latency_ms"])) if row["response_latency_ms"] else None,
                    filler_count=int(row["fillers"]),
                    uncertainty_markers=int(row["uncertainty_markers"]),
                    word_count=len(row["text"].split()),
                    confidence=0.88,
                    source="demo_pack_zip",
                    rms_energy=float(row["rms_energy"]),
                    pitch_variance=float(row["pitch_variance"]),
                    noise_ratio=float(row["noise_ratio"]),
                    speech_rate_wpm=float(row["speech_rate_wpm"]),
                    section=row["section"],
                )
            )

        for row in _read_zip_csv(archive, f"{DEMO_PACK_ROOT}/data/events.csv"):
            begin_ms = int(float(row["time_ms"]))
            duration_ms = int(float(row["duration_ms"])) if row["duration_ms"] else 0
            events_by_session.setdefault(row["session_id"], []).append(
                EventModel(
                    event_id=row["event_id"],
                    type=row["type"],
                    begin_ms=begin_ms,
                    end_ms=begin_ms + duration_ms,
                    speaker_ids=[row["speaker_id"]] if row["speaker_id"] else [],
                    severity=_severity_from_text(row["severity"]),
                    confidence=0.83,
                    evidence_refs=[EvidenceRef(kind="speaker", ref_id=row["speaker_id"], label=row["label"])] if row["speaker_id"] else [],
                    detail=row["label"],
                    label=row["label"],
                )
            )

        for row in _read_zip_csv(archive, f"{DEMO_PACK_ROOT}/data/questions.csv"):
            questions_by_session.setdefault(row["session_id"], []).append(
                QuestionAnalyticsRow(
                    question_id=row["question_id"],
                    question_text=row["question_text"],
                    question_turn_id=row["question_turn_id"],
                    answer_turn_id=row["answer_turn_id"],
                    response_latency_ms=int(float(row["response_latency_ms"])),
                    answer_duration_ms=int(float(row["answer_duration_ms"])),
                    directness_score=int(row["directness_score"]),
                    hesitation_score=int(row["hesitation_score"]),
                    affect_tag=row["affect_tag"],
                    evidence_refs=[
                        EvidenceRef(kind="turn", ref_id=row["question_turn_id"]),
                        EvidenceRef(kind="turn", ref_id=row["answer_turn_id"]),
                    ],
                )
            )

    adapters = build_adapter_inventory()
    imported: list[SessionBundle] = []
    for session_row in sessions:
        job_id = session_row["session_id"]
        metadata = {
            "title": session_row["title"],
            "session_type": session_row["session_type"],
            "language_hint": session_row["language"],
            "region": session_row["region"],
            "environment_primary": session_row["environment_primary"],
            "source_type": "demo_pack_zip",
            "dataset_id": "voice_analytics_demo_pack",
            "dataset_title": "Voice Analytics Demo Pack",
            "access_type": "local_synthetic",
        }
        quality = QualitySummary(
            speech_ratio=0.78,
            noise_score=round(float(session_row["quality_overview"]["noise_ratio"]), 3),
            noise_ratio=round(float(session_row["quality_overview"]["noise_ratio"]), 3),
            avg_snr_db=float(session_row["quality_overview"]["avg_snr_db"]),
            clipping_ratio=0.0,
            vad_fp_count=int(session_row["quality_overview"]["vad_fp_count"]),
            vad_fn_count=int(session_row["quality_overview"]["vad_fn_count"]),
            noisy_segment_count=len(events_by_session.get(job_id, [])),
            is_usable=float(session_row["quality_overview"]["avg_snr_db"]) >= 10,
            warning_flags=["demo_pack_synthetic"],
        )
        turns = turns_by_session.get(job_id, [])
        transcript = " ".join(turn.text for turn in turns).strip()
        speakers = speakers_by_session.get(job_id, [])
        events = events_by_session.get(job_id, [])
        questions = questions_by_session.get(job_id, [])
        profile, profile_display, profile_coverage, profile_provider_decision = build_profile(
            "conversation_analytics",
            metadata,
            transcript,
            quality,
            speakers,
            ProcessSessionOptions(metadata=metadata),
        )
        content = build_content(transcript, turns, metadata, quality, events, questions)
        environment = build_environment(metadata, quality, events, session_row["duration_ms"] / 1000)
        diarization, diarization_provider = build_diarization(job_id, Path("."), metadata, turns, adapters)
        speaker_roles = build_speaker_role_summary(speakers, turns, metadata)
        speakers, turns = apply_speaker_roles(speakers, turns, speaker_roles)
        spectrogram = SpectrogramArtifact(readiness_state="fallback", notes=["synthetic_session_has_no_rendered_spectrogram"])
        prosody_tracks: list[Any] = []
        nonverbal_cues = build_nonverbal_cues(
            job_id,
            metadata,
            diarization,
            prosody_tracks,
            turns,
            questions,
            quality,
            words=content.words,
            events=events,
        )
        timeline_tracks = build_timeline_tracks(diarization, content, turns, questions, nonverbal_cues, events)
        signals = build_signals(quality, speakers, turns, events, questions, content, speaker_roles)
        diagnostics = Diagnostics(
            adapters=adapters,
            confidence_caveats=["demo_pack_synthetic"],
            degraded_reasons=[],
            provider_decisions=[diarization_provider, profile_provider_decision],
            fallback_logic=["synthetic_session_import"],
        )
        source = DatasetReference(
            dataset_id="voice_analytics_demo_pack",
            title="Voice Analytics Demo Pack",
            access_type="local_synthetic",
            reference_label=session_row["session_id"],
            metadata={"title": session_row["title"]},
        )
        artifacts = ArtifactPaths(
            result_path=str(REPO_ROOT / "runs" / job_id / "result.json"),
            timeline_path=str(REPO_ROOT / "runs" / job_id / "timeline.json"),
            quality_path=str(REPO_ROOT / "runs" / job_id / "quality.json"),
            events_path=str(REPO_ROOT / "runs" / job_id / "events.json"),
            questions_path=str(REPO_ROOT / "runs" / job_id / "questions.json"),
            environment_path=str(REPO_ROOT / "runs" / job_id / "environment.json"),
            signals_path=str(REPO_ROOT / "runs" / job_id / "signals.json"),
            profile_path=str(REPO_ROOT / "runs" / job_id / "profile.json"),
            transcript_words_path=str(REPO_ROOT / "runs" / job_id / "transcript.words.json"),
            transcript_sentences_path=str(REPO_ROOT / "runs" / job_id / "transcript.sentences.json"),
            transcript_tokens_path=str(REPO_ROOT / "runs" / job_id / "transcript.tokens.json"),
            bundle_path=str(REPO_ROOT / "runs" / job_id / "bundle.json"),
        )
        result = SessionResult(
            job_id=job_id,
            analysis_mode="conversation_analytics",
            duration_sec=round(session_row["duration_ms"] / 1000, 3),
            speaker_count=session_row["speaker_count"],
            transcript=transcript,
            quality=quality,
            profile=profile,
            metrics=build_metrics(session_row["duration_ms"] / 1000, transcript, quality, speakers, turns, events, questions),
            speakers=speakers,
            turns=turns,
            events=events,
            diagnostics=diagnostics,
            source=source,
            artifacts=artifacts,
        )
        waveform = WaveformArtifact(duration_ms=int(session_row["duration_ms"]))
        bundle = build_session_bundle(
            result,
            session_title=session_row["title"],
            session_type=session_row["session_type"],
            language=session_row["language"],
            region=session_row["region"],
            call_channel="synthetic_call",
            source_type="demo_pack_zip",
            environment=environment,
            profile_display=profile_display,
            profile_coverage=profile_coverage,
            speaker_roles=speaker_roles,
            diarization=diarization,
            waveform=waveform,
            spectrogram=spectrogram,
            prosody_tracks=prosody_tracks,
            nonverbal_cues=nonverbal_cues,
            timeline_tracks=timeline_tracks,
            content=content,
            questions=questions,
            signals=signals,
            stage_status=build_stage_status(
                artifacts,
                diagnostics,
                quality,
                environment,
                profile_display,
                profile_coverage,
                speaker_roles,
                content,
                questions,
                signals,
                diarization,
                waveform,
                spectrogram,
                prosody_tracks,
                nonverbal_cues,
                timeline_tracks,
            ),
            readiness_tier="full",
        )
        persist_session_artifacts(
            job_id,
            metadata,
            quality,
            profile_display,
            profile_coverage,
            diarization,
            waveform,
            spectrogram,
            prosody_tracks,
            nonverbal_cues,
            timeline_tracks,
            content,
            questions,
            environment,
            signals,
            speaker_roles,
            result,
            bundle,
        )
        store.seed_session(job_id, "conversation_analytics", metadata=metadata)
        store.set_completed(job_id, Path("runs") / job_id / "result.json")
        imported.append(bundle)

    return imported


def import_materialized_dataset_samples(
    dataset_ids: list[str] | None = None,
    *,
    samples_per_dataset: int = 2,
) -> list[SessionResult]:
    dataset_lookup = {record["id"]: record for record in list_dataset_records()}
    store = SessionStore()
    imported: list[SessionResult] = []
    for dataset_id in dataset_ids or CURATED_DATASET_IDS:
        dataset_record = dataset_lookup.get(dataset_id)
        if not dataset_record or dataset_record.get("health_status") != "ready":
            continue
        if dataset_id == "meld":
            imported.extend(import_meld_dataset_samples(samples_per_dataset=samples_per_dataset))
            continue
        rows = [row for row in list_materialized_records(dataset_id) if row.get("absolute_output_path")]
        for index, row in enumerate(rows[:samples_per_dataset]):
            absolute_path = Path(row["absolute_output_path"])
            if not absolute_path.exists():
                continue
            job_id = f"{dataset_id}-sample-{index + 1:02d}"
            analysis_mode = _analysis_mode_for_dataset(dataset_id)
            metadata = {
                "title": f"{dataset_record['title']} sample {index + 1}",
                "dataset_id": dataset_id,
                "dataset_title": dataset_record["title"],
                "access_type": dataset_record.get("access_type"),
                "language_hint": row.get("language") or "unknown",
                "reference_label": absolute_path.name,
                "source_type": "materialized_audio_dataset",
                "split": row.get("source_parquet"),
                "speaker_hints": {row.get("speaker_id") or "speaker_0": {"role": row.get("speaker")}},
                "session_type": _session_type_for_dataset(dataset_id),
                "call_channel": "downloaded_dataset",
            }
            store.seed_session(job_id, analysis_mode, metadata=metadata)
            store.save_upload(job_id, absolute_path.name, absolute_path)
            store.set_processing(job_id)
            result = create_session_result(
                job_id=job_id,
                analysis_mode=analysis_mode,
                original_path=absolute_path,
                options=ProcessSessionOptions(metadata=metadata),
            )
            store.set_completed(job_id, Path("runs") / job_id / "result.json")
            imported.append(result)
    return imported


def import_meld_dataset_samples(*, samples_per_dataset: int = 2) -> list[SessionResult]:
    dataset_lookup = {record["id"]: record for record in list_dataset_records()}
    dataset_record = dataset_lookup.get("meld")
    if not dataset_record:
        return []

    label_files = [
        REPO_ROOT / "data" / "raw" / "meld" / "labels" / "train_sent_emo.csv",
        REPO_ROOT / "data" / "raw" / "meld" / "labels" / "dev_sent_emo.csv",
    ]
    store = SessionStore()
    selected_rows: list[tuple[str, dict[str, str]]] = []
    for split_name, label_path in (("train", label_files[0]), ("dev", label_files[1])):
        if not label_path.exists():
            continue
        with label_path.open() as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                selected_rows.append((split_name, row))
                if len(selected_rows) >= samples_per_dataset:
                    break
        if len(selected_rows) >= samples_per_dataset:
            break

    imported: list[SessionResult] = []
    for index, (split_name, row) in enumerate(selected_rows):
        media_path = REPO_ROOT / "data" / "raw" / "meld" / "MELD.Raw" / f"{split_name}_splits" / f"dia{row['Dialogue_ID']}_utt{row['Utterance_ID']}.mp4"
        if not media_path.exists():
            continue
        speaker_id = row["Speaker"].strip().lower().replace(" ", "_") or "speaker_0"
        job_id = f"meld-sample-{index + 1:02d}"
        metadata = {
            "title": f"MELD dialogue {row['Dialogue_ID']} utterance {row['Utterance_ID']}",
            "dataset_id": "meld",
            "dataset_title": dataset_record["title"],
            "access_type": dataset_record.get("access_type"),
            "language_hint": "english",
            "reference_label": row["Emotion"],
            "source_type": "materialized_audio_dataset",
            "split": split_name,
            "session_type": "emotion_benchmark",
            "call_channel": "benchmark_media",
            "transcript_hint": row["Utterance"],
            "speaker_segments": [
                {
                    "turn_id": f"{job_id}-turn-0",
                    "speaker_id": speaker_id,
                    "start_ms": _meld_time_to_ms(row["StartTime"]),
                    "end_ms": _meld_time_to_ms(row["EndTime"]),
                    "text": row["Utterance"],
                    "source": "meld_benchmark",
                    "confidence": 0.96,
                }
            ],
            "speaker_roles": {speaker_id: row["Speaker"]},
            "sentence_emotion_labels": [
                {
                    "benchmark_id": f"meld:{row['Dialogue_ID']}:{row['Utterance_ID']}",
                    "text": row["Utterance"],
                    "emotion_label": row["Emotion"],
                    "sentiment_label": row["Sentiment"],
                    "start_ms": _meld_time_to_ms(row["StartTime"]),
                    "end_ms": _meld_time_to_ms(row["EndTime"]),
                    "confidence": 0.99,
                }
            ],
        }
        store.seed_session(job_id, "full", metadata=metadata)
        store.save_upload(job_id, media_path.name, media_path)
        store.set_processing(job_id)
        result = create_session_result(
            job_id=job_id,
            analysis_mode="full",
            original_path=media_path,
            options=ProcessSessionOptions(metadata=metadata),
        )
        store.set_completed(job_id, Path("runs") / job_id / "result.json")
        imported.append(result)
    return imported


def adapter_coverage() -> list[str]:
    return [adapter.key for adapter in build_adapter_inventory() if adapter.available]


def _read_zip_text(archive: zipfile.ZipFile, member: str) -> str:
    return archive.read(member).decode("utf-8")


def _read_zip_csv(archive: zipfile.ZipFile, member: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(_read_zip_text(archive, member))))


def _analysis_mode_for_dataset(dataset_id: str) -> str:
    if dataset_id == "ravdess_speech_16k":
        return "voice_profile"
    if dataset_id in {"voxconverse", "indic_audio_natural_conversations_sample"}:
        return "conversation_analytics"
    return "full"


def _session_type_for_dataset(dataset_id: str) -> str:
    if dataset_id == "podcast_fillers_processed":
        return "podcast_clip"
    if dataset_id == "voxconverse":
        return "speaker_diarization"
    if dataset_id == "indic_audio_natural_conversations_sample":
        return "natural_conversation"
    return "analysis"


def _severity_from_text(value: str) -> str:
    lowered = value.lower()
    if lowered == "high":
        return "critical"
    if lowered == "medium":
        return "warning"
    return "info"


def _meld_time_to_ms(value: str) -> int:
    time_part, milli_part = value.split(",")
    hours, minutes, seconds = [int(part) for part in time_part.split(":")]
    return ((hours * 3600 + minutes * 60 + seconds) * 1000) + int(milli_part)
