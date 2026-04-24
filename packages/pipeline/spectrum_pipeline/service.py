from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import subprocess
import wave
from array import array
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any, Callable
from uuid import uuid4

from spectrum_core.constants import RUNS_DIR
from spectrum_core.models import (
    AnalysisMode,
    ArtifactPaths,
    ConversationReport,
    ContentSummary,
    DatasetReference,
    DiarizationSegment,
    DiarizationSummary,
    DisplayState,
    Diagnostics,
    EnvironmentSummary,
    EvidenceClass,
    EventModel,
    EvidenceRef,
    JobActivityEntry,
    LabelPrediction,
    LangMixPrediction,
    MetricSummary,
    NonverbalCue,
    PredictionSource,
    ProviderDecision,
    ProfileField,
    ProfileCoverageSummary,
    ProfileSummary,
    ProsodyPoint,
    ProsodyTrack,
    QualitySummary,
    QuestionAnalyticsRow,
    ReadinessTier,
    SentenceEmotionSpan,
    SessionBundle,
    SessionDescriptor,
    SessionJobStatus,
    SessionRecord,
    SessionResult,
    SignalCard,
    SpeakerRole,
    SpeakerRoleAssignment,
    SpeakerRoleSummary,
    SpectrogramArtifact,
    SpeakerSummary,
    StageStatus,
    StageState,
    TokenEmotionSpan,
    TimeWindow,
    TimelineTrack,
    TimelineTrackItem,
    TranscriptViewSummary,
    TurnModel,
    WaveformArtifact,
    WordTimestamp,
)
from spectrum_core.registry import build_adapter_inventory
from .acoustic_cue_provider import detect_acoustic_vocal_cues, load_acoustic_cue_cache, save_acoustic_cue_cache
from .alignment_provider import align_words_with_whisperx, load_alignment_cache, save_alignment_cache
from .conversation_report import build_conversation_report
from .diarization_provider import diarize_with_pyannote, load_diarization_cache, save_diarization_cache
from .nonverbal_provider import detect_textual_vocal_cues
from .openai_provider import analyze_conversation_with_openai, openai_enabled, transcribe_audio_with_openai
from .profile_provider import infer_accent_broad_signal, infer_age_signal, infer_voice_presentation_signal
from .transcription_provider import load_transcription_cache, normalize_word_records, save_transcription_cache, transcribe_with_faster_whisper

DB_PATH = RUNS_DIR / "spectrum.sqlite3"
FILLER_PATTERN = re.compile(r"\b(uh|um|ah|hmm|erm|like)\b", re.IGNORECASE)
UNCERTAINTY_PHRASES = [
    "maybe",
    "not sure",
    "i think",
    "depends",
    "kind of",
    "sort of",
    "probably",
    "around",
]
QUESTION_PREFIXES = ("how", "what", "why", "can", "could", "would", "will", "do", "does", "did", "is", "are", "any")
PROFILE_VISIBLE_THRESHOLD = 0.72
PROFILE_MUTED_THRESHOLD = 0.5
AFFECT_VISIBLE_THRESHOLD = 0.72
AFFECT_MUTED_THRESHOLD = 0.5
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")
EMOTION_CUES: dict[str, tuple[str, ...]] = {
    "joy": ("great", "awesome", "glad", "love", "perfect", "excellent", "happy", "thanks"),
    "anger": ("why", "issue", "problem", "charged", "refund", "angry", "annoyed", "frustrated", "upset"),
    "sadness": ("sorry", "lost", "sad", "unhappy", "difficult", "hard"),
    "surprise": ("what", "wow", "really", "unexpected", "suddenly"),
    "fear": ("worried", "risk", "scared", "unsafe", "concerned"),
    "disgust": ("gross", "awful", "terrible"),
}
SENTIMENT_BY_EMOTION = {
    "joy": "positive",
    "anger": "negative",
    "sadness": "negative",
    "fear": "negative",
    "disgust": "negative",
    "surprise": "neutral",
    "neutral": "neutral",
    "calm": "neutral",
}
TOPIC_KEYWORDS = {
    "pricing": ("price", "pricing", "pay", "budget", "salary", "compensation"),
    "privacy": ("privacy", "secure", "security", "data", "stored", "compliance"),
    "support": ("support", "payment", "transaction", "refund", "charged", "issue"),
    "workflow": ("manual", "workflow", "ops", "notes", "process"),
}
JOB_STAGE_DEFINITIONS = [
    {"key": "upload", "label": "Uploading audio", "weight": 5},
    {"key": "normalize", "label": "Normalizing audio", "weight": 8},
    {"key": "diarization", "label": "Aligning speaker diarization", "weight": 10},
    {"key": "waveform_visuals", "label": "Preparing waveform and spectrogram views", "weight": 7},
    {"key": "quality", "label": "Scoring call quality and noise", "weight": 10},
    {"key": "structure", "label": "Finding turns, pauses, and overlaps", "weight": 10},
    {"key": "content", "label": "Extracting transcript and content signals", "weight": 10},
    {"key": "speaker_roles", "label": "Classifying human and AI speakers", "weight": 7},
    {"key": "affect", "label": "Aligning sentence emotion and transcript spans", "weight": 8},
    {"key": "prosody", "label": "Tracing pitch, energy, and speaking-rate tracks", "weight": 8},
    {"key": "questions", "label": "Mapping questions and answers", "weight": 6},
    {"key": "nonverbal_cues", "label": "Tagging non-verbal cues and prosody events", "weight": 8},
    {"key": "human_analysis", "label": "Scoring human emotion and behavior", "weight": 7},
    {"key": "signals", "label": "Scoring hesitation, friction, and rapport", "weight": 6},
    {"key": "persist", "label": "Saving results", "weight": 4},
]
JOB_STAGE_INDEX = {stage["key"]: index + 1 for index, stage in enumerate(JOB_STAGE_DEFINITIONS)}
JOB_STAGE_BY_KEY = {stage["key"]: stage for stage in JOB_STAGE_DEFINITIONS}
JOB_STAGE_COUNT = len(JOB_STAGE_DEFINITIONS)


@dataclass
class TranscriptionOutcome:
    transcript: str
    words: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    provider: ProviderDecision = field(
        default_factory=lambda: ProviderDecision(kind="transcription", provider_key="faster_whisper")
    )


@dataclass
class AlignmentOutcome:
    words: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    provider: ProviderDecision = field(
        default_factory=lambda: ProviderDecision(kind="alignment", provider_key="whisperx")
    )


def _provider_cache_path(job_id: str, kind: str) -> Path:
    return run_file(job_id, f"{kind}.provider.json")


def _load_provider_cache(job_id: str, kind: str) -> dict[str, Any] | None:
    path = _provider_cache_path(job_id, kind)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def _save_provider_cache(job_id: str, kind: str, payload: dict[str, Any]) -> None:
    _provider_cache_path(job_id, kind).write_text(json.dumps(payload, indent=2) + "\n")


def _upload_provider_preference(metadata: dict[str, Any]) -> str:
    explicit = str(metadata.get("provider_override") or metadata.get("transcription_provider") or "").strip().lower()
    if explicit in {"local", "openai"}:
        return explicit
    env_value = os.environ.get("SPECTRUM_UPLOAD_PROVIDER", "local").strip().lower()
    if env_value in {"local", "openai"}:
        return env_value
    return "local"


def _normalize_provider_words(words: list[dict[str, Any]], *, source: str) -> list[dict[str, Any]]:
    return normalize_word_records(words, source=source)


def _readiness_tier(
    transcript: str,
    diarization: DiarizationSummary,
    nonverbal_cues: list[NonverbalCue] | None = None,
) -> ReadinessTier:
    visible_vocal_cues = [
        cue
        for cue in (nonverbal_cues or [])
        if cue.family == "vocal_sound" and cue.display_state in {"visible", "muted"}
    ]
    if diarization.readiness_state == "ready" and transcript.strip():
        if any(cue.attribution_state != "strong" for cue in visible_vocal_cues):
            return "partial"
        return "full"
    if diarization.readiness_state == "fallback" and transcript.strip():
        return "partial"
    if transcript.strip():
        return "transcript_only"
    return "blocked"


def _quality_band(quality: QualitySummary) -> str:
    if quality.noise_ratio >= 0.35 or not quality.is_usable:
        return "risky"
    if quality.noise_ratio >= 0.2:
        return "watch"
    return "clean"


def _completed_percent_before(stage_key: str) -> int:
    total = 0
    for stage in JOB_STAGE_DEFINITIONS:
        if stage["key"] == stage_key:
            break
        total += int(stage["weight"])
    return total


def estimate_upload_seconds(file_size_bytes: int) -> int:
    file_size_mb = max(0.0, file_size_bytes / (1024 * 1024))
    return max(1, min(20, round(file_size_mb / 8)))


def estimate_analysis_seconds(duration_sec: float) -> int:
    return max(8, min(180, round(6 + max(0.0, duration_sec) * 0.8)))


def estimate_total_job_seconds(duration_sec: float, file_size_bytes: int) -> int:
    return estimate_upload_seconds(file_size_bytes) + estimate_analysis_seconds(duration_sec)


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def count_words(text: str) -> int:
    return len([token for token in re.split(r"\s+", text.strip()) if token])


def derive_fillers(text: str) -> list[str]:
    return [match.group(0).lower() for match in FILLER_PATTERN.finditer(text)]


def derive_uncertainty_markers(text: str) -> list[str]:
    lowered = text.lower()
    return [phrase for phrase in UNCERTAINTY_PHRASES if phrase in lowered]


def derive_topics(text: str, turns: list[TurnModel]) -> list[str]:
    labels = {turn.section for turn in turns if turn.section}
    lowered = text.lower()
    for label, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            labels.add(label)
    return sorted(label for label in labels if label)


def derive_age_band(age: float | None, confidence: float = 0.0, threshold: float = 0.5) -> LabelPrediction:
    if age is None or confidence < threshold:
        return LabelPrediction(label="unknown", confidence=confidence)
    if age < 18:
        label = "under_18"
    elif age <= 24:
        label = "18_24"
    elif age <= 34:
        label = "25_34"
    elif age <= 49:
        label = "35_49"
    else:
        label = "50_plus"
    return LabelPrediction(label=label, confidence=confidence)


def confidence_display_state(
    confidence: float,
    *,
    label: str | None = None,
    visible_threshold: float = PROFILE_VISIBLE_THRESHOLD,
    muted_threshold: float = PROFILE_MUTED_THRESHOLD,
) -> DisplayState:
    if not label or label == "unknown" or confidence <= 0:
        return "unavailable"
    if confidence >= visible_threshold:
        return "visible"
    if confidence >= muted_threshold:
        return "muted"
    return "hidden"


def finalize_label_prediction(
    prediction: LabelPrediction,
    *,
    label: str | None = None,
    confidence: float | None = None,
    source: PredictionSource | None = None,
    summary: str | None = None,
    warning_flags: list[str] | None = None,
    visible_threshold: float = PROFILE_VISIBLE_THRESHOLD,
    muted_threshold: float = PROFILE_MUTED_THRESHOLD,
) -> LabelPrediction:
    label_value = label if label is not None else prediction.label
    confidence_value = confidence if confidence is not None else prediction.confidence
    source_value = source if source is not None else prediction.source
    warnings = list(prediction.warning_flags)
    if warning_flags:
        warnings.extend(warning_flags)
    return LabelPrediction(
        label=label_value,
        confidence=confidence_value,
        source=source_value,
        display_state=confidence_display_state(
            confidence_value,
            label=label_value,
            visible_threshold=visible_threshold,
            muted_threshold=muted_threshold,
        ),
        summary=summary if summary is not None else prediction.summary,
        warning_flags=sorted(set(warnings)),
    )


def finalize_lang_mix(prediction: LangMixPrediction) -> LangMixPrediction:
    return LangMixPrediction(
        label=prediction.label,
        english_ratio=prediction.english_ratio,
        language_ratios=prediction.language_ratios,
        source=prediction.source,
        display_state=confidence_display_state(
            prediction.english_ratio if prediction.label != "unknown" else 0.0,
            label=prediction.label,
            visible_threshold=0.6,
            muted_threshold=0.35,
        ),
        summary=prediction.summary,
        warning_flags=sorted(set(prediction.warning_flags)),
    )


def profile_field_from_prediction(
    key: str,
    label: str,
    prediction: LabelPrediction | LangMixPrediction,
    *,
    value: str | None = None,
    summary: str | None = None,
    details: dict[str, float | str] | None = None,
) -> ProfileField:
    resolved_value = value if value is not None else prediction.label
    extra_details = details or {}
    if isinstance(prediction, LangMixPrediction):
        extra_details = {
            **extra_details,
            "english_ratio": prediction.english_ratio,
            **{name: ratio for name, ratio in prediction.language_ratios.items()},
        }
    return ProfileField(
        key=key,
        label=label,
        value=resolved_value,
        confidence=prediction.confidence if isinstance(prediction, LabelPrediction) else prediction.english_ratio,
        source=prediction.source,
        display_state=prediction.display_state,
        summary=summary if summary is not None else prediction.summary,
        warning_flags=list(prediction.warning_flags),
        details=extra_details,
    )


@dataclass
class ProcessSessionOptions:
    prototype_noncommercial: bool = False
    enable_comparisons: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class SessionStore:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="spectrum-analysis")
        self._futures: dict[str, Future[SessionResult]] = {}
        self._future_lock = Lock()
        self._init_db()
        self._mark_stale_jobs_failed()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    job_id TEXT PRIMARY KEY,
                    analysis_mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    original_filename TEXT,
                    original_path TEXT,
                    result_path TEXT,
                    error TEXT,
                    metadata_json TEXT
                )
                """
            )

    def create_session(self, analysis_mode: str, metadata: dict[str, Any] | None = None) -> SessionRecord:
        job_id = str(uuid4())
        now = utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions (
                    job_id, analysis_mode, status, created_at, updated_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (job_id, analysis_mode, "created", now, now, json.dumps(metadata or {})),
            )
        self.write_job_status(
            job_id,
            status="created",
            stage_key=None,
            stage_label=None,
            stage_index=0,
            stage_count=JOB_STAGE_COUNT,
            percent_complete=0,
            message="Session created",
            eta_seconds=0,
            started_at=None,
            error=None,
        )
        return self.get_session(job_id)

    def seed_session(self, job_id: str, analysis_mode: AnalysisMode, metadata: dict[str, Any] | None = None) -> SessionRecord:
        now = utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions (
                    job_id, analysis_mode, status, created_at, updated_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    analysis_mode = excluded.analysis_mode,
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
                """,
                (job_id, analysis_mode, "created", now, now, json.dumps(metadata or {})),
            )
        self.write_job_status(
            job_id,
            status="created",
            stage_key=None,
            stage_label=None,
            stage_index=0,
            stage_count=JOB_STAGE_COUNT,
            percent_complete=0,
            message="Session created",
            eta_seconds=0,
            started_at=None,
            error=None,
        )
        return self.get_session(job_id)

    def save_upload(self, job_id: str, filename: str, original_path: Path) -> SessionRecord:
        now = utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE sessions
                SET status = ?, updated_at = ?, original_filename = ?, original_path = ?
                WHERE job_id = ?
                """,
                ("uploaded", now, filename, str(original_path), job_id),
            )
        self.write_job_status(
            job_id,
            status="uploaded",
            stage_key="upload",
            stage_label=JOB_STAGE_BY_KEY["upload"]["label"],
            stage_index=JOB_STAGE_INDEX["upload"],
            stage_count=JOB_STAGE_COUNT,
            percent_complete=_completed_percent_before("normalize"),
            message="Audio upload complete",
            eta_seconds=0,
            started_at=None,
            error=None,
        )
        return self.get_session(job_id)

    def set_processing(self, job_id: str) -> SessionRecord:
        return self._update(job_id, status="processing", error=None)

    def set_queued(self, job_id: str) -> SessionRecord:
        return self._update(job_id, status="queued", error=None)

    def set_completed(self, job_id: str, result_path: Path) -> SessionRecord:
        self.clear_background_job(job_id)
        return self._update(job_id, status="completed", result_path=str(result_path), error=None)

    def set_failed(self, job_id: str, error: str) -> SessionRecord:
        self.clear_background_job(job_id)
        return self._update(job_id, status="failed", error=error)

    def register_background_job(self, job_id: str, future: Future[SessionResult]) -> None:
        with self._future_lock:
            self._futures[job_id] = future

    def get_background_job(self, job_id: str) -> Future[SessionResult] | None:
        with self._future_lock:
            return self._futures.get(job_id)

    def clear_background_job(self, job_id: str) -> None:
        with self._future_lock:
            self._futures.pop(job_id, None)

    def status_path(self, job_id: str) -> Path:
        return run_file(job_id, "status.json")

    def _load_job_status_file(self, job_id: str) -> SessionJobStatus | None:
        status_path = self.status_path(job_id)
        if not status_path.exists():
            return None
        try:
            return SessionJobStatus.model_validate_json(status_path.read_text())
        except json.JSONDecodeError:
            return None

    def read_job_status(self, job_id: str) -> SessionJobStatus | None:
        status = self._load_job_status_file(job_id)
        if status is None:
            return None
        future = self.get_background_job(job_id)
        if status.status in {"queued", "processing"} and (future is None or future.cancelled()):
            status = self.fail_interrupted_job(job_id)
        elif status.status in {"queued", "processing"} and future is not None and future.done():
            try:
                future.result()
            except Exception as error:  # pragma: no cover
                status = self.write_job_status(
                    job_id,
                    status="failed",
                    stage_key=status.stage_key,
                    stage_label=status.stage_label,
                    stage_index=status.stage_index,
                    stage_count=status.stage_count,
                    percent_complete=status.percent_complete,
                    message="Analysis failed",
                    eta_seconds=0,
                    started_at=status.started_at,
                    error=str(error),
                )
                self.set_failed(job_id, str(error))
            else:
                if run_file(job_id, "result.json").exists():
                    status = self.write_job_status(
                        job_id,
                        status="completed",
                        stage_key="persist",
                        stage_label=JOB_STAGE_BY_KEY["persist"]["label"],
                        stage_index=JOB_STAGE_INDEX["persist"],
                        stage_count=JOB_STAGE_COUNT,
                        percent_complete=100,
                        message="Analysis complete",
                        eta_seconds=0,
                        started_at=status.started_at,
                        error=None,
                    )
        return status

    def write_job_status(
        self,
        job_id: str,
        *,
        status: str,
        stage_key: str | None,
        stage_label: str | None,
        stage_index: int,
        stage_count: int,
        percent_complete: int,
        message: str,
        eta_seconds: int,
        started_at: str | None,
        error: str | None,
    ) -> SessionJobStatus:
        previous = self._load_job_status_file(job_id)
        now = utc_now()
        history = list(previous.history) if previous else []
        if previous and previous.stage_key and previous.stage_key != stage_key and previous.status in {"uploaded", "queued", "processing"}:
            history.append(
                JobActivityEntry(
                    stage_key=previous.stage_key,
                    stage_label=previous.stage_label or previous.stage_key,
                    message=previous.message,
                    completed_at=now,
                    percent_complete=previous.percent_complete,
                )
            )
        payload = SessionJobStatus(
            job_id=job_id,
            status=status,
            stage_key=stage_key,
            stage_label=stage_label,
            stage_index=stage_index,
            stage_count=stage_count,
            percent_complete=max(0, min(100, percent_complete)),
            message=message,
            eta_seconds=max(0, eta_seconds),
            started_at=started_at if started_at is not None else (previous.started_at if previous else None),
            updated_at=now,
            error=error,
            history=history,
        )
        self.status_path(job_id).write_text(payload.model_dump_json(indent=2) + "\n")
        return payload

    def fail_interrupted_job(self, job_id: str) -> SessionJobStatus:
        previous = self._load_job_status_file(job_id)
        if previous is None:
            failed = self.write_job_status(
                job_id,
                status="failed",
                stage_key=None,
                stage_label=None,
                stage_index=0,
                stage_count=JOB_STAGE_COUNT,
                percent_complete=0,
                message="Analysis interrupted before status could be restored",
                eta_seconds=0,
                started_at=None,
                error="Analysis was interrupted by a server restart or worker shutdown.",
            )
            try:
                self.set_failed(job_id, failed.error or "Analysis interrupted")
            except KeyError:
                pass
            return failed
        failed = self.write_job_status(
            job_id,
            status="failed",
            stage_key=previous.stage_key,
            stage_label=previous.stage_label,
            stage_index=previous.stage_index,
            stage_count=previous.stage_count,
            percent_complete=previous.percent_complete,
            message="Analysis interrupted",
            eta_seconds=0,
            started_at=previous.started_at,
            error="Analysis was interrupted by a server restart or worker shutdown.",
        )
        try:
            self.set_failed(job_id, failed.error or "Analysis interrupted")
        except KeyError:
            pass
        return failed

    def _update(self, job_id: str, **changes: Any) -> SessionRecord:
        now = utc_now()
        columns = ["updated_at = ?"]
        values: list[Any] = [now]
        for key, value in changes.items():
            columns.append(f"{key} = ?")
            values.append(value)
        values.append(job_id)
        with self._connect() as connection:
            connection.execute(f"UPDATE sessions SET {', '.join(columns)} WHERE job_id = ?", values)
        return self.get_session(job_id)

    def get_session(self, job_id: str) -> SessionRecord:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM sessions WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        return SessionRecord(
            job_id=row["job_id"],
            analysis_mode=row["analysis_mode"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            original_filename=row["original_filename"],
            result_path=row["result_path"],
            error=row["error"],
        )

    def list_sessions(self) -> list[SessionRecord]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM sessions ORDER BY datetime(updated_at) DESC").fetchall()
        return [
            SessionRecord(
                job_id=row["job_id"],
                analysis_mode=row["analysis_mode"],
                status=row["status"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                original_filename=row["original_filename"],
                result_path=row["result_path"],
                error=row["error"],
            )
            for row in rows
        ]

    def _mark_stale_jobs_failed(self) -> None:
        for status_path in RUNS_DIR.glob("*/status.json"):
            try:
                status = SessionJobStatus.model_validate_json(status_path.read_text())
            except (FileNotFoundError, json.JSONDecodeError):
                continue
            if status.status in {"queued", "processing"}:
                self.fail_interrupted_job(status.job_id)


@dataclass
class JobProgressReporter:
    store: SessionStore
    job_id: str
    duration_sec_hint: float
    file_size_bytes: int
    started_at: str = field(default_factory=utc_now)

    @classmethod
    def from_audio_path(cls, store: SessionStore, job_id: str, audio_path: Path) -> "JobProgressReporter":
        try:
            duration_sec_hint = probe_duration(audio_path)
        except Exception:  # pragma: no cover
            duration_sec_hint = 0.0
        return cls(
            store=store,
            job_id=job_id,
            duration_sec_hint=duration_sec_hint,
            file_size_bytes=audio_path.stat().st_size if audio_path.exists() else 0,
        )

    def queue(self) -> SessionJobStatus:
        return self.store.write_job_status(
            self.job_id,
            status="queued",
            stage_key="normalize",
            stage_label=JOB_STAGE_BY_KEY["normalize"]["label"],
            stage_index=JOB_STAGE_INDEX["normalize"],
            stage_count=JOB_STAGE_COUNT,
            percent_complete=_completed_percent_before("normalize"),
            message="Queued for analysis",
            eta_seconds=self._eta_for_stage("normalize"),
            started_at=self.started_at,
            error=None,
        )

    def stage(self, stage_key: str, message: str | None = None) -> SessionJobStatus:
        stage = JOB_STAGE_BY_KEY[stage_key]
        return self.store.write_job_status(
            self.job_id,
            status="processing",
            stage_key=stage_key,
            stage_label=stage["label"],
            stage_index=JOB_STAGE_INDEX[stage_key],
            stage_count=JOB_STAGE_COUNT,
            percent_complete=_completed_percent_before(stage_key),
            message=message or stage["label"],
            eta_seconds=self._eta_for_stage(stage_key),
            started_at=self.started_at,
            error=None,
        )

    def complete(self) -> SessionJobStatus:
        return self.store.write_job_status(
            self.job_id,
            status="completed",
            stage_key="persist",
            stage_label=JOB_STAGE_BY_KEY["persist"]["label"],
            stage_index=JOB_STAGE_INDEX["persist"],
            stage_count=JOB_STAGE_COUNT,
            percent_complete=100,
            message="Analysis complete",
            eta_seconds=0,
            started_at=self.started_at,
            error=None,
        )

    def fail(self, error: Exception | str) -> SessionJobStatus:
        previous = self.store._load_job_status_file(self.job_id)
        error_text = str(error)
        return self.store.write_job_status(
            self.job_id,
            status="failed",
            stage_key=previous.stage_key if previous else None,
            stage_label=previous.stage_label if previous else None,
            stage_index=previous.stage_index if previous else 0,
            stage_count=previous.stage_count if previous else JOB_STAGE_COUNT,
            percent_complete=previous.percent_complete if previous else 0,
            message="Analysis failed",
            eta_seconds=0,
            started_at=self.started_at,
            error=error_text,
        )

    def _eta_for_stage(self, stage_key: str) -> int:
        baseline = estimate_total_job_seconds(self.duration_sec_hint, self.file_size_bytes)
        remaining_ratio = max(0.0, 1 - (_completed_percent_before(stage_key) / 100))
        return max(0, round(baseline * remaining_ratio))


def session_dir(job_id: str) -> Path:
    return RUNS_DIR / job_id


def run_file(job_id: str, *parts: str) -> Path:
    path = session_dir(job_id).joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def normalize_audio(input_path: Path, output_path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-vn",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def render_telephony_audio(input_path: Path, output_path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-ac",
            "1",
            "-ar",
            "8000",
            "-vn",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def probe_duration(audio_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip() or 0.0)


def detect_silences(audio_path: Path) -> list[tuple[float, float]]:
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(audio_path),
            "-af",
            "silencedetect=noise=-30dB:d=0.3",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    silence_starts: list[float] = []
    intervals: list[tuple[float, float]] = []
    for line in result.stderr.splitlines():
        if "silence_start:" in line:
            silence_starts.append(float(line.split("silence_start:")[-1].strip()))
        elif "silence_end:" in line and silence_starts:
            match = re.search(r"silence_end:\s*([0-9.]+)", line)
            if match:
                intervals.append((silence_starts.pop(0), float(match.group(1))))
    return intervals


def waveform_stats(audio_path: Path) -> tuple[float | None, float]:
    with wave.open(str(audio_path), "rb") as handle:
        if handle.getsampwidth() != 2:
            return None, 0.0
        frames = handle.readframes(handle.getnframes())
    samples = array("h")
    samples.frombytes(frames)
    if not samples:
        return None, 0.0
    values = [abs(sample) for sample in samples]
    peak = max(values) / 32768.0
    rms = math.sqrt(sum(sample * sample for sample in values) / len(values)) / 32768.0
    clipping_ratio = sum(1 for sample in values if sample >= 32000) / len(values)
    noise_floor = max(peak - rms, 1e-6)
    avg_snr_db = 20 * math.log10((rms + 1e-6) / noise_floor)
    return round(avg_snr_db, 3), clipping_ratio


def load_normalized_samples(audio_path: Path) -> tuple[int, list[float]]:
    with wave.open(str(audio_path), "rb") as handle:
        if handle.getsampwidth() != 2:
            raise ValueError("Only 16-bit PCM audio is supported for visual artifacts.")
        frames = handle.readframes(handle.getnframes())
        sample_rate = handle.getframerate()
    pcm = array("h")
    pcm.frombytes(frames)
    return sample_rate, [sample / 32768.0 for sample in pcm]


def build_waveform_artifact(audio_path: Path, duration_sec: float, bucket_count: int = 640) -> WaveformArtifact:
    try:
        _sample_rate, samples = load_normalized_samples(audio_path)
    except Exception:
        return WaveformArtifact(duration_ms=int(duration_sec * 1000))
    if not samples:
        return WaveformArtifact(duration_ms=int(duration_sec * 1000))
    bucket_count = max(80, min(bucket_count, len(samples)))
    step = max(1, len(samples) // bucket_count)
    peaks: list[float] = []
    for index in range(0, len(samples), step):
        window = samples[index : index + step]
        if not window:
            continue
        peaks.append(round(max(abs(sample) for sample in window), 4))
    return WaveformArtifact(
        duration_ms=int(duration_sec * 1000),
        sample_count=len(samples),
        bucket_count=len(peaks),
        peaks=peaks,
    )


def generate_spectrogram(audio_path: Path, output_path: Path) -> SpectrogramArtifact:
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(audio_path),
                "-lavfi",
                "showspectrumpic=s=1600x360:legend=disabled:color=intensity",
                "-frames:v",
                "1",
                str(output_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        return SpectrogramArtifact(
            readiness_state="fallback",
            image_path=None,
            notes=[f"spectrogram_generation_failed:{error.__class__.__name__}"],
        )
    return SpectrogramArtifact(
        readiness_state="ready",
        image_path=str(output_path),
        width=1600,
        height=360,
    )


def _estimate_pitch_hz(window: list[float], sample_rate: int) -> float | None:
    if len(window) < 2:
        return None
    rms = math.sqrt(sum(sample * sample for sample in window) / len(window))
    if rms < 0.015:
        return None
    zero_crossings = sum(1 for left, right in zip(window, window[1:]) if (left <= 0 < right) or (left >= 0 > right))
    if zero_crossings <= 1:
        return None
    hz = zero_crossings * sample_rate / (2 * len(window))
    if 50 <= hz <= 450:
        return round(hz, 2)
    return None


def _track_display_state(samples: list[ProsodyPoint]) -> DisplayState:
    if not samples:
        return "unavailable"
    if len(samples) >= 12:
        return "visible"
    return "muted"


def build_prosody_tracks(audio_path: Path, turns: list[TurnModel], duration_sec: float) -> list[ProsodyTrack]:
    try:
        sample_rate, samples = load_normalized_samples(audio_path)
    except Exception:
        return []
    if not samples:
        return []

    window_ms = 120
    window_size = max(1, int(sample_rate * (window_ms / 1000)))
    pitch_points: list[ProsodyPoint] = []
    energy_points: list[ProsodyPoint] = []
    rate_points: list[ProsodyPoint] = []
    duration_ms = int(duration_sec * 1000)

    for start_index in range(0, len(samples), window_size):
        window = samples[start_index : start_index + window_size]
        if not window:
            continue
        timestamp_ms = min(duration_ms, int((start_index / sample_rate) * 1000))
        rms = math.sqrt(sum(sample * sample for sample in window) / len(window))
        energy_points.append(ProsodyPoint(timestamp_ms=timestamp_ms, value=round(rms, 4)))
        pitch = _estimate_pitch_hz(window, sample_rate)
        if pitch is not None:
            pitch_points.append(ProsodyPoint(timestamp_ms=timestamp_ms, value=pitch))
        matching_turn = next((turn for turn in turns if turn.start_ms <= timestamp_ms <= turn.end_ms and turn.speech_rate_wpm), None)
        if matching_turn and matching_turn.speech_rate_wpm is not None:
            rate_points.append(ProsodyPoint(timestamp_ms=timestamp_ms, value=float(matching_turn.speech_rate_wpm)))

    return [
        ProsodyTrack(
            key="pitch_hz",
            label="Pitch",
            unit="Hz",
            source="heuristic",
            display_state=_track_display_state(pitch_points),
            samples=pitch_points,
            notes=["Zero-crossing pitch proxy from the normalized waveform."],
        ),
        ProsodyTrack(
            key="energy_rms",
            label="Energy",
            unit="rms",
            source="heuristic",
            display_state=_track_display_state(energy_points),
            samples=energy_points,
            notes=["RMS energy track from the normalized waveform."],
        ),
        ProsodyTrack(
            key="speaking_rate_wpm",
            label="Speaking Rate",
            unit="wpm",
            source="heuristic",
            display_state=_track_display_state(rate_points),
            samples=rate_points,
            notes=["Windowed speaking-rate projection derived from aligned turns."],
        ),
    ]


def _adapter_lookup(adapters: list[Any], key: str) -> Any | None:
    return next((adapter for adapter in adapters if adapter.key == key), None)


def _overlap_windows_from_segments(segments: list[DiarizationSegment]) -> list[TimeWindow]:
    windows: list[TimeWindow] = []
    ordered = sorted(segments, key=lambda segment: (segment.start_ms, segment.end_ms))
    for previous, current in zip(ordered, ordered[1:]):
        if current.start_ms < previous.end_ms and current.speaker_id != previous.speaker_id:
            windows.append(
                TimeWindow(
                    start_ms=current.start_ms,
                    end_ms=previous.end_ms,
                    label="speaker_overlap",
                )
            )
    return windows


def _segments_from_metadata(
    job_id: str,
    metadata: dict[str, Any],
    turns: list[TurnModel],
    *,
    source: PredictionSource,
    confidence: float,
) -> list[DiarizationSegment]:
    raw_segments = metadata.get("diarization_segments") or metadata.get("speaker_segments") or []
    if raw_segments:
        return [
            DiarizationSegment(
                segment_id=str(segment.get("segment_id", f"{job_id}-speaker-{index}")),
                speaker_id=str(segment.get("speaker_id", "speaker_0")),
                start_ms=int(segment.get("start_ms", 0)),
                end_ms=int(segment.get("end_ms", 0)),
                confidence=float(segment.get("confidence", confidence)),
                source=source,
                display_state=confidence_display_state(float(segment.get("confidence", confidence)), label=str(segment.get("speaker_id", "speaker_0"))),
                label=str(segment.get("label", segment.get("speaker_id", "speaker_0"))),
            )
            for index, segment in enumerate(raw_segments)
        ]
    if turns:
        return [
            DiarizationSegment(
                segment_id=f"{job_id}-speaker-segment-{index}",
                speaker_id=turn.speaker_id,
                start_ms=turn.start_ms,
                end_ms=turn.end_ms,
                confidence=confidence,
                source=source,
                display_state=confidence_display_state(confidence, label=turn.speaker_id),
                label=turn.speaker_id,
            )
            for index, turn in enumerate(turns)
        ]
    return []


def _fallback_uploaded_segments(job_id: str, metadata: dict[str, Any], turns: list[TurnModel]) -> list[DiarizationSegment]:
    if not turns:
        return []
    raw_segments = metadata.get("diarization_segments") or metadata.get("speaker_segments") or []
    if raw_segments:
        return _segments_from_metadata(job_id, metadata, turns, source="metadata_hint", confidence=0.62)

    distinct_speakers = {turn.speaker_id for turn in turns if turn.speaker_id}
    if len(turns) <= 1 and len(distinct_speakers) <= 1:
        return [
            DiarizationSegment(
                segment_id=f"{job_id}-fallback-speaker-0",
                speaker_id=turns[0].speaker_id or "speaker_0",
                start_ms=turns[0].start_ms,
                end_ms=turns[0].end_ms,
                confidence=0.26,
                source="heuristic",
                display_state="muted",
                label=(turns[0].speaker_id or "speaker_0").replace("_", " "),
            )
        ]

    return [
        DiarizationSegment(
            segment_id=f"{job_id}-fallback-speaker-{index}",
            speaker_id=turn.speaker_id or f"speaker_{index % 2}",
            start_ms=turn.start_ms,
            end_ms=turn.end_ms,
            confidence=min(0.58, max(0.32, turn.confidence)),
            source="heuristic",
            display_state="muted",
            label=(turn.speaker_id or f"speaker_{index % 2}").replace("_", " "),
        )
        for index, turn in enumerate(turns)
    ]


def _maybe_diarize_with_pyannote(audio_path: Path, job_id: str, adapters: list[Any]) -> tuple[list[DiarizationSegment], list[str], ProviderDecision]:
    pyannote = _adapter_lookup(adapters, "pyannote")
    if not pyannote or not pyannote.available or not pyannote.token_present:
        notes: list[str] = []
        if pyannote and pyannote.available and not pyannote.token_present:
            notes.append("pyannote_token_missing")
        elif not pyannote or not pyannote.available:
            notes.append("pyannote_missing")
        return [], [], ProviderDecision(
            kind="diarization",
            provider_key="pyannote",
            used=False,
            cached=False,
            status="blocked",
            notes=notes,
        )
    cache_path = _provider_cache_path(job_id, "diarization")
    cached_segments = load_diarization_cache(cache_path)
    if cached_segments:
        segments = [
            segment.model_copy(update={"segment_id": segment.segment_id or f"{job_id}-pyannote-cache-{index}"})
            for index, segment in enumerate(cached_segments)
        ]
        return segments, [], ProviderDecision(
            kind="diarization",
            provider_key="pyannote",
            used=bool(segments),
            cached=bool(segments),
            status="ready" if segments else "fallback",
            notes=["diarization_cache_reused"] if segments else [],
        )
    segments, notes = diarize_with_pyannote(audio_path)
    if segments:
        segments = [
            segment.model_copy(update={"segment_id": f"{job_id}-pyannote-{index}"})
            for index, segment in enumerate(segments)
        ]
        save_diarization_cache(cache_path, segments)
        return segments, [], ProviderDecision(
            kind="diarization",
            provider_key="pyannote",
            used=bool(segments),
            cached=False,
            status="ready" if segments else "fallback",
            notes=[],
        )
    return [], notes, ProviderDecision(
        kind="diarization",
        provider_key="pyannote",
        used=False,
        cached=False,
        status="fallback" if notes else "blocked",
        notes=notes or ["pyannote_missing"],
    )


def build_diarization(
    job_id: str,
    audio_path: Path,
    metadata: dict[str, Any],
    turns: list[TurnModel],
    adapters: list[Any],
) -> tuple[DiarizationSummary, ProviderDecision]:
    source_type = str(metadata.get("source_type") or "direct_audio_file")
    dataset_id = str(metadata.get("dataset_id") or "")
    benchmark_source = dataset_id in {"ami_corpus", "meld"} or bool(metadata.get("benchmark_diarization"))
    if benchmark_source:
        segments = _segments_from_metadata(job_id, metadata, turns, source="benchmark_label", confidence=0.96)
        status: StageState = "ready" if segments else "fallback"
        return (
            DiarizationSummary(
                readiness_state=status,
                source="benchmark_label" if segments else "unavailable",
                confidence=0.96 if segments else 0.0,
                segments=segments,
                overlap_windows=_overlap_windows_from_segments(segments),
                notes=["Benchmark-aligned diarization metadata is driving the speaker lanes."],
            ),
            ProviderDecision(
                kind="diarization",
                provider_key="benchmark_metadata",
                used=bool(segments),
                cached=False,
                status=status,
                notes=["benchmark_diarization"] if segments else ["benchmark_diarization_missing"],
            ),
        )

    if source_type != "direct_audio_file":
        segments = _segments_from_metadata(job_id, metadata, turns, source="metadata_hint", confidence=0.7)
        status: StageState = "ready" if segments else "fallback"
        return (
            DiarizationSummary(
                readiness_state=status,
                source="metadata_hint" if segments else "unavailable",
                confidence=0.7 if segments else 0.0,
                segments=segments,
                overlap_windows=_overlap_windows_from_segments(segments),
                notes=["Non-upload sources can reuse trusted metadata speaker spans when available."],
            ),
            ProviderDecision(
                kind="diarization",
                provider_key="metadata_hint",
                used=bool(segments),
                cached=False,
                status=status,
                notes=["metadata_diarization"] if segments else ["metadata_diarization_missing"],
            ),
        )

    segments, notes, provider = _maybe_diarize_with_pyannote(audio_path, job_id, adapters)
    if segments:
        return (
            DiarizationSummary(
                readiness_state="ready",
                source="model",
                confidence=0.81,
                segments=segments,
                overlap_windows=_overlap_windows_from_segments(segments),
                notes=notes or ["Pyannote supplied the uploaded diarization view."],
            ),
            provider,
        )

    pyannote = _adapter_lookup(adapters, "pyannote")
    fallback_segments = _fallback_uploaded_segments(job_id, metadata, turns)
    if fallback_segments:
        fallback_notes = [
            "Speaker coverage is using turn-aligned fallback segmentation for this upload.",
            "Speaker-attributed vocal cues remain conservative until pyannote diarization is available.",
        ]
        if pyannote and pyannote.available and not pyannote.token_present:
            fallback_notes.insert(
                0,
                "Pyannote is installed, but the Hugging Face token or model access is missing for uploaded diarization.",
            )
        elif not pyannote or not pyannote.available:
            fallback_notes.insert(
                0,
                "Pyannote speaker diarization is not available locally, so the upload is using a degraded speaker timeline.",
            )
        return (
            DiarizationSummary(
                readiness_state="fallback",
                source="heuristic",
                confidence=round(sum(segment.confidence for segment in fallback_segments) / len(fallback_segments), 3),
                segments=fallback_segments,
                overlap_windows=_overlap_windows_from_segments(fallback_segments),
                notes=[*fallback_notes, *notes],
            ),
            ProviderDecision(
                kind="diarization",
                provider_key="heuristic_fallback",
                used=True,
                cached=False,
                status="fallback",
                notes=["diarization_fallback_segments", *provider.notes],
            ),
        )

    gate_note = "Full diarized cue view requires pyannote speaker diarization on uploaded audio."
    if pyannote and pyannote.available and not pyannote.token_present:
        gate_note = "Pyannote is installed, but the Hugging Face token or model access is missing for uploaded diarization."
    return (
        DiarizationSummary(
            readiness_state="blocked",
            source="unavailable",
            confidence=0.0,
            segments=[],
            overlap_windows=[],
            notes=[gate_note, *notes],
        ),
        ProviderDecision(
            kind="diarization",
            provider_key="pyannote",
            used=False,
            cached=False,
            status="blocked",
            notes=["diarization_blocked", *provider.notes],
        ),
    )


def _group_openai_words_into_segments(job_id: str, words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for index, word in enumerate(words):
        text = str(word.get("word") or "").strip()
        if not text:
            continue
        speaker_value = word.get("speaker")
        if speaker_value is None:
            speaker_id = "speaker_0"
        elif isinstance(speaker_value, str) and speaker_value.startswith("speaker_"):
            speaker_id = speaker_value
        else:
            speaker_id = f"speaker_{speaker_value}"
        start_ms = int(float(word.get("start", 0.0)) * 1000)
        end_ms = int(float(word.get("end", 0.0)) * 1000)
        confidence = float(word.get("confidence", 0.82))
        if current and current["speaker_id"] == speaker_id and start_ms - current["end_ms"] <= 500:
            current["end_ms"] = max(current["end_ms"], end_ms)
            current["text"] = f"{current['text']} {text}".strip()
            current["confidence"] = max(current["confidence"], confidence)
            continue
        current = {
            "turn_id": f"{job_id}-openai-turn-{len(grouped)}",
            "speaker_id": speaker_id,
            "label": speaker_id.replace("_", " "),
            "start_ms": start_ms,
            "end_ms": end_ms,
            "text": text,
            "confidence": confidence,
            "source": "model",
        }
        grouped.append(current)
    return grouped


def _metadata_turns(turns: list[TurnModel]) -> list[dict[str, Any]]:
    return [
        {
            "turn_id": turn.turn_id,
            "speaker_id": turn.speaker_id,
            "start_ms": turn.start_ms,
            "end_ms": turn.end_ms,
            "text": turn.text,
            "confidence": turn.confidence,
        }
        for turn in turns
        if turn.text.strip()
    ]


def enrich_metadata_with_openai(job_id: str, audio_path: Path, metadata: dict[str, Any]) -> tuple[dict[str, Any], list[str], ProviderDecision]:
    if not openai_enabled():
        return {}, ["openai_not_configured"], ProviderDecision(
            kind="role_analysis",
            provider_key="openai_audio_analysis",
            used=False,
            cached=False,
            status="blocked",
            notes=["openai_not_configured"],
        )
    source_type = str(metadata.get("source_type") or "direct_audio_file")
    if source_type != "direct_audio_file":
        return {}, ["openai_skipped_for_non_upload"], ProviderDecision(
            kind="role_analysis",
            provider_key="openai_audio_analysis",
            used=False,
            cached=False,
            status="missing",
            notes=["openai_skipped_for_non_upload"],
        )

    warnings: list[str] = []
    updates: dict[str, Any] = {}
    transcription, transcription_warnings = transcribe_audio_with_openai(audio_path)
    warnings.extend(transcription_warnings)
    if not transcription:
        return {}, warnings, ProviderDecision(
            kind="role_analysis",
            provider_key="openai_audio_analysis",
            used=False,
            cached=False,
            status="fallback",
            notes=list(warnings),
        )

    transcript = str(transcription.get("transcript") or "").strip()
    if transcript:
        updates["transcript_hint"] = transcript
    raw_words = list(transcription.get("words") or [])
    if raw_words:
        normalized_words = [
            {
                "word": str(word.get("word") or ""),
                "start_ms": int(float(word.get("start", 0.0)) * 1000),
                "end_ms": int(float(word.get("end", 0.0)) * 1000),
                "confidence": float(word.get("confidence", 0.0)),
                "source": "model",
                "speaker_id": f"speaker_{word['speaker']}" if word.get("speaker") is not None and not str(word.get("speaker")).startswith("speaker_") else word.get("speaker"),
            }
            for word in raw_words
            if str(word.get("word") or "").strip()
        ]
        updates["openai_word_timestamps"] = normalized_words
        updates["transcript_word_timestamps"] = normalized_words
        if any(word.get("speaker") is not None for word in raw_words):
            updates["speaker_segments"] = _group_openai_words_into_segments(job_id, raw_words)

    turns_for_analysis = list(updates.get("speaker_segments") or metadata.get("speaker_segments") or [])
    if not turns_for_analysis and transcript:
        turns_for_analysis = [
            {
                "turn_id": f"{job_id}-turn-0",
                "speaker_id": "speaker_0",
                "start_ms": 0,
                "end_ms": int(probe_duration(audio_path) * 1000),
                "text": transcript,
                "confidence": 0.7,
            }
        ]

    analysis, analysis_warnings = analyze_conversation_with_openai(transcript, turns_for_analysis, metadata)
    warnings.extend(analysis_warnings)
    if analysis:
        updates["speaker_role_hints"] = {
            str(item["speaker_id"]): str(item["speaker_role"])
            for item in analysis.get("speaker_roles", [])
            if str(item.get("speaker_id") or "").strip()
        }
        updates["speaker_role_hint_source"] = "model"
        updates["openai_speaker_role_details"] = analysis.get("speaker_roles", [])
        updates["turn_emotion_hints"] = {
            str(item["turn_id"]): {
                "emotion_label": str(item.get("emotion_label") or "unlabeled"),
                "sentiment_label": str(item.get("sentiment_label") or "neutral"),
                "confidence": float(item.get("confidence", 0.0)),
                "notes": list(item.get("notes", [])),
                "source": "model",
            }
            for item in analysis.get("turn_annotations", [])
            if str(item.get("turn_id") or "").strip()
        }
        updates["openai_human_summary"] = str(analysis.get("human_summary") or "")
        if isinstance(analysis.get("report_enrichment"), dict):
            updates["openai_report_enrichment"] = analysis["report_enrichment"]
    updates["openai_provider_used"] = True
    updates["openai_provider_warnings"] = warnings
    _save_provider_cache(
        job_id,
        "openai-role-analysis",
        {
            "provider_key": "openai_audio_analysis",
            "warnings": warnings,
            "transcription_model": transcription.get("model"),
            "analysis_model": analysis.get("model") if analysis else None,
        },
    )
    return (
        updates,
        warnings,
        ProviderDecision(
            kind="role_analysis",
            provider_key="openai_audio_analysis",
            used=bool(transcript or analysis),
            cached=False,
            status="ready" if transcript or analysis else "fallback",
            notes=list(warnings),
        ),
    )


def build_speaker_role_summary(
    speakers: list[SpeakerSummary],
    turns: list[TurnModel],
    metadata: dict[str, Any] | None = None,
) -> SpeakerRoleSummary:
    metadata = metadata or {}
    known_speakers = [speaker.speaker_id for speaker in speakers] or sorted({turn.speaker_id for turn in turns})
    hint_source = str(metadata.get("speaker_role_hint_source") or "metadata_hint")
    hint_assignments = dict(metadata.get("speaker_role_hints") or {})
    if metadata.get("human_speaker_hint"):
        hint_assignments.setdefault(str(metadata["human_speaker_hint"]), "human")
    if metadata.get("ai_speaker_hint"):
        hint_assignments.setdefault(str(metadata["ai_speaker_hint"]), "ai")
    detail_rows = {str(item.get("speaker_id")): item for item in metadata.get("openai_speaker_role_details", [])}
    role_notes: list[str] = []
    assignments: list[SpeakerRoleAssignment] = []

    def heuristic_role(speaker_id: str) -> tuple[SpeakerRole, float, list[str]]:
        speaker_turns = [turn for turn in turns if turn.speaker_id == speaker_id]
        combined = " ".join(turn.text.lower() for turn in speaker_turns[:3])
        ai_markers = ["how can i help", "virtual assistant", "ai assistant", "automated", "thank you for calling", "i can help you", "assistant"]
        human_markers = ["um", "uh", "not sure", "i think", "maybe", "can you", "could you"]
        if any(marker in combined for marker in ai_markers):
            return "ai", 0.68, ["heuristic_conversational_pattern"]
        if any(marker in combined for marker in human_markers):
            return "human", 0.61, ["heuristic_conversational_pattern"]
        return "unknown", 0.0, ["insufficient_role_signal"]

    for speaker_id in known_speakers:
        if speaker_id in hint_assignments:
            detail = detail_rows.get(speaker_id, {})
            assignments.append(
                SpeakerRoleAssignment(
                    speaker_id=speaker_id,
                    speaker_role=str(hint_assignments[speaker_id]),
                    confidence=float(detail.get("confidence", 0.92 if hint_source == "manual_override" else 0.78)),
                    source=hint_source if hint_source in {"manual_override", "model"} else "metadata_hint",
                    notes=list(detail.get("notes", [])) or [f"{hint_source}_speaker_role"],
                )
            )
            continue
        role, confidence, notes = heuristic_role(speaker_id)
        assignments.append(
            SpeakerRoleAssignment(
                speaker_id=speaker_id,
                speaker_role=role,
                confidence=confidence,
                source="heuristic" if role != "unknown" else "unavailable",
                notes=notes,
            )
        )

    primary_human = next((assignment.speaker_id for assignment in assignments if assignment.speaker_role == "human"), None)
    primary_ai = next((assignment.speaker_id for assignment in assignments if assignment.speaker_role == "ai"), None)
    if not primary_human and assignments:
        primary_human = assignments[0].speaker_id
        role_notes.append("defaulted_primary_human_to_dominant_speaker")
    return SpeakerRoleSummary(
        primary_human_speaker_id=primary_human,
        primary_ai_speaker_id=primary_ai,
        assignments=assignments,
        notes=role_notes,
    )


def _role_map(role_summary: SpeakerRoleSummary | None) -> dict[str, SpeakerRole]:
    if not role_summary:
        return {}
    return {assignment.speaker_id: assignment.speaker_role for assignment in role_summary.assignments}


def apply_speaker_roles(
    speakers: list[SpeakerSummary],
    turns: list[TurnModel],
    role_summary: SpeakerRoleSummary,
) -> tuple[list[SpeakerSummary], list[TurnModel]]:
    role_assignments = {assignment.speaker_id: assignment for assignment in role_summary.assignments}
    for speaker in speakers:
        assignment = role_assignments.get(speaker.speaker_id)
        if assignment:
            speaker.speaker_role = assignment.speaker_role
            speaker.role_confidence = assignment.confidence
            speaker.role_source = assignment.source
    for turn in turns:
        assignment = role_assignments.get(turn.speaker_id)
        if assignment:
            turn.speaker_role = assignment.speaker_role
    return speakers, turns


def _speaker_at_timestamp(diarization: DiarizationSummary, timestamp_ms: int) -> str | None:
    for segment in diarization.segments:
        if segment.start_ms <= timestamp_ms <= segment.end_ms:
            return segment.speaker_id
    return None


def build_nonverbal_cues(
    job_id: str,
    metadata: dict[str, Any],
    diarization: DiarizationSummary,
    prosody_tracks: list[ProsodyTrack],
    turns: list[TurnModel],
    questions: list[QuestionAnalyticsRow],
    quality: QualitySummary,
    words: list[WordTimestamp] | None = None,
    events: list[EventModel] | None = None,
    acoustic_cues: list[NonverbalCue] | None = None,
) -> list[NonverbalCue]:
    cues: list[NonverbalCue] = []
    words = words or []
    events = events or []
    acoustic_cues = acoustic_cues or []
    source_type = str(metadata.get("source_type") or "direct_audio_file")
    strong_diarization = diarization.readiness_state == "ready"

    for index, cue in enumerate(metadata.get("benchmark_nonverbal_cues", [])):
        cue_type = str(cue.get("type", "vocal_sound"))
        confidence = float(cue.get("confidence", 0.98))
        speaker_id = cue.get("speaker_id")
        cues.append(
            NonverbalCue(
                cue_id=str(cue.get("cue_id", f"{job_id}-cue-{index}")),
                type=cue_type,
                family=str(cue.get("family", "vocal_sound")),
                label=str(cue.get("label", cue_type.replace("_", " "))),
                start_ms=int(cue.get("start_ms", 0)),
                end_ms=int(cue.get("end_ms", cue.get("start_ms", 0))),
                confidence=confidence,
                source="benchmark_label",
                display_state=confidence_display_state(confidence, label=cue_type, visible_threshold=0.65, muted_threshold=0.45),
                attribution_state="strong" if speaker_id else "unassigned",
                speaker_id=str(speaker_id) if speaker_id else None,
                evidence_refs=[EvidenceRef(kind="benchmark", ref_id=str(cue.get("benchmark_id", cue_type)), label=str(cue.get("label", cue_type)))],
                explainability_mask=["benchmark_label"],
            )
        )

    pitch_track = next((track for track in prosody_tracks if track.key == "pitch_hz"), None)
    energy_track = next((track for track in prosody_tracks if track.key == "energy_rms"), None)

    if pitch_track:
        last_pitch_spike_ms = -10_000
        for previous, current in zip(pitch_track.samples, pitch_track.samples[1:]):
            if (
                current.value > previous.value * 1.28
                and current.value - previous.value >= 32
                and current.timestamp_ms - last_pitch_spike_ms >= 900
            ):
                speaker_id = _speaker_at_timestamp(diarization, current.timestamp_ms) if strong_diarization else None
                cues.append(
                    NonverbalCue(
                        cue_id=f"{job_id}-pitch-{current.timestamp_ms}",
                        type="pitch_spike",
                        family="prosody",
                        label="pitch spike",
                        start_ms=current.timestamp_ms,
                        end_ms=current.timestamp_ms + 220,
                        confidence=0.62 if strong_diarization else 0.48,
                        source="heuristic",
                        display_state="muted" if source_type == "direct_audio_file" and not strong_diarization else "visible",
                        attribution_state="strong" if speaker_id else ("muted" if source_type != "direct_audio_file" else "unassigned"),
                        speaker_id=speaker_id,
                        evidence_refs=[EvidenceRef(kind="prosody_track", ref_id="pitch_hz", label="Pitch")],
                        explainability_mask=["heuristic_prosody"],
                    )
                )
                last_pitch_spike_ms = current.timestamp_ms

    if energy_track:
        last_energy_spike_ms = -10_000
        for previous, current in zip(energy_track.samples, energy_track.samples[1:]):
            if (
                current.value > previous.value * 1.4
                and current.value >= 0.08
                and current.timestamp_ms - last_energy_spike_ms >= 1200
            ):
                speaker_id = _speaker_at_timestamp(diarization, current.timestamp_ms) if strong_diarization else None
                cues.append(
                    NonverbalCue(
                        cue_id=f"{job_id}-energy-{current.timestamp_ms}",
                        type="energy_spike",
                        family="prosody",
                        label="energy spike",
                        start_ms=current.timestamp_ms,
                        end_ms=current.timestamp_ms + 220,
                        confidence=0.58,
                        source="heuristic",
                        display_state="muted",
                        attribution_state="strong" if speaker_id else "muted",
                        speaker_id=speaker_id,
                        evidence_refs=[EvidenceRef(kind="prosody_track", ref_id="energy_rms", label="Energy")],
                        explainability_mask=["heuristic_prosody"],
                    )
                )
                last_energy_spike_ms = current.timestamp_ms

    cues.extend(acoustic_cues)
    cues.extend(
        detect_textual_vocal_cues(
            job_id=job_id,
            turns=turns,
            words=words,
            diarization=diarization,
            strong_diarization=strong_diarization,
            source_type=source_type,
        )
    )

    for event in events:
        if event.type != "backchannel":
            continue
        speaker_id = event.speaker_ids[0] if strong_diarization and event.speaker_ids else None
        cues.append(
            NonverbalCue(
                cue_id=f"{job_id}-event-{event.event_id}",
                type="backchannel",
                family="conversational",
                label=event.label or "backchannel",
                start_ms=event.begin_ms,
                end_ms=event.end_ms,
                confidence=max(0.45, event.confidence or 0.58),
                source="heuristic",
                display_state="visible" if strong_diarization or source_type != "direct_audio_file" else "muted",
                attribution_state="strong" if speaker_id else ("muted" if source_type != "direct_audio_file" else "unassigned"),
                speaker_id=speaker_id,
                evidence_refs=list(event.evidence_refs),
                explainability_mask=["event_backchannel"],
            )
        )

    answer_turns = {turn.turn_id: turn for turn in turns}
    for question in questions:
        if question.hesitation_score < 55:
            continue
        answer_turn = answer_turns.get(question.answer_turn_id)
        if not answer_turn:
            continue
        speaker_id = answer_turn.speaker_id if strong_diarization else None
        explainability = list(question.explainability_mask)
        if quality.avg_snr_db is not None and quality.avg_snr_db < 10:
            explainability.append("low_snr")
        cues.append(
            NonverbalCue(
                cue_id=f"{job_id}-hesitation-{question.question_id}",
                type="hesitation_onset",
                family="prosody",
                label="hesitation",
                start_ms=max(0, answer_turn.start_ms - min(question.response_latency_ms, 600)),
                end_ms=answer_turn.start_ms,
                confidence=0.7 if not explainability else 0.54,
                source="heuristic",
                display_state="visible" if not explainability else "muted",
                attribution_state="strong" if speaker_id else "muted",
                speaker_id=speaker_id,
                evidence_refs=list(question.evidence_refs),
                explainability_mask=sorted(set(explainability)),
            )
        )

    if source_type == "direct_audio_file" and not strong_diarization:
        for cue in cues:
            if cue.family == "vocal_sound":
                cue.display_state = "muted"
                cue.speaker_id = None
                cue.attribution_state = "unassigned"
                cue.explainability_mask = sorted(set(cue.explainability_mask + ["speaker_attribution_blocked"]))

    return sorted(cues, key=lambda cue: (cue.start_ms, cue.end_ms))


def _tone_for_track_item(label: str, track_type: str) -> str:
    lowered = label.lower()
    if track_type == "nonverbal":
        if "laugh" in lowered:
            return "positive"
        if "cough" in lowered or "sigh" in lowered:
            return "warning"
        return "accent"
    if track_type == "emotion":
        if lowered in {"anger", "sadness", "fear", "disgust"}:
            return "warning"
        if lowered in {"joy", "surprise"}:
            return "positive"
    if track_type in {"overlap", "interruption"}:
        return "warning"
    return "default"


def build_timeline_tracks(
    diarization: DiarizationSummary,
    content: ContentSummary,
    turns: list[TurnModel],
    questions: list[QuestionAnalyticsRow],
    nonverbal_cues: list[NonverbalCue],
    events: list[EventModel],
) -> list[TimelineTrack]:
    turn_lookup = {turn.turn_id: turn for turn in turns}
    speaker_items = [
        TimelineTrackItem(
            item_id=segment.segment_id,
            label=segment.label or segment.speaker_id,
            start_ms=segment.start_ms,
            end_ms=segment.end_ms,
            tone="default",
            speaker_id=segment.speaker_id,
            confidence=segment.confidence,
        )
        for segment in diarization.segments
    ]
    transcript_items = [
        TimelineTrackItem(
            item_id=sentence.sentence_id,
            label=sentence.emotion_label if sentence.display_state in {"visible", "muted"} else sentence.speaker_id,
            start_ms=sentence.start_ms,
            end_ms=sentence.end_ms,
            tone=_tone_for_track_item(sentence.emotion_label, "emotion"),
            speaker_id=sentence.speaker_id,
            confidence=sentence.confidence,
            evidence_refs=sentence.evidence_refs,
        )
        for sentence in content.sentences
    ]
    question_items = [
        TimelineTrackItem(
            item_id=question.question_id,
            label=question.affect_tag,
            start_ms=(turn_lookup.get(question.question_turn_id).start_ms if turn_lookup.get(question.question_turn_id) else 0),
            end_ms=(turn_lookup.get(question.answer_turn_id).end_ms if turn_lookup.get(question.answer_turn_id) else question.answer_duration_ms),
            tone="accent",
            confidence=float(question.hesitation_score) / 100,
            evidence_refs=question.evidence_refs,
        )
        for question in questions
    ]
    nonverbal_items = [
        TimelineTrackItem(
            item_id=cue.cue_id,
            label=cue.label,
            start_ms=cue.start_ms,
            end_ms=cue.end_ms,
            tone=_tone_for_track_item(cue.label, "nonverbal"),
            speaker_id=cue.speaker_id,
            confidence=cue.confidence,
            evidence_refs=cue.evidence_refs,
        )
        for cue in nonverbal_cues
        if cue.family == "vocal_sound" and cue.display_state in {"visible", "muted"}
    ]
    prosody_items = [
        TimelineTrackItem(
            item_id=cue.cue_id,
            label=cue.label,
            start_ms=cue.start_ms,
            end_ms=cue.end_ms,
            tone="accent",
            speaker_id=cue.speaker_id,
            confidence=cue.confidence,
            evidence_refs=cue.evidence_refs,
        )
        for cue in nonverbal_cues
        if cue.family == "prosody" and cue.display_state in {"visible", "muted"}
    ]
    overlap_items = [
        TimelineTrackItem(
            item_id=f"overlap-{index}",
            label=window.label or "overlap",
            start_ms=window.start_ms,
            end_ms=window.end_ms,
            tone="warning",
        )
        for index, window in enumerate(diarization.overlap_windows)
    ] + [
        TimelineTrackItem(
            item_id=event.event_id,
            label=event.type,
            start_ms=event.begin_ms,
            end_ms=event.end_ms,
            tone="warning" if event.type in {"interruption", "backchannel"} else "default",
            confidence=event.confidence,
            evidence_refs=event.evidence_refs,
        )
        for event in events
        if event.type in {"interruption", "backchannel"}
    ]
    evidence_items = [
        TimelineTrackItem(
            item_id=f"evidence-{index}",
            label=ref.label or ref.ref_id,
            start_ms=item.start_ms,
            end_ms=item.start_ms + 260,
            tone="default",
            evidence_refs=[ref],
        )
        for index, item in enumerate(transcript_items[:8])
        for ref in item.evidence_refs[:1]
    ]
    return [
        TimelineTrack(
            track_id="speaker-lanes",
            label="Speaker lanes",
            type="speaker",
            status=diarization.readiness_state,
            items=speaker_items,
            notes=list(diarization.notes),
        ),
        TimelineTrack(track_id="transcript-emotion", label="Transcript / sentence emotion", type="emotion", items=transcript_items),
        TimelineTrack(track_id="questions", label="Questions", type="question", items=question_items),
        TimelineTrack(
            track_id="nonverbal",
            label="Non-verbal cues",
            type="nonverbal",
            status="ready" if nonverbal_items else ("blocked" if diarization.readiness_state == "blocked" else "fallback"),
            items=nonverbal_items,
            notes=["Confidence-gated vocal cues appear here when the evidence posture supports them."],
        ),
        TimelineTrack(track_id="prosody-events", label="Prosody events", type="prosody", items=prosody_items),
        TimelineTrack(track_id="overlap", label="Overlap / interruption", type="overlap", items=overlap_items),
        TimelineTrack(track_id="evidence", label="Evidence refs", type="evidence", items=evidence_items),
    ]


def naive_lang_mix(transcript: str, language_hint: str | None = None) -> LangMixPrediction:
    hint = (language_hint or "").strip().lower()
    if transcript.strip():
        ascii_chars = sum(1 for char in transcript if char.isascii() and char.isalpha())
        letter_chars = sum(1 for char in transcript if char.isalpha())
        english_ratio = ascii_chars / letter_chars if letter_chars else 0.0
        if english_ratio > 0.9:
            label = "english"
        elif english_ratio > 0.6:
            label = f"{hint[:2]}_en" if hint and hint not in {"english", "en"} else "mixed"
        elif hint:
            label = hint[:2]
        else:
            label = "non_english"
        language_ratios = {"english": round(english_ratio, 3)}
        if hint and hint not in {"english", "en"}:
            language_ratios[hint[:2]] = round(1 - english_ratio, 3)
        return LangMixPrediction(
            label=label,
            english_ratio=round(english_ratio, 3),
            language_ratios=language_ratios,
            source="heuristic",
            display_state="visible" if english_ratio >= PROFILE_MUTED_THRESHOLD else "muted",
            summary="Transcript character distribution used as a lightweight language-mix proxy.",
            warning_flags=["heuristic_language_mix"],
        )
    if hint in {"english", "en"}:
        return LangMixPrediction(
            label="english",
            english_ratio=1.0,
            language_ratios={"english": 1.0},
            source="metadata_hint",
            display_state="muted",
            summary="Language hint supplied the language-mix fallback.",
            warning_flags=["language_hint_used"],
        )
    if hint:
        return LangMixPrediction(
            label=hint[:2],
            english_ratio=0.0,
            language_ratios={hint[:2]: 1.0},
            source="metadata_hint",
            display_state="muted",
            summary="Language hint supplied the language-mix fallback.",
            warning_flags=["language_hint_used"],
        )
    return LangMixPrediction(label="unknown")


def maybe_transcribe(job_id: str, audio_path: Path, transcript_hint: str | None = None) -> TranscriptionOutcome:
    cache_path = _provider_cache_path(job_id, "transcription")
    cached = load_transcription_cache(cache_path)
    if cached and cached.get("provider_key") == "faster_whisper":
        words = _normalize_provider_words(list(cached.get("words", [])), source="model")
        transcript = str(cached.get("transcript") or "")
        return TranscriptionOutcome(
            transcript=transcript,
            words=words,
            warnings=[],
            provider=ProviderDecision(
                kind="transcription",
                provider_key="faster_whisper",
                used=bool(transcript),
                cached=True,
                status="ready" if transcript else "fallback",
                notes=["transcription_cache_reused"],
            ),
        )

    model_name = os.environ.get("SPECTRUM_WHISPER_MODEL", "tiny")
    transcript, words, warnings = transcribe_with_faster_whisper(audio_path, model_name=model_name)
    if transcript:
        save_transcription_cache(
            cache_path,
            {
                "provider_key": "faster_whisper",
                "model": model_name,
                "transcript": transcript,
                "words": words,
            },
        )
        return TranscriptionOutcome(
            transcript=transcript,
            words=words,
            warnings=warnings,
            provider=ProviderDecision(
                kind="transcription",
                provider_key="faster_whisper",
                used=True,
                cached=False,
                status="ready",
                notes=[],
            ),
        )

    if "asr_model_unavailable" in warnings:
        if transcript_hint:
            return TranscriptionOutcome(
                transcript=transcript_hint,
                warnings=["transcript_hint_used", *warnings],
                provider=ProviderDecision(
                    kind="transcription",
                    provider_key="transcript_hint",
                    used=True,
                    cached=False,
                    status="fallback",
                    notes=["transcript_hint_used", *warnings],
                ),
            )
        return TranscriptionOutcome(
            transcript="",
            warnings=warnings,
            provider=ProviderDecision(
                kind="transcription",
                provider_key="faster_whisper",
                used=False,
                cached=False,
                status="blocked",
                notes=warnings,
            ),
        )

    if transcript_hint:
        warnings.append("transcript_hint_used")
        return TranscriptionOutcome(
            transcript=transcript_hint,
            warnings=warnings,
            provider=ProviderDecision(
                kind="transcription",
                provider_key="transcript_hint",
                used=True,
                cached=False,
                status="fallback",
                notes=list(warnings),
            ),
        )
    warnings = warnings or ["asr_empty_output"]
    return TranscriptionOutcome(
        transcript="",
        words=[],
        warnings=warnings,
        provider=ProviderDecision(
            kind="transcription",
            provider_key="faster_whisper",
            used=False,
            cached=False,
            status="fallback",
            notes=list(warnings),
        ),
    )


def maybe_align_words(
    job_id: str,
    audio_path: Path,
    metadata: dict[str, Any],
    provider_words: list[dict[str, Any]],
    adapters: list[Any],
) -> AlignmentOutcome:
    if not provider_words:
        return AlignmentOutcome(
            words=[],
            warnings=["alignment_missing"],
            provider=ProviderDecision(
                kind="alignment",
                provider_key="whisperx",
                used=False,
                cached=False,
                status="blocked",
                notes=["alignment_missing"],
            ),
        )

    whisperx = _adapter_lookup(adapters, "whisperx")
    if not whisperx or not whisperx.available:
        return AlignmentOutcome(
            words=provider_words,
            warnings=["alignment_missing"],
            provider=ProviderDecision(
                kind="alignment",
                provider_key="whisperx",
                used=False,
                cached=False,
                status="fallback",
                notes=["alignment_missing"],
            ),
        )

    cache_path = _provider_cache_path(job_id, "alignment")
    cached = load_alignment_cache(cache_path)
    if cached and cached.get("words"):
        words = _normalize_provider_words(list(cached.get("words", [])), source="model")
        return AlignmentOutcome(
            words=words,
            warnings=[],
            provider=ProviderDecision(
                kind="alignment",
                provider_key="whisperx",
                used=True,
                cached=True,
                status="ready",
                notes=["alignment_cache_reused"],
            ),
        )

    aligned_words, warnings = align_words_with_whisperx(
        audio_path,
        provider_words,
        language=metadata.get("language_hint"),
    )
    normalized = _normalize_provider_words(aligned_words, source="model")
    if normalized and not warnings:
        save_alignment_cache(
            cache_path,
            {
                "provider_key": "whisperx",
                "words": normalized,
            },
        )
        return AlignmentOutcome(
            words=normalized,
            warnings=[],
            provider=ProviderDecision(
                kind="alignment",
                provider_key="whisperx",
                used=True,
                cached=False,
                status="ready",
                notes=[],
            ),
        )

    return AlignmentOutcome(
        words=provider_words,
        warnings=warnings or ["alignment_missing"],
        provider=ProviderDecision(
            kind="alignment",
            provider_key="whisperx",
            used=False,
            cached=False,
            status="fallback",
            notes=warnings or ["alignment_missing"],
        ),
    )


def maybe_detect_acoustic_cues(
    job_id: str,
    prosody_tracks: list[ProsodyTrack],
    words: list[WordTimestamp],
    diarization: DiarizationSummary,
    quality: QualitySummary,
    source_type: str,
    adapters: list[Any],
) -> tuple[list[NonverbalCue], ProviderDecision]:
    cache_path = _provider_cache_path(job_id, "acoustic_cues")
    cached = load_acoustic_cue_cache(cache_path)
    if cached:
        provider_key, cues = cached
        return cues, ProviderDecision(
            kind="nonverbal_cues",
            provider_key=provider_key,
            used=bool(cues),
            cached=True,
            status="ready" if cues else "fallback",
            notes=["acoustic_cue_cache_reused"],
        )

    yamnet = _adapter_lookup(adapters, "yamnet")
    panns = _adapter_lookup(adapters, "panns")
    preferred_model = "yamnet" if yamnet and yamnet.available else "panns" if panns and panns.available else None
    provider_key = preferred_model or "acoustic_heuristic"
    cues = detect_acoustic_vocal_cues(
        job_id=job_id,
        prosody_tracks=prosody_tracks,
        words=words,
        diarization=diarization,
        quality=quality,
        source_type=source_type,
        provider_key=provider_key,
        model_backed=False,
    )
    save_acoustic_cue_cache(cache_path, provider_key, cues)
    notes = (
        [f"{preferred_model}_adapter_available_proxy_mode", "acoustic_classifier_not_wired"]
        if preferred_model
        else []
    )
    if not cues:
        notes.extend(["speaker_attribution_blocked"] if diarization.readiness_state != "ready" else ["acoustic_cues_not_detected"])
    return cues, ProviderDecision(
        kind="nonverbal_cues",
        provider_key=provider_key,
        used=bool(cues),
        cached=False,
        status="ready" if cues else "fallback",
        notes=notes,
    )


def build_quality(audio_path: Path, analysis_mode: AnalysisMode, silences: list[tuple[float, float]], metadata: dict[str, Any]) -> QualitySummary:
    duration_sec = probe_duration(audio_path)
    silence_sec = sum(end - start for start, end in silences)
    speech_ratio = clamp((duration_sec - silence_sec) / duration_sec) if duration_sec else 0.0
    avg_snr_db, clipping_ratio = waveform_stats(audio_path)
    noise_component = 0.0 if avg_snr_db is None else clamp((18.0 - avg_snr_db) / 18.0)
    noise_score = clamp((1 - speech_ratio) * 0.5 + clipping_ratio * 0.25 + noise_component * 0.25)
    noise_ratio = clamp((1 - speech_ratio) * 0.4 + clipping_ratio * 0.15 + noise_component * 0.45)
    vad_fp_count = int(metadata.get("vad_fp_count", round(noise_ratio * 10)))
    vad_fn_count = int(metadata.get("vad_fn_count", round(max(0.0, (0.55 - speech_ratio) * 8))))
    warning_flags: list[str] = ["silero_vad_fallback"]
    if analysis_mode == "voice_profile" and duration_sec < 8:
        warning_flags.append("shorter_than_voice_profile_target")
    if analysis_mode == "voice_profile" and duration_sec > 30:
        warning_flags.append("longer_than_voice_profile_target")
    if speech_ratio < 0.45:
        warning_flags.append("low_speech_ratio")
    if avg_snr_db is not None and avg_snr_db < 10:
        warning_flags.append("low_snr")
    if clipping_ratio > 0.01:
        warning_flags.append("clipping_detected")
    low_snr_windows: list[TimeWindow] = []
    if avg_snr_db is not None and avg_snr_db < 10 and duration_sec:
        low_snr_windows.append(TimeWindow(start_ms=0, end_ms=int(duration_sec * 1000), label="global_low_snr"))
    noisy_segment_count = len(low_snr_windows) + int(noise_ratio > 0.35) + sum(1 for start, end in silences if end - start < 0.6)
    return QualitySummary(
        speech_ratio=round(speech_ratio, 3),
        noise_score=round(noise_score, 3),
        noise_ratio=round(noise_ratio, 3),
        avg_snr_db=avg_snr_db,
        clipping_ratio=round(clipping_ratio, 4),
        vad_fp_count=vad_fp_count,
        vad_fn_count=vad_fn_count,
        noisy_segment_count=noisy_segment_count,
        low_snr_windows=low_snr_windows,
        is_usable=speech_ratio >= 0.45 and (avg_snr_db is None or avg_snr_db >= 6),
        warning_flags=warning_flags,
    )


def build_turns_from_metadata(
    job_id: str,
    duration_sec: float,
    transcript: str,
    metadata: dict[str, Any],
    analysis_mode: AnalysisMode,
) -> list[TurnModel]:
    speaker_segments = metadata.get("speaker_segments") or []
    turns: list[TurnModel] = []
    if speaker_segments:
        previous_end_ms: int | None = None
        for index, segment in enumerate(speaker_segments):
            start_ms = int(segment.get("start_ms", 0))
            end_ms = int(segment.get("end_ms", start_ms))
            response_latency_ms = None if previous_end_ms is None else max(0, start_ms - previous_end_ms)
            text = str(segment.get("text", "")).strip()
            turns.append(
                TurnModel(
                    turn_id=str(segment.get("turn_id", f"{job_id}-turn-{index}")),
                    speaker_id=segment.get("speaker_id", "speaker_0"),
                    start_ms=start_ms,
                    end_ms=end_ms,
                    text=text,
                    response_latency_ms=response_latency_ms,
                    filler_count=int(segment.get("filler_count", len(derive_fillers(text)))),
                    uncertainty_markers=int(segment.get("uncertainty_markers", len(derive_uncertainty_markers(text)))),
                    word_count=count_words(text),
                    confidence=float(segment.get("confidence", 0.65)),
                    source=segment.get("source", "metadata"),
                    rms_energy=_coerce_float(segment.get("rms_energy")),
                    pitch_variance=_coerce_float(segment.get("pitch_variance")),
                    noise_ratio=_coerce_float(segment.get("noise_ratio")),
                    speech_rate_wpm=_coerce_float(segment.get("speech_rate_wpm")),
                    section=segment.get("section"),
                )
            )
            previous_end_ms = end_ms
        return turns

    dialogue_turns = metadata.get("dialogue_turns") or []
    if dialogue_turns:
        total_words = sum(max(1, count_words(turn_text)) for turn_text in dialogue_turns)
        cursor_ms = 0
        speaker_sequence = metadata.get("speaker_sequence") or []
        for index, turn_text in enumerate(dialogue_turns):
            turn_words = max(1, count_words(turn_text))
            duration_ms = max(450, int(duration_sec * 1000 * (turn_words / total_words)))
            start_ms = cursor_ms
            end_ms = min(int(duration_sec * 1000), start_ms + duration_ms)
            speaker_id = speaker_sequence[index] if index < len(speaker_sequence) else f"speaker_{index % 2}"
            turns.append(
                TurnModel(
                    turn_id=f"{job_id}-turn-{index}",
                    speaker_id=speaker_id,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    text=turn_text.strip(),
                    response_latency_ms=0 if index == 0 else 180,
                    filler_count=len(derive_fillers(turn_text)),
                    uncertainty_markers=len(derive_uncertainty_markers(turn_text)),
                    word_count=turn_words,
                    confidence=0.42,
                    source="dialogue_hint",
                    speech_rate_wpm=round(turn_words / max((duration_ms / 1000) / 60, 1e-6), 2),
                )
            )
            cursor_ms = end_ms
        if turns:
            turns[-1].end_ms = max(turns[-1].end_ms, int(duration_sec * 1000))
        return turns

    if transcript:
        return [
            TurnModel(
                turn_id=f"{job_id}-turn-0",
                speaker_id="speaker_0",
                start_ms=0,
                end_ms=int(duration_sec * 1000),
                text=transcript,
                response_latency_ms=0,
                filler_count=len(derive_fillers(transcript)),
                uncertainty_markers=len(derive_uncertainty_markers(transcript)),
                word_count=count_words(transcript),
                confidence=0.25 if analysis_mode == "voice_profile" else 0.18,
                source="transcript",
                speech_rate_wpm=round(count_words(transcript) / max(duration_sec / 60, 1e-6), 2),
            )
        ]
    return []


def build_speakers(turns: list[TurnModel], duration_sec: float, metadata: dict[str, Any] | None = None) -> list[SpeakerSummary]:
    total_duration_ms = max(1, int(duration_sec * 1000))
    by_speaker: dict[str, list[TurnModel]] = {}
    metadata = metadata or {}
    speaker_hints = metadata.get("speaker_hints", {})
    for turn in turns:
        by_speaker.setdefault(turn.speaker_id, []).append(turn)
    speakers: list[SpeakerSummary] = []
    for speaker_id, speaker_turns in by_speaker.items():
        talk_ms = sum(max(0, turn.end_ms - turn.start_ms) for turn in speaker_turns)
        avg_turn_ms = talk_ms / max(1, len(speaker_turns))
        interruption_count = sum(1 for turn in speaker_turns if (turn.response_latency_ms or 9999) < 120)
        average_wpm = sum(turn.speech_rate_wpm or 0.0 for turn in speaker_turns) / max(1, sum(1 for turn in speaker_turns if turn.speech_rate_wpm))
        role = metadata.get("speaker_roles", {}).get(speaker_id) or speaker_hints.get(speaker_id, {}).get("role")
        speakers.append(
            SpeakerSummary(
                speaker_id=speaker_id,
                role=role,
                talk_ratio=round(talk_ms / total_duration_ms, 3),
                avg_turn_ms=round(avg_turn_ms, 2),
                interruption_count=interruption_count,
                overlap_ms=0.0,
                wpm=round(average_wpm, 2) if average_wpm else None,
            )
        )
    return sorted(speakers, key=lambda speaker: speaker.talk_ratio, reverse=True)


def build_events(
    job_id: str,
    turns: list[TurnModel],
    silences: list[tuple[float, float]],
    quality: QualitySummary,
    duration_sec: float,
    metadata: dict[str, Any] | None = None,
) -> list[EventModel]:
    events: list[EventModel] = []
    metadata = metadata or {}
    for index, (start, end) in enumerate(silences):
        duration = end - start
        if duration < 1.0:
            continue
        events.append(
            EventModel(
                event_id=f"{job_id}-pause-{index}",
                type="long_pause",
                begin_ms=int(start * 1000),
                end_ms=int(end * 1000),
                severity="warning" if duration > 1.5 else "info",
                confidence=0.55,
                evidence_refs=[EvidenceRef(kind="silence", ref_id=f"silence:{index}")],
                detail="Silence span detected by ffmpeg silencedetect.",
            )
        )

    for index in range(1, len(turns)):
        previous_turn = turns[index - 1]
        turn = turns[index]
        if turn.start_ms < previous_turn.end_ms:
            overlap_ms = previous_turn.end_ms - turn.start_ms
            overlap_type = "backchannel" if overlap_ms < 400 else "interruption"
            events.append(
                EventModel(
                    event_id=f"{job_id}-overlap-{index}",
                    type=overlap_type,
                    begin_ms=turn.start_ms,
                    end_ms=previous_turn.end_ms,
                    speaker_ids=[previous_turn.speaker_id, turn.speaker_id],
                    severity="warning" if overlap_ms >= 400 else "info",
                    confidence=0.45,
                    evidence_refs=[EvidenceRef(kind="turn", ref_id=previous_turn.turn_id), EvidenceRef(kind="turn", ref_id=turn.turn_id)],
                    detail="Estimated overlap from aligned turns.",
                    label="short_overlap_backchannel" if overlap_type == "backchannel" else "speaker_takeover_overlap",
                )
            )
        elif (turn.response_latency_ms or 0) < 150 and turn.speaker_id != previous_turn.speaker_id:
            events.append(
                EventModel(
                    event_id=f"{job_id}-interrupt-{index}",
                    type="interruption",
                    begin_ms=turn.start_ms,
                    end_ms=turn.end_ms,
                    speaker_ids=[previous_turn.speaker_id, turn.speaker_id],
                    severity="warning",
                    confidence=0.4,
                    evidence_refs=[EvidenceRef(kind="turn", ref_id=previous_turn.turn_id), EvidenceRef(kind="turn", ref_id=turn.turn_id)],
                    detail="Low response latency suggests an interruption.",
                )
            )

    if quality.avg_snr_db is not None and quality.avg_snr_db < 10 and duration_sec:
        events.append(
            EventModel(
                event_id=f"{job_id}-low-snr",
                type="low_snr_segment",
                begin_ms=0,
                end_ms=int(duration_sec * 1000),
                severity="critical" if quality.avg_snr_db < 8 else "warning",
                confidence=0.62,
                evidence_refs=[EvidenceRef(kind="quality", ref_id="avg_snr_db")],
                detail="Global low-SNR condition inferred from the normalized waveform.",
            )
        )

    if quality.vad_fp_count:
        events.append(
            EventModel(
                event_id=f"{job_id}-vad-fp",
                type="vad_false_positive",
                begin_ms=0,
                end_ms=min(900, int(duration_sec * 1000)),
                severity="warning",
                confidence=0.35,
                evidence_refs=[EvidenceRef(kind="quality", ref_id="vad_fp_count")],
                detail="Heuristic VAD false-positive count inferred from noise burden.",
            )
        )
    if quality.vad_fn_count:
        events.append(
            EventModel(
                event_id=f"{job_id}-vad-fn",
                type="vad_false_negative",
                begin_ms=max(0, int(duration_sec * 1000) - 900),
                end_ms=int(duration_sec * 1000),
                severity="info",
                confidence=0.28,
                evidence_refs=[EvidenceRef(kind="quality", ref_id="vad_fn_count")],
                detail="Heuristic VAD false-negative count inferred from low-speech sections.",
            )
        )

    for raw_event in metadata.get("events", []):
        events.append(
            EventModel(
                event_id=str(raw_event.get("event_id", f"{job_id}-event-{len(events)}")),
                type=str(raw_event.get("type", "event")),
                begin_ms=int(raw_event.get("begin_ms", raw_event.get("time_ms", 0))),
                end_ms=int(raw_event.get("end_ms", raw_event.get("time_ms", 0)) + raw_event.get("duration_ms", 0)),
                speaker_ids=[raw_event["speaker_id"]] if raw_event.get("speaker_id") else list(raw_event.get("speaker_ids", [])),
                severity=_severity_from_value(raw_event.get("severity")),
                confidence=float(raw_event.get("confidence", 0.72)),
                evidence_refs=[EvidenceRef(kind="turn", ref_id=raw_event["speaker_id"], label=str(raw_event.get("label", "")))] if raw_event.get("speaker_id") else [],
                detail=str(raw_event.get("detail", raw_event.get("label", ""))) or None,
                label=raw_event.get("label"),
            )
        )

    return sorted(events, key=lambda event: (event.begin_ms, event.end_ms))


def hint_prediction(label: str | None, confidence: float, warning: str) -> LabelPrediction:
    if not label:
        return LabelPrediction()
    return LabelPrediction(label=label, confidence=confidence, source="metadata_hint", summary="Metadata hints provided this field.", warning_flags=[warning])


def build_profile(
    analysis_mode: AnalysisMode,
    metadata: dict[str, Any],
    transcript: str,
    quality: QualitySummary,
    speakers: list[SpeakerSummary],
    options: ProcessSessionOptions,
    *,
    audio_path: Path | None = None,
    adapters: list[Any] | None = None,
) -> tuple[ProfileSummary, list[ProfileField], ProfileCoverageSummary, ProviderDecision]:
    source_type = str(metadata.get("source_type") or "direct_audio_file")
    dataset_id = str(metadata.get("dataset_id") or "")
    trusted_metadata = source_type in {"demo_pack_zip", "materialized_audio_dataset"} or dataset_id in {"ravdess_speech_16k", "meld"}
    adapters = adapters or build_adapter_inventory()
    accent_signal = infer_accent_broad_signal(audio_path or Path("."), metadata, trusted_metadata=trusted_metadata, adapters=adapters)
    accent_broad = finalize_label_prediction(
        LabelPrediction(
            label=accent_signal["label"],
            confidence=float(accent_signal["confidence"]),
            source=accent_signal["source"],
            summary=accent_signal["summary"],
            warning_flags=list(accent_signal["warning_flags"]),
        ),
        confidence=float(accent_signal["confidence"]),
        source=accent_signal["source"],
        summary=accent_signal["summary"],
        warning_flags=list(accent_signal["warning_flags"]),
    )
    accent_fine = finalize_label_prediction(
        hint_prediction(metadata.get("accent_fine_hint"), 0.42, "metadata_hint_not_model_inference")
        if metadata.get("accent_fine_hint") and accent_broad.label == "indian" and analysis_mode in {"voice_profile", "full"}
        else LabelPrediction(),
        confidence=0.42 if metadata.get("accent_fine_hint") and accent_broad.label == "indian" else 0.0,
        source="metadata_hint" if metadata.get("accent_fine_hint") and accent_broad.label == "indian" else "unavailable",
        summary="Fine accent stays internal until a dedicated benchmarked model path is wired for production.",
        warning_flags=["internal_only_fine_accent"] if accent_broad.label == "indian" else ["global_english_production_mode"],
    )
    accent_fine.display_state = "hidden"

    dominant_speaker = speakers[0].speaker_id if speakers else None
    speaker_hints = metadata.get("speaker_hints", {})
    dominant_hints = speaker_hints.get(dominant_speaker or "", {})
    if not dominant_hints and speaker_hints:
        dominant_hints = next(iter(speaker_hints.values()))
    voice_signal = infer_voice_presentation_signal({**metadata, "speaker_hints": speaker_hints}, trusted_metadata=trusted_metadata)
    voice_presentation = finalize_label_prediction(
        LabelPrediction(
            label=str(voice_signal["label"]),
            confidence=float(voice_signal["confidence"]),
            source=voice_signal["source"],
            summary=voice_signal["summary"],
            warning_flags=list(voice_signal["warning_flags"]),
        ),
        confidence=float(voice_signal["confidence"]),
        source=voice_signal["source"],
        summary=voice_signal["summary"],
        warning_flags=list(voice_signal["warning_flags"]),
    )
    age_signal = infer_age_signal({**metadata, "speaker_hints": speaker_hints}, trusted_metadata=trusted_metadata)
    age_band = derive_age_band(age_signal["age"], confidence=float(age_signal["confidence"])) if age_signal["age"] is not None else LabelPrediction()
    age_band = finalize_label_prediction(
        age_band,
        source=age_signal["source"],
        confidence=float(age_signal["confidence"]),
        summary=age_signal["summary"],
        warning_flags=list(age_signal["warning_flags"]),
    )

    if source_type == "direct_audio_file":
        if voice_presentation.label != "unknown" and voice_presentation.source != "benchmark_label":
            voice_presentation.warning_flags.append("trusted_metadata_required")
            voice_presentation.summary = "Voice presentation stays hidden on ad hoc uploads unless benchmark-backed or trusted metadata explicitly supports it."
            voice_presentation.display_state = "hidden"
        if age_band.label != "unknown" and age_band.source not in {"benchmark_label", "metadata_hint"}:
            age_band.warning_flags.append("trusted_metadata_required")
            age_band.summary = "Age-band output stays hidden on ad hoc uploads unless benchmark-backed or trusted metadata supports it."
            age_band.display_state = "hidden"
        if age_band.label != "unknown" and age_band.source == "metadata_hint" and not trusted_metadata:
            age_band.warning_flags.append("trusted_metadata_required")
            age_band.display_state = "hidden"
        if voice_presentation.label != "unknown" and voice_presentation.source == "metadata_hint" and not trusted_metadata:
            voice_presentation.warning_flags.append("trusted_metadata_required")
            voice_presentation.display_state = "hidden"

    if not quality.is_usable:
        for prediction in (accent_broad, accent_fine, voice_presentation, age_band):
            prediction.warning_flags.append("low_quality_clip")
            if prediction.display_state == "visible":
                prediction.display_state = "muted"

    accent_broad = finalize_label_prediction(
        accent_broad,
        confidence=accent_broad.confidence,
        source=accent_broad.source,
        summary=accent_broad.summary or "Broad accent uses the strongest available benchmark, metadata, or configured model signal.",
    )
    accent_fine = finalize_label_prediction(
        accent_fine,
        confidence=accent_fine.confidence,
        source=accent_fine.source,
        summary=accent_fine.summary or "Fine accent stays hidden in Global English production mode.",
    )
    voice_presentation = finalize_label_prediction(
        voice_presentation,
        confidence=voice_presentation.confidence,
        source=voice_presentation.source,
        summary=voice_presentation.summary or "Voice presentation is a soft proxy and remains hidden when support is weak.",
    )
    lang_mix = finalize_lang_mix(naive_lang_mix(transcript, metadata.get("language_hint")))

    profile = ProfileSummary(
        accent_broad=accent_broad,
        accent_fine=accent_fine,
        voice_presentation=voice_presentation,
        age_band=age_band,
        lang_mix=lang_mix,
    )
    display = [
        profile_field_from_prediction("accent_broad", "Broad Accent", accent_broad),
        profile_field_from_prediction("accent_fine", "Fine Accent", accent_fine),
        profile_field_from_prediction("voice_presentation", "Voice Presentation", voice_presentation),
        profile_field_from_prediction("age_band", "Age Band", age_band),
        profile_field_from_prediction("lang_mix", "Language Mix", lang_mix, value=lang_mix.label, summary=lang_mix.summary),
    ]
    if speakers:
        average_wpm = speakers[0].wpm or 0.0
        prosody_posture = "measured" if average_wpm >= 140 else "steady" if average_wpm >= 95 else "measured_slow"
        display.append(
            ProfileField(
                key="speaking_rate_baseline",
                label="Speaking Rate Baseline",
                value=f"{round(average_wpm, 1)} wpm" if average_wpm else "unknown",
                confidence=0.58 if average_wpm else 0.0,
                source="heuristic",
                display_state="visible" if average_wpm else "unavailable",
                summary="Dominant-speaker speaking rate gives the profile panel a baseline pacing anchor.",
                details={"dominant_speaker": speakers[0].speaker_id, "prosody_posture": prosody_posture},
            )
        )
    coverage = ProfileCoverageSummary(
        model_backed_fields=[field.key for field in display if field.source == "model" and field.display_state in {"visible", "muted"}],
        metadata_only_fields=[field.key for field in display if field.source in {"metadata_hint", "benchmark_label"} and field.display_state in {"visible", "muted"}],
        hidden_fields=[field.key for field in display if field.display_state == "hidden"],
        unavailable_fields=[field.key for field in display if field.display_state == "unavailable"],
    )
    provider_key = "speechbrain_commonaccent" if accent_broad.source == "model" else "metadata_profile" if coverage.metadata_only_fields else "heuristic_profile"
    provider_status: StageState = "ready" if any(field.display_state in {"visible", "muted"} for field in display) else "fallback"
    provider_notes = sorted({warning for field in display for warning in field.warning_flags})
    return (
        profile,
        display,
        coverage,
        ProviderDecision(
            kind="profile",
            provider_key=provider_key,
            used=provider_status == "ready",
            cached=False,
            status=provider_status,
            notes=provider_notes,
        ),
    )


def build_metrics(
    duration_sec: float,
    transcript: str,
    quality: QualitySummary,
    speakers: list[SpeakerSummary],
    turns: list[TurnModel],
    events: list[EventModel],
    questions: list[QuestionAnalyticsRow] | None = None,
    speaker_roles: SpeakerRoleSummary | None = None,
) -> dict[str, MetricSummary]:
    role_map = _role_map(speaker_roles)
    focus_turns = [turn for turn in turns if role_map.get(turn.speaker_id, turn.speaker_role) == "human"] or turns
    focus_transcript = " ".join(turn.text for turn in focus_turns if turn.text.strip()) or transcript
    focus_speakers = [speaker for speaker in speakers if role_map.get(speaker.speaker_id, speaker.speaker_role) == "human"] or speakers
    word_count = count_words(focus_transcript)
    speech_minutes = max(duration_sec * max(quality.speech_ratio, 0.01) / 60.0, 1e-6)
    speech_rate = round(word_count / speech_minutes, 2) if word_count else 0.0
    avg_turn_ms = round(sum(max(0, turn.end_ms - turn.start_ms) for turn in focus_turns) / max(1, len(focus_turns)), 2) if focus_turns else 0.0
    interruption_count = sum(1 for event in events if event.type == "interruption" and (not event.speaker_ids or any(role_map.get(speaker_id) == "human" for speaker_id in event.speaker_ids)))
    overlap_ms = sum(max(0, event.end_ms - event.begin_ms) for event in events if event.type in {"backchannel", "interruption"})
    response_latencies = [turn.response_latency_ms for turn in focus_turns if turn.response_latency_ms is not None and turn.response_latency_ms > 0]
    response_latency_ms = round(sum(response_latencies) / len(response_latencies), 2) if response_latencies else 0.0
    talk_ratio = focus_speakers[0].talk_ratio if focus_speakers else 1.0
    hesitation_score = round(sum(row.hesitation_score for row in questions or []) / max(1, len(questions or [])), 2)
    return {
        "speech_ratio": MetricSummary(name="Speech Ratio", value=quality.speech_ratio, unit="ratio", confidence=0.7, description="Share of the clip treated as speech after silence analysis."),
        "noise_score": MetricSummary(name="Noise Score", value=quality.noise_score, unit="ratio", confidence=0.45, description="Heuristic noise estimate based on waveform dynamics and silence burden."),
        "noise_ratio": MetricSummary(name="Noise Ratio", value=quality.noise_ratio, unit="ratio", confidence=0.42, description="Share of the session affected by environmental contamination heuristics."),
        "avg_snr_db": MetricSummary(name="Average SNR", value=quality.avg_snr_db, unit="dB", confidence=0.4, description="Approximate signal-to-noise ratio estimate from the normalized waveform."),
        "speech_rate_wpm": MetricSummary(name="Speech Rate", value=speech_rate, unit="wpm", confidence=0.35 if transcript else 0.0, description="Words per minute across the detected speech duration."),
        "talk_ratio": MetricSummary(name="Talk Ratio", value=talk_ratio, unit="ratio", confidence=0.3 if len(speakers) > 1 else 0.18, description="Share of total talking time attributed to the dominant speaker."),
        "avg_turn_ms": MetricSummary(name="Average Turn Length", value=avg_turn_ms, unit="ms", confidence=0.35 if turns else 0.0, description="Average detected or estimated turn duration."),
        "interruption_count": MetricSummary(name="Interruption Count", value=interruption_count, unit="count", confidence=0.25 if len(turns) > 1 else 0.0, description="Estimated count of low-latency or overlapping turn takeovers."),
        "overlap_ms": MetricSummary(name="Overlap", value=overlap_ms, unit="ms", confidence=0.22 if overlap_ms else 0.0, description="Estimated overlapping speech duration from turn alignment."),
        "response_latency_ms": MetricSummary(name="Response Latency", value=response_latency_ms, unit="ms", confidence=0.28 if response_latency_ms else 0.0, description="Average time between the end of one turn and the start of the next."),
        "hesitation_score": MetricSummary(name="Hesitation Score", value=hesitation_score, unit="score", confidence=0.46 if questions else 0.0, description="Blended hesitation score across derived question-answer pairs."),
    }


def normalize_emotion_label(label: str | None) -> str:
    lowered = str(label or "").strip().lower()
    mapping = {
        "happy": "joy",
        "joyful": "joy",
        "sad": "sadness",
        "angry": "anger",
        "surprised": "surprise",
        "fearful": "fear",
        "disgusted": "disgust",
        "calm": "calm",
    }
    if lowered in mapping:
        return mapping[lowered]
    return lowered or "unlabeled"


def _sentence_explainability_mask(quality: QualitySummary, events: list[EventModel], start_ms: int, end_ms: int) -> list[str]:
    mask: list[str] = []
    if quality.avg_snr_db is not None and quality.avg_snr_db < 10:
        mask.append("low_snr")
    if quality.noise_ratio > 0.35:
        mask.append("environment_contamination")
    if quality.vad_fp_count or quality.vad_fn_count:
        mask.append("vad_instability")
    if any(event.begin_ms < end_ms and event.end_ms > start_ms and event.type in {"interruption", "backchannel"} for event in events):
        mask.append("high_overlap")
    return sorted(set(mask))


def _lookup_benchmark_sentence(
    benchmark_rows: list[dict[str, Any]],
    index: int,
    text: str,
    start_ms: int,
    end_ms: int,
) -> dict[str, Any] | None:
    if index < len(benchmark_rows):
        candidate = benchmark_rows[index]
        candidate_text = str(candidate.get("text") or "").strip().lower()
        if not candidate_text or candidate_text == text.strip().lower():
            return candidate
    for row in benchmark_rows:
        row_text = str(row.get("text") or "").strip().lower()
        if row_text and row_text == text.strip().lower():
            return row
        row_start = int(row.get("start_ms", -1))
        row_end = int(row.get("end_ms", -1))
        if row_start >= 0 and row_end >= 0 and row_start <= start_ms and row_end >= end_ms:
            return row
    return None


def _heuristic_emotion_scores(text: str) -> dict[str, float]:
    lowered = text.lower()
    scores: dict[str, float] = {"neutral": 0.34}
    for emotion, cues in EMOTION_CUES.items():
        for cue in cues:
            if cue in lowered:
                scores[emotion] = scores.get(emotion, 0.0) + 0.16
    if "!" in text:
        scores["surprise"] = scores.get("surprise", 0.0) + min(text.count("!"), 3) * 0.08
        scores["anger"] = scores.get("anger", 0.0) + min(text.count("!"), 2) * 0.06
    if "?" in text:
        scores["surprise"] = scores.get("surprise", 0.0) + min(text.count("?"), 3) * 0.07
    filler_count = len(derive_fillers(text))
    uncertainty = len(derive_uncertainty_markers(text))
    if filler_count or uncertainty:
        scores["neutral"] = scores.get("neutral", 0.0) + 0.08
        scores["sadness"] = scores.get("sadness", 0.0) + 0.04 * uncertainty
    total = sum(scores.values()) or 1.0
    return {label: round(value / total, 3) for label, value in scores.items()}


def _sentence_from_benchmark(
    sentence_id: str,
    speaker_id: str,
    turn_id: str,
    speaker_role: SpeakerRole,
    text: str,
    start_ms: int,
    end_ms: int,
    benchmark: dict[str, Any],
    explainability_mask: list[str],
) -> SentenceEmotionSpan:
    emotion_label = normalize_emotion_label(benchmark.get("emotion_label") or benchmark.get("emotion"))
    confidence = float(benchmark.get("confidence", 0.98))
    evidence_refs = [EvidenceRef(kind="turn", ref_id=turn_id)]
    if benchmark.get("benchmark_id"):
        evidence_refs.append(EvidenceRef(kind="benchmark", ref_id=str(benchmark["benchmark_id"]), label=emotion_label))
    return SentenceEmotionSpan(
        sentence_id=sentence_id,
        speaker_id=speaker_id,
        turn_id=turn_id,
        speaker_role=speaker_role,
        start_ms=int(benchmark.get("start_ms", start_ms)),
        end_ms=int(benchmark.get("end_ms", end_ms)),
        text=text,
        emotion_label=emotion_label,
        emotion_scores={emotion_label: confidence},
        sentiment_label=str(benchmark.get("sentiment_label") or benchmark.get("sentiment") or SENTIMENT_BY_EMOTION.get(emotion_label)),
        confidence=confidence,
        source="benchmark_label",
        display_state=confidence_display_state(confidence, label=emotion_label, visible_threshold=0.65, muted_threshold=0.45),
        explainability_mask=sorted(set(explainability_mask + ["benchmark_label"])),
        evidence_refs=evidence_refs,
    )


def _sentence_from_heuristic(
    sentence_id: str,
    speaker_id: str,
    turn_id: str,
    speaker_role: SpeakerRole,
    text: str,
    start_ms: int,
    end_ms: int,
    explainability_mask: list[str],
) -> SentenceEmotionSpan:
    scores = _heuristic_emotion_scores(text)
    emotion_label, confidence = max(scores.items(), key=lambda item: item[1])
    adjusted_confidence = confidence
    if explainability_mask:
        adjusted_confidence = round(confidence * 0.78, 3)
    display_state = confidence_display_state(
        adjusted_confidence,
        label=emotion_label,
        visible_threshold=AFFECT_VISIBLE_THRESHOLD,
        muted_threshold=AFFECT_MUTED_THRESHOLD,
    )
    if adjusted_confidence < AFFECT_MUTED_THRESHOLD:
        emotion_label = "unlabeled"
        display_state = "hidden"
    return SentenceEmotionSpan(
        sentence_id=sentence_id,
        speaker_id=speaker_id,
        turn_id=turn_id,
        speaker_role=speaker_role,
        start_ms=start_ms,
        end_ms=end_ms,
        text=text,
        emotion_label=emotion_label,
        emotion_scores=scores,
        sentiment_label=SENTIMENT_BY_EMOTION.get(emotion_label),
        confidence=adjusted_confidence,
        source="heuristic",
        display_state=display_state,
        explainability_mask=explainability_mask,
        evidence_refs=[EvidenceRef(kind="turn", ref_id=turn_id)],
    )


def _build_sentence_spans(
    turns: list[TurnModel],
    metadata: dict[str, Any],
    quality: QualitySummary,
    events: list[EventModel],
    questions: list[QuestionAnalyticsRow],
) -> list[SentenceEmotionSpan]:
    benchmark_rows = list(metadata.get("sentence_emotion_labels", []))
    turn_emotion_hints = dict(metadata.get("turn_emotion_hints", {}))
    spans: list[SentenceEmotionSpan] = []
    benchmark_index = 0
    for turn in turns:
        text = turn.text.strip()
        if not text:
            continue
        sentences = [chunk.strip() for chunk in SENTENCE_SPLIT_PATTERN.split(text) if chunk.strip()] or [text]
        total_words = sum(max(1, count_words(sentence)) for sentence in sentences)
        cursor_ms = turn.start_ms
        for sentence_index, sentence_text in enumerate(sentences):
            word_count = max(1, count_words(sentence_text))
            sentence_duration = max(220, round((turn.end_ms - turn.start_ms) * (word_count / total_words))) if total_words else max(220, turn.end_ms - turn.start_ms)
            sentence_start = cursor_ms
            sentence_end = turn.end_ms if sentence_index == len(sentences) - 1 else min(turn.end_ms, cursor_ms + sentence_duration)
            explainability_mask = _sentence_explainability_mask(quality, events, sentence_start, sentence_end)
            sentence_id = f"{turn.turn_id}-sentence-{sentence_index + 1}"
            benchmark = _lookup_benchmark_sentence(benchmark_rows, benchmark_index, sentence_text, sentence_start, sentence_end)
            if benchmark is not None:
                span = _sentence_from_benchmark(
                    sentence_id,
                    turn.speaker_id,
                    turn.turn_id,
                    turn.speaker_role,
                    sentence_text,
                    sentence_start,
                    sentence_end,
                    benchmark,
                    explainability_mask,
                )
                benchmark_index += 1
            elif turn.turn_id in turn_emotion_hints:
                hint = turn_emotion_hints[turn.turn_id]
                emotion_label = normalize_emotion_label(hint.get("emotion_label"))
                confidence = float(hint.get("confidence", 0.72))
                display_state = confidence_display_state(
                    confidence,
                    label=emotion_label,
                    visible_threshold=AFFECT_VISIBLE_THRESHOLD,
                    muted_threshold=AFFECT_MUTED_THRESHOLD,
                )
                if turn.speaker_role == "ai" and display_state == "visible":
                    display_state = "muted"
                span = SentenceEmotionSpan(
                    sentence_id=sentence_id,
                    speaker_id=turn.speaker_id,
                    turn_id=turn.turn_id,
                    speaker_role=turn.speaker_role,
                    start_ms=sentence_start,
                    end_ms=sentence_end,
                    text=sentence_text,
                    emotion_label=emotion_label,
                    emotion_scores={emotion_label: confidence},
                    sentiment_label=str(hint.get("sentiment_label") or SENTIMENT_BY_EMOTION.get(emotion_label, "neutral")),
                    confidence=confidence,
                    source="model",
                    display_state=display_state,
                    explainability_mask=sorted(set(explainability_mask + list(hint.get("notes", [])))),
                    evidence_refs=[EvidenceRef(kind="turn", ref_id=turn.turn_id)],
                )
            else:
                span = _sentence_from_heuristic(
                    sentence_id,
                    turn.speaker_id,
                    turn.turn_id,
                    turn.speaker_role,
                    sentence_text,
                    sentence_start,
                    sentence_end,
                    explainability_mask,
                )
                if turn.speaker_role == "ai" and span.display_state == "visible":
                    span.display_state = "muted"
            related_questions = [
                question
                for question in questions
                if question.question_turn_id == turn.turn_id or question.answer_turn_id == turn.turn_id
            ]
            if related_questions:
                span.evidence_refs.extend(EvidenceRef(kind="question", ref_id=question.question_id, label=question.affect_tag) for question in related_questions[:2])
            spans.append(span)
            cursor_ms = sentence_end
    return spans


def _build_token_spans(words: list[WordTimestamp], sentences: list[SentenceEmotionSpan]) -> list[TokenEmotionSpan]:
    tokens: list[TokenEmotionSpan] = []
    for sentence in sentences:
        if sentence.display_state != "visible" or sentence.confidence < AFFECT_VISIBLE_THRESHOLD:
            continue
        matching_words = [
            word
            for word in words
            if word.start_ms >= sentence.start_ms and word.end_ms <= sentence.end_ms
        ]
        for index, word in enumerate(matching_words):
            tokens.append(
                TokenEmotionSpan(
                    token_id=f"{sentence.sentence_id}-token-{index + 1}",
                    turn_id=sentence.turn_id,
                    sentence_id=sentence.sentence_id,
                    word=word.word,
                    start_ms=word.start_ms,
                    end_ms=word.end_ms,
                    emotion_label=sentence.emotion_label,
                    confidence=min(sentence.confidence, word.confidence or sentence.confidence),
                    display_state="muted",
                    inherited_from_sentence=True,
                )
            )
    return tokens


def build_content(
    transcript: str,
    turns: list[TurnModel],
    metadata: dict[str, Any] | None = None,
    quality: QualitySummary | None = None,
    events: list[EventModel] | None = None,
    questions: list[QuestionAnalyticsRow] | None = None,
    words_override: list[WordTimestamp] | None = None,
) -> ContentSummary:
    metadata = metadata or {}
    quality = quality or QualitySummary()
    events = events or []
    questions = questions or []
    words = words_override or _build_word_timestamps(turns, transcript, metadata)
    sentences = _build_sentence_spans(turns, metadata, quality, events, questions)
    tokens = _build_token_spans(words, sentences)
    fillers = sorted({marker for turn in turns for marker in derive_fillers(turn.text)})
    uncertainty_markers = sorted({marker for turn in turns for marker in derive_uncertainty_markers(turn.text)})
    labels = sorted({sentence.emotion_label for sentence in sentences if sentence.display_state in {"visible", "muted"} and sentence.emotion_label != "unlabeled"})
    return ContentSummary(
        transcript=transcript,
        words=words,
        sentences=sentences,
        tokens=tokens,
        fillers=fillers,
        uncertainty_markers=uncertainty_markers,
        topic_labels=derive_topics(transcript, turns),
        view_summary=TranscriptViewSummary(
            sentence_count=len(sentences),
            highlighted_sentence_count=sum(1 for sentence in sentences if sentence.display_state in {"visible", "muted"}),
            token_overlay_count=len(tokens),
            emotion_labels=labels,
        ),
    )


def build_environment(
    metadata: dict[str, Any],
    quality: QualitySummary,
    events: list[EventModel],
    duration_sec: float,
) -> EnvironmentSummary:
    contamination_windows = list(quality.low_snr_windows)
    primary = str(metadata.get("environment_primary") or metadata.get("call_channel") or "phone_call_unknown")
    tags = list(metadata.get("environment_tags", []))
    notes: list[str] = []
    noise_events = [event for event in events if event.type in {"noise_spike", "low_snr_segment", "vad_false_positive"}]
    for event in noise_events:
        contamination_windows.append(TimeWindow(start_ms=event.begin_ms, end_ms=event.end_ms, label=event.type))
        if event.label:
            tags.append(event.label)
    if quality.noise_ratio > 0.35:
        tags.append("fan_or_hum")
        notes.append("Noise ratio is above the cautious interpretation threshold.")
    if quality.avg_snr_db is not None and quality.avg_snr_db < 10:
        tags.append("traffic_or_street_noise")
        notes.append("Low SNR downweights prosody-heavy interpretations.")
    if quality.clipping_ratio > 0.01:
        tags.append("line_clipping")
    tags = sorted({tag for tag in tags if tag})
    taxonomy_status = "fallback"
    if metadata.get("environment_primary") or tags:
        taxonomy_status = "ready"
    elif duration_sec <= 0:
        taxonomy_status = "missing"
    return EnvironmentSummary(
        primary=primary,
        tags=tags,
        contamination_windows=sorted(contamination_windows, key=lambda window: (window.start_ms, window.end_ms)),
        taxonomy_status=taxonomy_status,
        notes=notes,
    )


def build_questions(
    job_id: str,
    turns: list[TurnModel],
    events: list[EventModel],
    quality: QualitySummary,
    environment: EnvironmentSummary,
    metadata: dict[str, Any] | None = None,
    speaker_roles: SpeakerRoleSummary | None = None,
) -> list[QuestionAnalyticsRow]:
    metadata = metadata or {}
    role_map = _role_map(speaker_roles)
    rows: list[QuestionAnalyticsRow] = []
    for explicit in metadata.get("questions", []):
        rows.append(
            QuestionAnalyticsRow(
                question_id=str(explicit["question_id"]),
                question_text=str(explicit["question_text"]),
                question_turn_id=str(explicit["question_turn_id"]),
                answer_turn_id=str(explicit["answer_turn_id"]),
                response_latency_ms=int(explicit["response_latency_ms"]),
                answer_duration_ms=int(explicit["answer_duration_ms"]),
                directness_score=int(explicit["directness_score"]),
                hesitation_score=int(explicit["hesitation_score"]),
                affect_tag=str(explicit["affect_tag"]),
                evidence_refs=[EvidenceRef(kind="turn", ref_id=str(explicit["question_turn_id"])), EvidenceRef(kind="turn", ref_id=str(explicit["answer_turn_id"]))],
                explainability_mask=list(explicit.get("explainability_mask", [])),
            )
        )
    if rows:
        return rows

    for index, turn in enumerate(turns[:-1]):
        text = turn.text.strip()
        lowered = text.lower()
        if "?" not in text and not lowered.startswith(QUESTION_PREFIXES):
            continue
        answer_turn = _next_answer_turn(turns, index)
        if answer_turn is None:
            continue
        if role_map and role_map.get(answer_turn.speaker_id, answer_turn.speaker_role) != "human":
            continue
        raw_latency = max(0, answer_turn.start_ms - turn.end_ms)
        relevant_events = [event for event in events if event.begin_ms <= answer_turn.start_ms and event.end_ms >= turn.end_ms]
        explainability_mask: list[str] = []
        latency_discount = 0
        if quality.avg_snr_db is not None and quality.avg_snr_db < 10:
            explainability_mask.append("low_snr")
        if quality.noise_ratio > 0.35:
            explainability_mask.append("environment_contamination")
        if any(event.type in {"noise_spike", "low_snr_segment"} for event in relevant_events):
            explainability_mask.append("noisy_answer_start")
            latency_discount = min(raw_latency, sum(max(0, event.end_ms - max(event.begin_ms, turn.end_ms)) for event in relevant_events if event.type in {"noise_spike", "low_snr_segment"}))
        if any(event.type == "vad_false_positive" for event in relevant_events):
            explainability_mask.append("vad_instability")
        effective_latency = max(0, raw_latency - latency_discount)
        answer_fillers = answer_turn.filler_count or len(derive_fillers(answer_turn.text))
        answer_uncertainty = answer_turn.uncertainty_markers or len(derive_uncertainty_markers(answer_turn.text))
        hesitation_base = min(100, round((effective_latency / 12000) * 65 + answer_fillers * 8 + answer_uncertainty * 9))
        if explainability_mask:
            hesitation_base = round(hesitation_base * 0.82)
        directness = max(10, min(100, round(100 - answer_fillers * 9 - answer_uncertainty * 11 - min(effective_latency / 220, 40))))
        affect_tag = _affect_tag(hesitation_base, directness)
        rows.append(
            QuestionAnalyticsRow(
                question_id=f"{job_id}-question-{len(rows) + 1}",
                question_text=text,
                question_turn_id=turn.turn_id,
                answer_turn_id=answer_turn.turn_id,
                response_latency_ms=effective_latency,
                answer_duration_ms=max(0, answer_turn.end_ms - answer_turn.start_ms),
                directness_score=directness,
                hesitation_score=hesitation_base,
                affect_tag=affect_tag,
                evidence_refs=[
                    EvidenceRef(kind="turn", ref_id=turn.turn_id),
                    EvidenceRef(kind="turn", ref_id=answer_turn.turn_id),
                    *[EvidenceRef(kind="event", ref_id=event.event_id, label=event.type) for event in relevant_events[:2]],
                ],
                explainability_mask=sorted(set(explainability_mask)),
            )
        )
    return rows


def build_signals(
    quality: QualitySummary,
    speakers: list[SpeakerSummary],
    turns: list[TurnModel],
    events: list[EventModel],
    questions: list[QuestionAnalyticsRow],
    content: ContentSummary,
    speaker_roles: SpeakerRoleSummary | None = None,
) -> list[SignalCard]:
    role_map = _role_map(speaker_roles)
    human_speakers = [speaker for speaker in speakers if role_map.get(speaker.speaker_id, speaker.speaker_role) == "human"] or speakers
    ai_speakers = [speaker for speaker in speakers if role_map.get(speaker.speaker_id, speaker.speaker_role) == "ai"]
    human_turns = [turn for turn in turns if role_map.get(turn.speaker_id, turn.speaker_role) == "human"] or turns
    hesitation_avg = round(sum(question.hesitation_score for question in questions) / max(1, len(questions)))
    directness_avg = round(sum(question.directness_score for question in questions) / max(1, len(questions))) if questions else 55
    interruption_count = sum(1 for event in events if event.type == "interruption" and (not event.speaker_ids or any(role_map.get(speaker_id) == "human" for speaker_id in event.speaker_ids)))
    engagement_drop = any(event.type == "engagement_drop" for event in events)
    human_talk_ratio = human_speakers[0].talk_ratio if human_speakers else 0.5
    ai_talk_ratio = ai_speakers[0].talk_ratio if ai_speakers else (speakers[1].talk_ratio if len(speakers) > 1 else 0.5)
    reciprocity = round(100 - abs((human_talk_ratio - ai_talk_ratio) * 140))
    reciprocity = max(10, min(100, reciprocity))
    friction_score = max(10, min(100, round(quality.noise_ratio * 100 * 0.35 + interruption_count * 11 + hesitation_avg * 0.35)))
    confidence_like = max(10, min(100, round(directness_avg * 0.7 + (100 - hesitation_avg) * 0.3)))
    rapport_score = max(10, min(100, round(reciprocity * 0.55 + (100 - interruption_count * 12) * 0.25 + (100 - quality.noise_ratio * 100) * 0.2)))
    frustration_risk = max(10, min(100, round(friction_score * 0.55 + quality.noise_ratio * 100 * 0.25 + quality.vad_fp_count * 2.5)))
    first_half = [turn for turn in human_turns if turn.start_ms <= (human_turns[-1].end_ms / 2 if human_turns else 0)]
    second_half = [turn for turn in human_turns if turn.start_ms > (human_turns[-1].end_ms / 2 if human_turns else 0)]
    first_density = sum(turn.word_count for turn in first_half) / max(1, len(first_half))
    second_density = sum(turn.word_count for turn in second_half) / max(1, len(second_half))
    drift = round(max(0.0, (first_density - second_density) * 6 + (18 if engagement_drop else 0)))
    explainability = []
    if quality.avg_snr_db is not None and quality.avg_snr_db < 10:
        explainability.append("low_snr")
    if quality.noise_ratio > 0.35:
        explainability.append("environment_contamination")
    if quality.vad_fp_count or quality.vad_fn_count:
        explainability.append("vad_instability")

    if any(sentence.speaker_role == "human" and sentence.source == "benchmark_label" for sentence in content.sentences):
        evidence_class: EvidenceClass = "benchmark_backed"
    elif any(sentence.speaker_role == "human" and sentence.source == "model" for sentence in content.sentences):
        evidence_class = "model_backed"
    elif any(sentence.speaker_role == "human" and sentence.source == "metadata_hint" for sentence in content.sentences):
        evidence_class = "metadata_backed"
    else:
        evidence_class = "heuristic_backed"

    return [
        _signal_card("hesitation", "Hesitation", hesitation_avg, f"Pause and filler burden averaged {hesitation_avg}/100 across question moments.", questions, explainability, evidence_class=evidence_class),
        _signal_card("engagement_drift", "Engagement Drift", drift, "Later turns show lighter answer density and more drift than the opening half.", [event for event in events if event.type == "engagement_drop"], explainability, evidence_class=evidence_class),
        _signal_card("reciprocity", "Reciprocity", reciprocity, "Speaker balance stays closer to healthy turn-sharing when talk ratio remains even.", speakers[:2], explainability, evidence_class=evidence_class),
        _signal_card("friction", "Friction", friction_score, "Noise, interruptions, and guarded responses are compounding into operational friction.", events, explainability, evidence_class=evidence_class),
        _signal_card("confidence_like_behavior", "Confidence-Like Behavior", confidence_like, "Direct answers and lower uncertainty markers lift this behavioral confidence proxy.", questions, explainability, evidence_class=evidence_class),
        _signal_card("rapport", "Rapport", rapport_score, "Balanced turn-taking and limited overlap keep rapport in a steadier range.", speakers[:2], explainability, evidence_class=evidence_class),
        _signal_card("frustration_risk", "Frustration Risk", frustration_risk, "Audio quality issues plus conversational friction raise the risk of a strained interaction.", events, explainability, evidence_class=evidence_class),
    ]


def build_stage_status(
    artifacts: ArtifactPaths,
    diagnostics: Diagnostics,
    quality: QualitySummary,
    environment: EnvironmentSummary,
    profile_display: list[ProfileField],
    profile_coverage: ProfileCoverageSummary,
    speaker_roles: SpeakerRoleSummary,
    content: ContentSummary,
    questions: list[QuestionAnalyticsRow],
    signals: list[SignalCard],
    diarization: DiarizationSummary,
    waveform: WaveformArtifact,
    spectrogram: SpectrogramArtifact,
    prosody_tracks: list[ProsodyTrack],
    nonverbal_cues: list[NonverbalCue],
    timeline_tracks: list[TimelineTrack],
) -> list[StageStatus]:
    alignment_decision = next((decision for decision in diagnostics.provider_decisions if decision.kind == "alignment"), None)
    nonverbal_decision = next((decision for decision in diagnostics.provider_decisions if decision.kind == "nonverbal_cues"), None)
    profile_decision = next((decision for decision in diagnostics.provider_decisions if decision.kind == "profile"), None)
    provisional_speaker_lanes = diarization.readiness_state == "fallback"
    muted_vocal_cues = [cue for cue in nonverbal_cues if cue.family == "vocal_sound" and cue.attribution_state != "strong"]
    return [
        StageStatus(
            key="audio",
            label="Layer A · Audio",
            status="ready" if artifacts.normalized_audio_path else "missing",
            summary="Raw, normalized, and telephony artifacts are materialized for replay and fallback analysis.",
            caveats=[] if artifacts.telephony_audio_path else ["telephony_render_missing"],
            adapter_keys=["ffmpeg"],
        ),
        StageStatus(
            key="diarization",
            label="Diarization",
            status=diarization.readiness_state,
            summary="Speaker lanes require benchmark timing or strong diarization adapters before the waveform workspace will treat them as trustworthy.",
            caveats=sorted(set(diarization.notes + (["speaker_lanes_provisional"] if provisional_speaker_lanes else []))),
            adapter_keys=["pyannote"],
        ),
        StageStatus(
            key="waveform_visuals",
            label="Waveform Visuals",
            status="ready" if waveform.peaks and spectrogram.readiness_state == "ready" else "fallback",
            summary="Waveform peaks, the spectrogram asset, and timeline views are materialized for synchronized playback.",
            caveats=list(spectrogram.notes),
            adapter_keys=["ffmpeg"],
        ),
        StageStatus(
            key="quality",
            label="Layer B · Quality",
            status="fallback",
            summary="Quality metrics use waveform heuristics and optional adapter disclosure.",
            caveats=quality.warning_flags,
            adapter_keys=["silero_vad", "yamnet", "panns"],
        ),
        StageStatus(
            key="structure",
            label="Layer C · Structure",
            status="ready" if questions or diagnostics.adapters else "fallback",
            summary="Turns, pauses, overlaps, and interruptions are aligned into a session timeline.",
            caveats=["pyannote_optional"] if not any(adapter.key == "pyannote" and adapter.available for adapter in diagnostics.adapters) else [],
            adapter_keys=["pyannote", "silero_vad"],
        ),
        StageStatus(
            key="content",
            label="Layer D · Content",
            status="ready" if content.transcript else "fallback",
            summary="Transcript, word timing proxies, topic labels, fillers, and uncertainty markers are bundled together.",
            caveats=sorted(
                set(
                    (["transcript_hint_used"] if "transcript_hint_used" in diagnostics.confidence_caveats else [])
                    + (alignment_decision.notes if alignment_decision else [])
                )
            ),
            adapter_keys=["faster_whisper", "whisperx"],
        ),
        StageStatus(
            key="speaker_roles",
            label="Speaker Roles",
            status="ready" if speaker_roles.assignments else "fallback",
            summary="Human-vs-AI role assignment is auto-inferred, then left open to manual correction in the dashboard.",
            caveats=list(speaker_roles.notes),
            adapter_keys=["openai_audio_analysis"],
        ),
        StageStatus(
            key="profile",
            label="Profile",
            status="ready" if any(field.display_state in {"visible", "muted"} for field in profile_display) else "fallback",
            summary="Voice-profile fields are confidence-gated and only surfaced when the evidence posture supports them.",
            caveats=sorted(
                {warning for field in profile_display for warning in field.warning_flags}
                | ({f"hidden_fields:{len(profile_coverage.hidden_fields)}"} if profile_coverage.hidden_fields else set())
                | ({f"unavailable_fields:{len(profile_coverage.unavailable_fields)}"} if profile_coverage.unavailable_fields else set())
                | set(profile_decision.notes if profile_decision else [])
            ),
            adapter_keys=["speechbrain_commonaccent", "ecapa_fine_accent", "audeering_age_gender"],
        ),
        StageStatus(
            key="transcript_affect",
            label="Transcript Affect",
            status="ready" if content.sentences else "fallback",
            summary="Sentence-level affect spans align transcript text with benchmark or heuristic emotional labels.",
            caveats=sorted({mask for sentence in content.sentences for mask in sentence.explainability_mask}),
            adapter_keys=["faster_whisper", "whisperx"],
        ),
        StageStatus(
            key="prosody",
            label="Prosody",
            status="ready" if any(track.samples for track in prosody_tracks) else "fallback",
            summary="Continuous pitch, energy, and speaking-rate tracks support the waveform-first inspection view.",
            caveats=sorted({note for track in prosody_tracks for note in track.notes}),
            adapter_keys=["librosa"],
        ),
        StageStatus(
            key="alignment",
            label="Alignment",
            status="ready" if content.words and content.sentences else "fallback",
            summary="Sentence and token overlays stay attached to the transcript only when timing alignment is good enough.",
            caveats=sorted(
                set((["token_overlay_missing"] if not content.tokens else []))
                | set(alignment_decision.notes if alignment_decision else [])
            ),
            adapter_keys=["whisperx"],
        ),
        StageStatus(
            key="nonverbal_cues",
            label="Non-Verbal Cues",
            status="ready" if any(cue.display_state in {"visible", "muted"} for cue in nonverbal_cues) else ("blocked" if diarization.readiness_state == "blocked" else "fallback"),
            summary="Laughter, vocal sounds, hesitation onsets, and prosody spikes share one confidence-gated cue ledger.",
            caveats=sorted(
                {mask for cue in nonverbal_cues for mask in cue.explainability_mask}
                | set(diarization.notes)
                | set(nonverbal_decision.notes if nonverbal_decision else [])
                | ({"speaker_attribution_limited"} if muted_vocal_cues else set())
            ),
            adapter_keys=["pyannote", "yamnet", "panns"],
        ),
        StageStatus(
            key="signals",
            label="Layer E · Signals",
            status="ready" if signals else "fallback",
            summary="Behavioral and emotional proxy cards carry evidence refs and explainability masks.",
            caveats=sorted(
                {mask for signal in signals for mask in signal.explainability_mask}
                | {signal.evidence_class for signal in signals}
            ),
            adapter_keys=["openai_audio_analysis", "opensmile", "speechbrain_commonaccent"],
        ),
        StageStatus(
            key="environment",
            label="Environment",
            status=environment.taxonomy_status,
            summary="Environment tags remain heuristic-first until optional event adapters are installed.",
            caveats=environment.notes,
            adapter_keys=["yamnet", "panns"],
        ),
        StageStatus(
            key="timeline_tracks",
            label="Timeline Tracks",
            status="ready" if any(track.items for track in timeline_tracks) else "fallback",
            summary="Speaker, transcript, question, cue, overlap, and evidence lanes stay synchronized around the main player.",
            caveats=sorted({note for track in timeline_tracks for note in track.notes}),
            adapter_keys=["ffmpeg", "pyannote"],
        ),
    ]


def build_session_bundle(
    result: SessionResult,
    *,
    session_title: str,
    session_type: str,
    language: str | None,
    region: str | None,
    call_channel: str | None,
    source_type: str,
    environment: EnvironmentSummary,
    profile_display: list[ProfileField],
    profile_coverage: ProfileCoverageSummary,
    speaker_roles: SpeakerRoleSummary,
    diarization: DiarizationSummary,
    waveform: WaveformArtifact,
    spectrogram: SpectrogramArtifact,
    prosody_tracks: list[ProsodyTrack],
    nonverbal_cues: list[NonverbalCue],
    timeline_tracks: list[TimelineTrack],
    content: ContentSummary,
    questions: list[QuestionAnalyticsRow],
    signals: list[SignalCard],
    stage_status: list[StageStatus],
    readiness_tier: ReadinessTier,
    conversation_report: ConversationReport | None = None,
) -> SessionBundle:
    return SessionBundle(
        session=SessionDescriptor(
            session_id=result.job_id,
            title=session_title,
            session_type=session_type,
            analysis_mode=result.analysis_mode,
            language=language,
            region=region,
            call_channel=call_channel,
            source_type=source_type,
            dataset_id=result.source.dataset_id if result.source else None,
            dataset_title=result.source.title if result.source else None,
            reference_label=result.source.reference_label if result.source else None,
            duration_sec=result.duration_sec,
            speaker_count=result.speaker_count,
            status="completed",
            readiness_tier=readiness_tier,
        ),
        source=result.source,
        artifacts=result.artifacts,
        quality=result.quality,
        environment=environment,
        profile=result.profile,
        profile_display=profile_display,
        profile_coverage=profile_coverage,
        speaker_roles=speaker_roles,
        diarization=diarization,
        waveform=waveform,
        spectrogram=spectrogram,
        prosody_tracks=prosody_tracks,
        nonverbal_cues=nonverbal_cues,
        timeline_tracks=timeline_tracks,
        speakers=result.speakers,
        turns=result.turns,
        events=result.events,
        questions=questions,
        content=content,
        signals=signals,
        conversation_report=conversation_report or ConversationReport(),
        metrics=result.metrics,
        diagnostics=result.diagnostics,
        stage_status=stage_status,
    )


def persist_session_artifacts(
    job_id: str,
    metadata: dict[str, Any],
    quality: QualitySummary,
    profile_display: list[ProfileField],
    profile_coverage: ProfileCoverageSummary,
    diarization: DiarizationSummary,
    waveform: WaveformArtifact,
    spectrogram: SpectrogramArtifact,
    prosody_tracks: list[ProsodyTrack],
    nonverbal_cues: list[NonverbalCue],
    timeline_tracks: list[TimelineTrack],
    content: ContentSummary,
    questions: list[QuestionAnalyticsRow],
    environment: EnvironmentSummary,
    signals: list[SignalCard],
    speaker_roles: SpeakerRoleSummary,
    result: SessionResult,
    bundle: SessionBundle,
) -> None:
    run_file(job_id, "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    run_file(job_id, "quality.json").write_text(quality.model_dump_json(indent=2) + "\n")
    run_file(job_id, "diarization.json").write_text(diarization.model_dump_json(indent=2) + "\n")
    run_file(job_id, "waveform.peaks.json").write_text(waveform.model_dump_json(indent=2) + "\n")
    run_file(job_id, "prosody.tracks.json").write_text(json.dumps([track.model_dump(mode="json") for track in prosody_tracks], indent=2) + "\n")
    run_file(job_id, "nonverbal_cues.json").write_text(json.dumps([cue.model_dump(mode="json") for cue in nonverbal_cues], indent=2) + "\n")
    run_file(job_id, "timeline_tracks.json").write_text(json.dumps([track.model_dump(mode="json") for track in timeline_tracks], indent=2) + "\n")
    run_file(job_id, "timeline.json").write_text(
        json.dumps(
            {
                "job_id": job_id,
                "turns": [turn.model_dump(mode="json") for turn in result.turns],
                "events": [event.model_dump(mode="json") for event in result.events],
                "timeline_tracks": [track.model_dump(mode="json") for track in timeline_tracks],
            },
            indent=2,
        )
        + "\n"
    )
    run_file(job_id, "events.json").write_text(json.dumps([event.model_dump(mode="json") for event in result.events], indent=2) + "\n")
    run_file(job_id, "questions.json").write_text(json.dumps([question.model_dump(mode="json") for question in questions], indent=2) + "\n")
    run_file(job_id, "roles.json").write_text(speaker_roles.model_dump_json(indent=2) + "\n")
    run_file(job_id, "environment.json").write_text(environment.model_dump_json(indent=2) + "\n")
    run_file(job_id, "signals.json").write_text(json.dumps([signal.model_dump(mode="json") for signal in signals], indent=2) + "\n")
    run_file(job_id, "profile.json").write_text(
        json.dumps(
            {
                "fields": [field.model_dump(mode="json") for field in profile_display],
                "coverage": profile_coverage.model_dump(mode="json"),
            },
            indent=2,
        )
        + "\n"
    )
    run_file(job_id, "transcript.words.json").write_text(json.dumps([word.model_dump(mode="json") for word in content.words], indent=2) + "\n")
    run_file(job_id, "transcript.sentences.json").write_text(json.dumps([sentence.model_dump(mode="json") for sentence in content.sentences], indent=2) + "\n")
    run_file(job_id, "transcript.tokens.json").write_text(json.dumps([token.model_dump(mode="json") for token in content.tokens], indent=2) + "\n")
    run_file(job_id, "result.json").write_text(result.model_dump_json(indent=2) + "\n")
    run_file(job_id, "bundle.json").write_text(bundle.model_dump_json(indent=2) + "\n")


def create_session_result(
    job_id: str,
    analysis_mode: AnalysisMode,
    original_path: Path,
    options: ProcessSessionOptions,
    progress: Callable[[str, str | None], Any] | None = None,
) -> SessionResult:
    metadata = options.metadata or {}
    session_dir(job_id).mkdir(parents=True, exist_ok=True)

    normalized_path = run_file(job_id, "normalized", "audio.wav")
    telephony_path = run_file(job_id, "telephony", "audio-8k.wav")
    waveform_path = run_file(job_id, "waveform.peaks.json")
    spectrogram_path = run_file(job_id, "spectrogram", "audio.png")
    if progress:
        progress("normalize", JOB_STAGE_BY_KEY["normalize"]["label"])
    normalize_audio(original_path, normalized_path)
    render_telephony_audio(original_path, telephony_path)
    duration_sec = probe_duration(normalized_path)
    silences = detect_silences(normalized_path)
    provider_preference = _upload_provider_preference(metadata)
    adapters = build_adapter_inventory()
    openai_warnings: list[str] = []
    role_provider_decision = ProviderDecision(kind="role_analysis", provider_key="heuristic", used=True, cached=False, status="fallback", notes=["heuristic_role_analysis"])
    if provider_preference == "openai":
        openai_updates, openai_warnings, role_provider_decision = enrich_metadata_with_openai(job_id, normalized_path, metadata)
        if openai_updates:
            metadata = {**metadata, **openai_updates}
        transcription_provider = ProviderDecision(
            kind="transcription",
            provider_key="openai_audio_analysis",
            used=bool(metadata.get("transcript_hint")),
            cached=False,
            status="ready" if metadata.get("transcript_hint") else "fallback",
            notes=list(openai_warnings),
        )
        transcript_outcome = TranscriptionOutcome(
            transcript=str(metadata.get("transcript_hint") or ""),
            words=_normalize_provider_words(list(metadata.get("transcript_word_timestamps", [])), source="model"),
            warnings=list(openai_warnings),
            provider=transcription_provider,
        )
    else:
        transcript_outcome = maybe_transcribe(job_id, normalized_path, transcript_hint=metadata.get("transcript_hint"))
        if transcript_outcome.words:
            metadata = {**metadata, "transcript_word_timestamps": transcript_outcome.words}
    transcript = transcript_outcome.transcript
    alignment_outcome = maybe_align_words(job_id, normalized_path, metadata, transcript_outcome.words, adapters)
    if alignment_outcome.words:
        metadata = {**metadata, "transcript_word_timestamps": alignment_outcome.words}
    transcript_warnings = sorted(set(transcript_outcome.warnings + alignment_outcome.warnings))
    turns = build_turns_from_metadata(job_id, duration_sec, transcript, metadata, analysis_mode)
    if not transcript and turns:
        transcript = " ".join(turn.text for turn in turns if turn.text).strip()
    if progress:
        progress("diarization", JOB_STAGE_BY_KEY["diarization"]["label"])
    diarization, diarization_provider = build_diarization(job_id, normalized_path, metadata, turns, adapters)
    if progress:
        progress("waveform_visuals", JOB_STAGE_BY_KEY["waveform_visuals"]["label"])
    waveform = build_waveform_artifact(normalized_path, duration_sec)
    spectrogram = generate_spectrogram(normalized_path, spectrogram_path)
    if progress:
        progress("quality", JOB_STAGE_BY_KEY["quality"]["label"])
    quality = build_quality(normalized_path, analysis_mode, silences, metadata)
    if progress:
        progress("structure", JOB_STAGE_BY_KEY["structure"]["label"])

    speakers = build_speakers(turns, duration_sec, metadata) if turns else [
        SpeakerSummary(
            speaker_id="speaker_0",
            role=metadata.get("speaker_roles", {}).get("speaker_0"),
            talk_ratio=1.0,
            avg_turn_ms=round(duration_sec * 1000, 2),
            interruption_count=0,
            overlap_ms=0.0,
        )
    ]
    if progress:
        progress("speaker_roles", JOB_STAGE_BY_KEY["speaker_roles"]["label"])
    speaker_roles = build_speaker_role_summary(speakers, turns, metadata)
    if metadata.get("speaker_role_hint_source") == "model":
        role_provider_decision = ProviderDecision(
            kind="role_analysis",
            provider_key="openai_audio_analysis",
            used=True,
            cached=False,
            status="ready",
            notes=list(metadata.get("openai_provider_warnings", [])),
        )
    speakers, turns = apply_speaker_roles(speakers, turns, speaker_roles)
    events = build_events(job_id, turns, silences, quality, duration_sec, metadata)
    profile, profile_display, profile_coverage, profile_provider_decision = build_profile(
        analysis_mode,
        metadata,
        transcript,
        quality,
        speakers,
        options,
        audio_path=normalized_path,
        adapters=adapters,
    )
    if progress:
        progress("content", JOB_STAGE_BY_KEY["content"]["label"])
    environment = build_environment(metadata, quality, events, duration_sec)
    if progress:
        progress("prosody", JOB_STAGE_BY_KEY["prosody"]["label"])
    prosody_tracks = build_prosody_tracks(normalized_path, turns, duration_sec)
    word_timestamps = _build_word_timestamps(turns, transcript, metadata)
    acoustic_cues, acoustic_cue_provider = maybe_detect_acoustic_cues(
        job_id,
        prosody_tracks,
        word_timestamps,
        diarization,
        quality,
        str(metadata.get("source_type") or "direct_audio_file"),
        adapters,
    )
    if progress:
        progress("questions", JOB_STAGE_BY_KEY["questions"]["label"])
    questions = build_questions(job_id, turns, events, quality, environment, metadata, speaker_roles)
    if progress:
        progress("affect", JOB_STAGE_BY_KEY["affect"]["label"])
    content = build_content(transcript, turns, metadata, quality, events, questions, words_override=word_timestamps)
    if progress:
        progress("nonverbal_cues", JOB_STAGE_BY_KEY["nonverbal_cues"]["label"])
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
        acoustic_cues=acoustic_cues,
    )
    diagnostics = Diagnostics(
        adapters=adapters,
        enabled_comparisons=[adapter.key for adapter in adapters if adapter.comparison_only and adapter.available and options.enable_comparisons],
        license_warnings=[adapter.warning for adapter in adapters if adapter.prototype_only and options.prototype_noncommercial and adapter.warning],
        confidence_caveats=sorted(set(transcript_warnings + openai_warnings + quality.warning_flags)),
        degraded_reasons=sorted(
            {
                *transcript_warnings,
                *openai_warnings,
                *diarization_provider.notes,
                *alignment_outcome.provider.notes,
                *acoustic_cue_provider.notes,
                *profile_provider_decision.notes,
                *(
                    ["transcript_missing_after_asr"]
                    if not transcript.strip()
                    else []
                ),
                *(
                    ["low_snr"]
                    if quality.avg_snr_db is not None and quality.avg_snr_db < 10
                    else []
                ),
                *(
                    ["high_noise_ratio"]
                    if quality.noise_ratio > 0.35
                    else []
                ),
            }
        ),
        provider_decisions=[
            transcript_outcome.provider,
            alignment_outcome.provider,
            diarization_provider,
            acoustic_cue_provider,
            role_provider_decision,
            profile_provider_decision,
        ],
        fallback_logic=[
            "ffmpeg_silence_analysis",
            "heuristic_question_mapping",
            "heuristic_signal_cards",
            "sentence_emotion_heuristics",
            "waveform_peak_decimation",
            "heuristic_prosody_tracks",
            "acoustic_cue_provider",
            "openai_provider_override" if provider_preference == "openai" else "oss_first_local_pipeline",
        ],
    )
    if options.prototype_noncommercial:
        diagnostics.license_warnings.append("Prototype-only age/voice presentation path is enabled. Do not ship non-commercial outputs without legal review.")
    metrics = build_metrics(duration_sec, transcript, quality, speakers, turns, events, questions, speaker_roles)
    source = DatasetReference(
        dataset_id=metadata.get("dataset_id"),
        title=metadata.get("dataset_title"),
        access_type=metadata.get("access_type"),
        split=metadata.get("split"),
        source_path=str(original_path),
        reference_label=metadata.get("reference_label"),
        metadata={"title": metadata.get("title"), "notes": metadata.get("notes")},
    )
    artifacts = ArtifactPaths(
        original_audio_path=str(original_path),
        normalized_audio_path=str(normalized_path),
        telephony_audio_path=str(telephony_path),
        waveform_path=str(waveform_path),
        spectrogram_path=str(spectrogram_path) if spectrogram.image_path else None,
        diarization_path=str(run_file(job_id, "diarization.json")),
        prosody_path=str(run_file(job_id, "prosody.tracks.json")),
        nonverbal_cues_path=str(run_file(job_id, "nonverbal_cues.json")),
        timeline_tracks_path=str(run_file(job_id, "timeline_tracks.json")),
        result_path=str(run_file(job_id, "result.json")),
        timeline_path=str(run_file(job_id, "timeline.json")),
        quality_path=str(run_file(job_id, "quality.json")),
        events_path=str(run_file(job_id, "events.json")),
        questions_path=str(run_file(job_id, "questions.json")),
        environment_path=str(run_file(job_id, "environment.json")),
        signals_path=str(run_file(job_id, "signals.json")),
        profile_path=str(run_file(job_id, "profile.json")),
        transcript_words_path=str(run_file(job_id, "transcript.words.json")),
        transcript_sentences_path=str(run_file(job_id, "transcript.sentences.json")),
        transcript_tokens_path=str(run_file(job_id, "transcript.tokens.json")),
        roles_path=str(run_file(job_id, "roles.json")),
        bundle_path=str(run_file(job_id, "bundle.json")),
    )

    result = SessionResult(
        job_id=job_id,
        analysis_mode=analysis_mode,
        duration_sec=round(duration_sec, 3),
        speaker_count=len({speaker.speaker_id for speaker in speakers}),
        transcript=transcript,
        quality=quality,
        profile=profile,
        metrics=metrics,
        speakers=speakers,
        turns=turns,
        events=events,
        diagnostics=diagnostics,
        source=source,
        artifacts=artifacts,
    )
    if progress:
        progress("human_analysis", JOB_STAGE_BY_KEY["human_analysis"]["label"])
    signals = build_signals(quality, speakers, turns, events, questions, content, speaker_roles)
    if progress:
        progress("signals", JOB_STAGE_BY_KEY["signals"]["label"])
    timeline_tracks = build_timeline_tracks(diarization, content, turns, questions, nonverbal_cues, events)
    stage_status = build_stage_status(
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
    )
    readiness_tier = _readiness_tier(transcript, diarization, nonverbal_cues)
    conversation_report = build_conversation_report(
        session_id=job_id,
        metadata=metadata,
        quality=quality,
        speaker_roles=speaker_roles,
        diarization=diarization,
        speakers=speakers,
        turns=turns,
        events=events,
        questions=questions,
        content=content,
        signals=signals,
        metrics=result.metrics,
        diagnostics=diagnostics,
        stage_status=stage_status,
    )
    bundle = build_session_bundle(
        result,
        session_title=str(metadata.get("title") or original_path.stem.replace("_", " ").title()),
        session_type=str(metadata.get("session_type") or "analysis"),
        language=metadata.get("language_hint"),
        region=metadata.get("region"),
        call_channel=metadata.get("call_channel"),
        source_type=str(metadata.get("source_type") or "direct_audio_file"),
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
        stage_status=stage_status,
        readiness_tier=readiness_tier,
        conversation_report=conversation_report,
    )
    if progress:
        progress("persist", JOB_STAGE_BY_KEY["persist"]["label"])
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
    return result


def bundle_from_result(result: SessionResult, metadata: dict[str, Any] | None = None) -> SessionBundle:
    metadata = metadata or {}
    speaker_roles = build_speaker_role_summary(result.speakers, result.turns, metadata)
    speakers, turns = apply_speaker_roles(list(result.speakers), list(result.turns), speaker_roles)
    adapters = result.diagnostics.adapters
    normalized_path = Path(result.artifacts.normalized_audio_path) if result.artifacts.normalized_audio_path else None
    _profile, profile_display, profile_coverage, profile_provider_decision = build_profile(
        result.analysis_mode,
        metadata,
        result.transcript,
        result.quality,
        speakers,
        ProcessSessionOptions(metadata=metadata),
        audio_path=normalized_path,
        adapters=adapters,
    )
    environment = build_environment(metadata, result.quality, result.events, result.duration_sec)
    questions = build_questions(result.job_id, turns, result.events, result.quality, environment, metadata, speaker_roles)
    content = build_content(result.transcript, turns, metadata, result.quality, result.events, questions)
    diarization, diarization_provider = (
        build_diarization(result.job_id, normalized_path or Path(result.artifacts.original_audio_path or ""), metadata, turns, adapters)
        if normalized_path or result.artifacts.original_audio_path
        else (
            DiarizationSummary(),
            ProviderDecision(kind="diarization", provider_key="unavailable", used=False, cached=False, status="missing", notes=["no_audio_for_diarization"]),
        )
    )
    waveform = build_waveform_artifact(normalized_path, result.duration_sec) if normalized_path and normalized_path.exists() else WaveformArtifact(duration_ms=int(result.duration_sec * 1000))
    spectrogram_path = result.artifacts.spectrogram_path if result.artifacts.spectrogram_path else None
    spectrogram = SpectrogramArtifact(
        readiness_state="ready" if spectrogram_path and Path(spectrogram_path).exists() else "fallback",
        image_path=spectrogram_path,
        width=1600,
        height=360,
    )
    prosody_tracks = build_prosody_tracks(normalized_path, turns, result.duration_sec) if normalized_path and normalized_path.exists() else []
    nonverbal_cues = build_nonverbal_cues(
        result.job_id,
        metadata,
        diarization,
        prosody_tracks,
        turns,
        questions,
        result.quality,
        words=content.words,
        events=result.events,
    )
    metrics = build_metrics(result.duration_sec, result.transcript, result.quality, speakers, turns, result.events, questions, speaker_roles)
    signals = build_signals(result.quality, speakers, turns, result.events, questions, content, speaker_roles)
    timeline_tracks = build_timeline_tracks(diarization, content, turns, questions, nonverbal_cues, result.events)
    stage_status = build_stage_status(
        result.artifacts,
        result.diagnostics,
        result.quality,
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
    )
    rebuilt_result = result.model_copy(update={"speakers": speakers, "turns": turns, "metrics": metrics})
    if not rebuilt_result.diagnostics.provider_decisions:
        rebuilt_result.diagnostics.provider_decisions = [
            ProviderDecision(
                kind="transcription",
                provider_key="transcript_hint" if metadata.get("transcript_hint") else "unknown",
                used=bool(result.transcript),
                cached=False,
                status="ready" if result.transcript else "fallback",
                notes=[],
            ),
            ProviderDecision(kind="alignment", provider_key="persisted_bundle", used=bool(content.words), cached=False, status="ready" if content.words else "fallback", notes=[]),
            diarization_provider,
            ProviderDecision(kind="nonverbal_cues", provider_key="persisted_bundle", used=bool(nonverbal_cues), cached=False, status="ready" if nonverbal_cues else "fallback", notes=[]),
            profile_provider_decision,
            ProviderDecision(
                kind="role_analysis",
                provider_key="heuristic",
                used=True,
                cached=False,
                status="fallback",
                notes=["heuristic_role_analysis"],
            ),
        ]
    conversation_report = build_conversation_report(
        session_id=result.job_id,
        metadata=metadata,
        quality=result.quality,
        speaker_roles=speaker_roles,
        diarization=diarization,
        speakers=speakers,
        turns=turns,
        events=result.events,
        questions=questions,
        content=content,
        signals=signals,
        metrics=metrics,
        diagnostics=rebuilt_result.diagnostics,
        stage_status=stage_status,
    )
    return build_session_bundle(
        rebuilt_result,
        session_title=str(metadata.get("title") or (result.source.metadata.get("title") if result.source and result.source.metadata else None) or result.job_id),
        session_type=str(metadata.get("session_type") or "analysis"),
        language=metadata.get("language_hint"),
        region=metadata.get("region"),
        call_channel=metadata.get("call_channel"),
        source_type=str(metadata.get("source_type") or "direct_audio_file"),
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
        stage_status=stage_status,
        readiness_tier=_readiness_tier(result.transcript, diarization, nonverbal_cues),
        conversation_report=conversation_report,
    )


def apply_manual_role_overrides(job_id: str, overrides: dict[str, SpeakerRole]) -> SessionBundle:
    result = SessionResult.model_validate_json(run_file(job_id, "result.json").read_text())
    metadata_path = run_file(job_id, "metadata.json")
    metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
    merged_hints = {str(key): str(value) for key, value in dict(metadata.get("speaker_role_hints") or {}).items()}
    merged_hints.update({speaker_id: role for speaker_id, role in overrides.items()})
    metadata["speaker_role_hints"] = merged_hints
    metadata["speaker_role_hint_source"] = "manual_override"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    bundle = bundle_from_result(result, metadata=metadata)
    updated_result = result.model_copy(update={"speakers": bundle.speakers, "turns": bundle.turns, "metrics": bundle.metrics})
    run_file(job_id, "result.json").write_text(updated_result.model_dump_json(indent=2) + "\n")
    run_file(job_id, "roles.json").write_text(bundle.speaker_roles.model_dump_json(indent=2) + "\n")
    run_file(job_id, "bundle.json").write_text(bundle.model_dump_json(indent=2) + "\n")
    run_file(job_id, "questions.json").write_text(json.dumps([question.model_dump(mode="json") for question in bundle.questions], indent=2) + "\n")
    run_file(job_id, "signals.json").write_text(json.dumps([signal.model_dump(mode="json") for signal in bundle.signals], indent=2) + "\n")
    run_file(job_id, "transcript.sentences.json").write_text(json.dumps([sentence.model_dump(mode="json") for sentence in bundle.content.sentences], indent=2) + "\n")
    run_file(job_id, "transcript.tokens.json").write_text(json.dumps([token.model_dump(mode="json") for token in bundle.content.tokens], indent=2) + "\n")
    run_file(job_id, "timeline_tracks.json").write_text(json.dumps([track.model_dump(mode="json") for track in bundle.timeline_tracks], indent=2) + "\n")
    return bundle


def _coerce_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _severity_from_value(value: Any) -> str:
    lowered = str(value or "").lower()
    if lowered in {"high", "critical"}:
        return "critical"
    if lowered in {"medium", "warning"}:
        return "warning"
    return "info"


def _build_word_timestamps(turns: list[TurnModel], transcript: str, metadata: dict[str, Any] | None = None) -> list[WordTimestamp]:
    metadata = metadata or {}
    provider_words = list(metadata.get("transcript_word_timestamps", [])) or list(metadata.get("openai_word_timestamps", []))
    if provider_words:
        return [
            WordTimestamp(
                word=str(word.get("word") or ""),
                start_ms=int(word.get("start_ms", 0)),
                end_ms=int(word.get("end_ms", 0)),
                confidence=float(word.get("confidence", 0.0)),
                source=str(word.get("source") or "model"),
                speaker_id=str(word.get("speaker_id")) if word.get("speaker_id") else None,
            )
            for word in provider_words
            if str(word.get("word") or "").strip()
        ]
    if not turns and not transcript:
        return []
    words: list[WordTimestamp] = []
    if turns:
        for turn in turns:
            tokens = [token for token in re.split(r"\s+", turn.text.strip()) if token]
            if not tokens:
                continue
            duration = max(1, turn.end_ms - turn.start_ms)
            step = duration / len(tokens)
            for index, token in enumerate(tokens):
                word_start = int(turn.start_ms + index * step)
                word_end = int(turn.start_ms + (index + 1) * step)
                words.append(
                    WordTimestamp(
                        word=token,
                        start_ms=word_start,
                        end_ms=word_end,
                        confidence=turn.confidence,
                        source=turn.source or "heuristic",
                        speaker_id=turn.speaker_id,
                    )
                )
        return words
    tokens = [token for token in re.split(r"\s+", transcript.strip()) if token]
    if not tokens:
        return []
    step = 200
    cursor = 0
    for token in tokens:
        words.append(WordTimestamp(word=token, start_ms=cursor, end_ms=cursor + step, confidence=0.0))
        cursor += step
    return words


def _next_answer_turn(turns: list[TurnModel], index: int) -> TurnModel | None:
    current = turns[index]
    for candidate in turns[index + 1 :]:
        if candidate.speaker_id != current.speaker_id:
            return candidate
    return None


def _affect_tag(hesitation_score: int, directness_score: int) -> str:
    if hesitation_score >= 75:
        return "guarded"
    if directness_score >= 75 and hesitation_score <= 35:
        return "engaged"
    if hesitation_score >= 55:
        return "hesitant"
    if directness_score >= 60:
        return "calm"
    return "thoughtful"


def _signal_status(score: int) -> str:
    if score >= 75:
        return "risk"
    if score <= 35:
        return "healthy"
    return "watch"


def _signal_card(
    key: str,
    label: str,
    score: int,
    summary: str,
    evidence_items: list[Any],
    explainability: list[str],
    *,
    evidence_class: EvidenceClass = "heuristic_backed",
) -> SignalCard:
    refs: list[EvidenceRef] = []
    for item in evidence_items[:3]:
        if isinstance(item, QuestionAnalyticsRow):
            refs.append(EvidenceRef(kind="question", ref_id=item.question_id, label=item.affect_tag))
        elif isinstance(item, EventModel):
            refs.append(EvidenceRef(kind="event", ref_id=item.event_id, label=item.type))
        elif isinstance(item, SpeakerSummary):
            refs.append(EvidenceRef(kind="speaker", ref_id=item.speaker_id, label=item.role))
    return SignalCard(
        key=key,
        label=label,
        score=max(0, min(100, score)),
        confidence=0.52 if refs else 0.28,
        status=_signal_status(score),
        evidence_class=evidence_class,
        summary=summary,
        evidence_refs=refs,
        explainability_mask=sorted(set(explainability)),
    )
