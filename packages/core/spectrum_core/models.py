from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .constants import SCHEMA_VERSION

AnalysisMode = Literal["voice_profile", "conversation_analytics", "full"]
SessionStatus = Literal["created", "uploaded", "queued", "processing", "completed", "failed"]
StageState = Literal["ready", "fallback", "blocked", "missing"]
ReadinessTier = Literal["full", "partial", "transcript_only", "blocked"]
SignalStatus = Literal["healthy", "watch", "risk"]
PredictionSource = Literal["model", "heuristic", "metadata_hint", "manual_override", "benchmark_label", "unavailable"]
DisplayState = Literal["visible", "muted", "hidden", "unavailable"]
SpeakerRole = Literal["human", "ai", "unknown"]
ProviderKind = Literal["transcription", "diarization", "role_analysis", "alignment", "nonverbal_cues", "profile"]
DistributionValueType = Literal["count", "average", "percent"]
BenchmarkTaskType = Literal["sentence_emotion", "utterance_emotion", "sentiment", "diarization_overlap", "nonverbal_cue_tagging"]
EvidenceClass = Literal["benchmark_backed", "model_backed", "heuristic_backed", "metadata_backed"]
ReportSeverity = Literal["info", "watch", "risk", "critical"]
ReportFindingSource = Literal["deterministic", "provider", "hybrid"]
ConversationReportCategory = Literal[
    "intent_resolution",
    "answer_quality",
    "agent_latency",
    "human_wait",
    "turn_taking",
    "interruption_overlap",
    "clarification_loop",
    "human_uncertainty",
    "friction_or_escalation",
    "agent_recovery",
    "role_confidence",
    "transcript_or_audio_risk",
]


class DatasetReference(BaseModel):
    dataset_id: str | None = None
    title: str | None = None
    access_type: str | None = None
    split: str | None = None
    source_path: str | None = None
    reference_label: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactPaths(BaseModel):
    original_audio_path: str | None = None
    normalized_audio_path: str | None = None
    telephony_audio_path: str | None = None
    waveform_path: str | None = None
    spectrogram_path: str | None = None
    diarization_path: str | None = None
    prosody_path: str | None = None
    nonverbal_cues_path: str | None = None
    timeline_tracks_path: str | None = None
    result_path: str | None = None
    timeline_path: str | None = None
    quality_path: str | None = None
    events_path: str | None = None
    questions_path: str | None = None
    environment_path: str | None = None
    signals_path: str | None = None
    profile_path: str | None = None
    transcript_words_path: str | None = None
    transcript_sentences_path: str | None = None
    transcript_tokens_path: str | None = None
    roles_path: str | None = None
    bundle_path: str | None = None


class LabelPrediction(BaseModel):
    label: str = "unknown"
    confidence: float = 0.0
    source: PredictionSource = "unavailable"
    display_state: DisplayState = "unavailable"
    summary: str | None = None
    warning_flags: list[str] = Field(default_factory=list)


class LangMixPrediction(BaseModel):
    label: str = "unknown"
    english_ratio: float = 0.0
    language_ratios: dict[str, float] = Field(default_factory=dict)
    source: PredictionSource = "unavailable"
    display_state: DisplayState = "unavailable"
    summary: str | None = None
    warning_flags: list[str] = Field(default_factory=list)


class TimeWindow(BaseModel):
    start_ms: int
    end_ms: int
    label: str | None = None


class QualitySummary(BaseModel):
    speech_ratio: float = 0.0
    noise_score: float = 1.0
    noise_ratio: float = 0.0
    avg_snr_db: float | None = None
    clipping_ratio: float = 0.0
    vad_fp_count: int = 0
    vad_fn_count: int = 0
    noisy_segment_count: int = 0
    low_snr_windows: list[TimeWindow] = Field(default_factory=list)
    is_usable: bool = False
    warning_flags: list[str] = Field(default_factory=list)


class MetricSummary(BaseModel):
    name: str
    value: float | int | str | bool | None
    unit: str | None = None
    confidence: float = 0.0
    description: str | None = None


class SpeakerSummary(BaseModel):
    speaker_id: str
    role: str | None = None
    speaker_role: SpeakerRole = "unknown"
    role_confidence: float = 0.0
    role_source: PredictionSource = "unavailable"
    talk_ratio: float = 0.0
    avg_turn_ms: float = 0.0
    interruption_count: int = 0
    overlap_ms: float = 0.0
    wpm: float | None = None


class TurnModel(BaseModel):
    turn_id: str
    speaker_id: str
    start_ms: int
    end_ms: int
    text: str = ""
    speaker_role: SpeakerRole = "unknown"
    response_latency_ms: int | None = None
    filler_count: int = 0
    uncertainty_markers: int = 0
    word_count: int = 0
    confidence: float = 0.0
    source: str | None = None
    rms_energy: float | None = None
    pitch_variance: float | None = None
    noise_ratio: float | None = None
    speech_rate_wpm: float | None = None
    section: str | None = None


class EvidenceRef(BaseModel):
    kind: str
    ref_id: str
    label: str | None = None


class EventModel(BaseModel):
    event_id: str
    type: str
    begin_ms: int
    end_ms: int
    speaker_ids: list[str] = Field(default_factory=list)
    severity: Literal["info", "warning", "critical"] = "info"
    confidence: float = 0.0
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    detail: str | None = None
    label: str | None = None


class AdapterRuntime(BaseModel):
    key: str
    name: str
    category: str
    available: bool
    enabled_by_default: bool
    token_required: bool = False
    token_present: bool = False
    comparison_only: bool = False
    prototype_only: bool = False
    license_class: str
    warning: str | None = None


class Diagnostics(BaseModel):
    adapters: list[AdapterRuntime] = Field(default_factory=list)
    enabled_comparisons: list[str] = Field(default_factory=list)
    license_warnings: list[str] = Field(default_factory=list)
    confidence_caveats: list[str] = Field(default_factory=list)
    fallback_logic: list[str] = Field(default_factory=list)
    degraded_reasons: list[str] = Field(default_factory=list)
    provider_decisions: list["ProviderDecision"] = Field(default_factory=list)


class ProfileSummary(BaseModel):
    accent_broad: LabelPrediction = Field(default_factory=LabelPrediction)
    accent_fine: LabelPrediction = Field(default_factory=LabelPrediction)
    voice_presentation: LabelPrediction = Field(default_factory=LabelPrediction)
    age_band: LabelPrediction = Field(default_factory=LabelPrediction)
    lang_mix: LangMixPrediction = Field(default_factory=LangMixPrediction)


class WordTimestamp(BaseModel):
    word: str
    start_ms: int
    end_ms: int
    confidence: float = 0.0
    source: str = "heuristic"
    speaker_id: str | None = None


class ProfileField(BaseModel):
    key: str
    label: str
    value: str = "unknown"
    confidence: float = 0.0
    source: PredictionSource = "unavailable"
    display_state: DisplayState = "unavailable"
    summary: str | None = None
    warning_flags: list[str] = Field(default_factory=list)
    details: dict[str, float | str] = Field(default_factory=dict)


class ProfileCoverageSummary(BaseModel):
    model_backed_fields: list[str] = Field(default_factory=list)
    metadata_only_fields: list[str] = Field(default_factory=list)
    hidden_fields: list[str] = Field(default_factory=list)
    unavailable_fields: list[str] = Field(default_factory=list)


class SentenceEmotionSpan(BaseModel):
    sentence_id: str
    speaker_id: str
    turn_id: str
    speaker_role: SpeakerRole = "unknown"
    start_ms: int
    end_ms: int
    text: str
    emotion_label: str = "unlabeled"
    emotion_scores: dict[str, float] = Field(default_factory=dict)
    sentiment_label: str | None = None
    confidence: float = 0.0
    source: PredictionSource = "unavailable"
    display_state: DisplayState = "unavailable"
    explainability_mask: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class TokenEmotionSpan(BaseModel):
    token_id: str
    turn_id: str
    sentence_id: str
    word: str
    start_ms: int
    end_ms: int
    emotion_label: str = "unlabeled"
    confidence: float = 0.0
    display_state: DisplayState = "unavailable"
    inherited_from_sentence: bool = True


class DiarizationSegment(BaseModel):
    segment_id: str
    speaker_id: str
    start_ms: int
    end_ms: int
    confidence: float = 0.0
    source: PredictionSource = "unavailable"
    display_state: DisplayState = "unavailable"
    label: str | None = None


class DiarizationSummary(BaseModel):
    readiness_state: StageState = "missing"
    source: PredictionSource = "unavailable"
    confidence: float = 0.0
    segments: list[DiarizationSegment] = Field(default_factory=list)
    overlap_windows: list[TimeWindow] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class SpeakerRoleAssignment(BaseModel):
    speaker_id: str
    speaker_role: SpeakerRole = "unknown"
    confidence: float = 0.0
    source: PredictionSource = "unavailable"
    notes: list[str] = Field(default_factory=list)


class SpeakerRoleSummary(BaseModel):
    primary_human_speaker_id: str | None = None
    primary_ai_speaker_id: str | None = None
    assignments: list[SpeakerRoleAssignment] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class WaveformArtifact(BaseModel):
    duration_ms: int = 0
    sample_count: int = 0
    bucket_count: int = 0
    peaks: list[float] = Field(default_factory=list)


class SpectrogramArtifact(BaseModel):
    readiness_state: StageState = "missing"
    image_path: str | None = None
    width: int = 0
    height: int = 0
    notes: list[str] = Field(default_factory=list)


class ProsodyPoint(BaseModel):
    timestamp_ms: int
    value: float


class ProsodyTrack(BaseModel):
    key: str
    label: str
    unit: str
    source: PredictionSource = "heuristic"
    display_state: DisplayState = "muted"
    samples: list[ProsodyPoint] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class NonverbalCue(BaseModel):
    cue_id: str
    type: str
    family: str
    label: str
    start_ms: int
    end_ms: int
    confidence: float = 0.0
    source: PredictionSource = "unavailable"
    display_state: DisplayState = "unavailable"
    attribution_state: Literal["strong", "muted", "unassigned"] = "unassigned"
    speaker_id: str | None = None
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    explainability_mask: list[str] = Field(default_factory=list)


class TimelineTrackItem(BaseModel):
    item_id: str
    label: str
    start_ms: int
    end_ms: int
    tone: str = "default"
    speaker_id: str | None = None
    confidence: float | None = None
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class TimelineTrack(BaseModel):
    track_id: str
    label: str
    type: str
    status: StageState = "ready"
    items: list[TimelineTrackItem] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class TranscriptViewSummary(BaseModel):
    sentence_count: int = 0
    highlighted_sentence_count: int = 0
    token_overlay_count: int = 0
    emotion_labels: list[str] = Field(default_factory=list)


class ContentSummary(BaseModel):
    transcript: str = ""
    words: list[WordTimestamp] = Field(default_factory=list)
    sentences: list[SentenceEmotionSpan] = Field(default_factory=list)
    tokens: list[TokenEmotionSpan] = Field(default_factory=list)
    fillers: list[str] = Field(default_factory=list)
    uncertainty_markers: list[str] = Field(default_factory=list)
    topic_labels: list[str] = Field(default_factory=list)
    view_summary: TranscriptViewSummary = Field(default_factory=TranscriptViewSummary)


class EnvironmentSummary(BaseModel):
    primary: str = "unknown"
    tags: list[str] = Field(default_factory=list)
    contamination_windows: list[TimeWindow] = Field(default_factory=list)
    taxonomy_status: StageState = "fallback"
    notes: list[str] = Field(default_factory=list)


class QuestionAnalyticsRow(BaseModel):
    question_id: str
    question_text: str
    question_turn_id: str
    answer_turn_id: str
    response_latency_ms: int
    answer_duration_ms: int
    directness_score: int
    hesitation_score: int
    affect_tag: str
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    explainability_mask: list[str] = Field(default_factory=list)


class SignalCard(BaseModel):
    key: str
    label: str
    score: int
    confidence: float = 0.0
    status: SignalStatus = "watch"
    evidence_class: EvidenceClass = "heuristic_backed"
    summary: str
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    explainability_mask: list[str] = Field(default_factory=list)


class ConversationReportExecutiveSummary(BaseModel):
    overall_diagnosis: str = "Conversation report has not been generated yet."
    call_outcome: str = "unknown"
    top_risks: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    recommended_next_action: str = "Run or rebuild the session analysis to generate a report."


class ConversationReportFinding(BaseModel):
    finding_id: str
    category: ConversationReportCategory
    title: str
    severity: ReportSeverity = "watch"
    confidence: float = 0.0
    claim: str
    impact: str
    likely_cause: str
    time_window: TimeWindow | None = None
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    related_metrics: dict[str, float | int | str | bool | None] = Field(default_factory=dict)
    suggested_next_check: str
    source: ReportFindingSource = "deterministic"


class ConversationReportSection(BaseModel):
    label: str
    summary: str = ""
    confidence: float = 0.0
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    details: list[str] = Field(default_factory=list)


class ConversationReportTrustLimit(BaseModel):
    key: str
    label: str
    severity: ReportSeverity = "watch"
    confidence: float = 0.0
    summary: str
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class ConversationReport(BaseModel):
    report_version: str = "0.1"
    report_type: str = "human_ai_diagnostic"
    executive_summary: ConversationReportExecutiveSummary = Field(default_factory=ConversationReportExecutiveSummary)
    findings: list[ConversationReportFinding] = Field(default_factory=list)
    conversation_arc: list[ConversationReportSection] = Field(default_factory=list)
    human_experience: ConversationReportSection = Field(default_factory=lambda: ConversationReportSection(label="Human experience"))
    agent_behavior: ConversationReportSection = Field(default_factory=lambda: ConversationReportSection(label="Agent behavior"))
    trust_limits: list[ConversationReportTrustLimit] = Field(default_factory=list)
    context: dict[str, str | float | int | bool | None] = Field(default_factory=dict)


class StageStatus(BaseModel):
    key: str
    label: str
    status: StageState
    summary: str
    caveats: list[str] = Field(default_factory=list)
    adapter_keys: list[str] = Field(default_factory=list)


class ProviderDecision(BaseModel):
    kind: ProviderKind
    provider_key: str
    used: bool = False
    cached: bool = False
    status: Literal["ready", "fallback", "blocked", "missing"] = "missing"
    notes: list[str] = Field(default_factory=list)


class SessionDescriptor(BaseModel):
    session_id: str
    title: str
    session_type: str = "analysis"
    analysis_mode: AnalysisMode
    language: str | None = None
    region: str | None = None
    call_channel: str | None = None
    source_type: str = "direct_audio_file"
    dataset_id: str | None = None
    dataset_title: str | None = None
    reference_label: str | None = None
    duration_sec: float = 0.0
    speaker_count: int = 0
    status: str = "completed"
    readiness_tier: ReadinessTier = "blocked"


class SessionBundle(BaseModel):
    schema_version: str = SCHEMA_VERSION
    session: SessionDescriptor
    source: DatasetReference | None = None
    artifacts: ArtifactPaths = Field(default_factory=ArtifactPaths)
    quality: QualitySummary = Field(default_factory=QualitySummary)
    environment: EnvironmentSummary = Field(default_factory=EnvironmentSummary)
    profile: ProfileSummary = Field(default_factory=ProfileSummary)
    profile_display: list[ProfileField] = Field(default_factory=list)
    profile_coverage: ProfileCoverageSummary = Field(default_factory=ProfileCoverageSummary)
    speaker_roles: SpeakerRoleSummary = Field(default_factory=SpeakerRoleSummary)
    diarization: DiarizationSummary = Field(default_factory=DiarizationSummary)
    waveform: WaveformArtifact = Field(default_factory=WaveformArtifact)
    spectrogram: SpectrogramArtifact = Field(default_factory=SpectrogramArtifact)
    prosody_tracks: list[ProsodyTrack] = Field(default_factory=list)
    nonverbal_cues: list[NonverbalCue] = Field(default_factory=list)
    timeline_tracks: list[TimelineTrack] = Field(default_factory=list)
    speakers: list[SpeakerSummary] = Field(default_factory=list)
    turns: list[TurnModel] = Field(default_factory=list)
    events: list[EventModel] = Field(default_factory=list)
    questions: list[QuestionAnalyticsRow] = Field(default_factory=list)
    content: ContentSummary = Field(default_factory=ContentSummary)
    signals: list[SignalCard] = Field(default_factory=list)
    conversation_report: ConversationReport = Field(default_factory=ConversationReport)
    metrics: dict[str, MetricSummary] = Field(default_factory=dict)
    diagnostics: Diagnostics = Field(default_factory=Diagnostics)
    stage_status: list[StageStatus] = Field(default_factory=list)


class SessionResult(BaseModel):
    job_id: str
    analysis_mode: AnalysisMode
    schema_version: str = SCHEMA_VERSION
    duration_sec: float
    speaker_count: int
    transcript: str = ""
    quality: QualitySummary = Field(default_factory=QualitySummary)
    profile: ProfileSummary = Field(default_factory=ProfileSummary)
    metrics: dict[str, MetricSummary] = Field(default_factory=dict)
    speakers: list[SpeakerSummary] = Field(default_factory=list)
    turns: list[TurnModel] = Field(default_factory=list)
    events: list[EventModel] = Field(default_factory=list)
    diagnostics: Diagnostics = Field(default_factory=Diagnostics)
    source: DatasetReference | None = None
    artifacts: ArtifactPaths = Field(default_factory=ArtifactPaths)


class SessionRecord(BaseModel):
    job_id: str
    analysis_mode: AnalysisMode
    status: SessionStatus
    created_at: str
    updated_at: str
    original_filename: str | None = None
    result_path: str | None = None
    error: str | None = None


class JobActivityEntry(BaseModel):
    stage_key: str
    stage_label: str
    message: str
    completed_at: str
    percent_complete: int


class SessionJobStatus(BaseModel):
    job_id: str
    status: SessionStatus
    stage_key: str | None = None
    stage_label: str | None = None
    stage_index: int = 0
    stage_count: int = 0
    percent_complete: int = 0
    message: str = ""
    eta_seconds: int = 0
    started_at: str | None = None
    updated_at: str
    error: str | None = None
    history: list[JobActivityEntry] = Field(default_factory=list)


class MetricDefinition(BaseModel):
    key: str
    label: str
    unit: str | None = None
    description: str


class SessionOverview(BaseModel):
    session_id: str
    title: str
    analysis_mode: AnalysisMode
    source_type: str
    dataset_id: str | None = None
    language: str | None = None
    duration_sec: float = 0.0
    usable: bool = False
    top_signal_keys: list[str] = Field(default_factory=list)
    quality: QualitySummary = Field(default_factory=QualitySummary)


class DatasetOverview(BaseModel):
    dataset_id: str
    title: str
    access_type: str | None = None
    source_type: str = "materialized_audio_dataset"
    health_status: str = "manifest_only"
    health_detail: str | None = None
    language_labels: list[str] = Field(default_factory=list)
    sample_count: int = 0
    imported_count: int = 0
    adapter_coverage: list[str] = Field(default_factory=list)
    stage_completeness: dict[str, int] = Field(default_factory=dict)


class CohortFilters(BaseModel):
    date_from: str | None = None
    date_to: str | None = None
    dataset_ids: list[str] = Field(default_factory=list)
    source_types: list[str] = Field(default_factory=list)
    analysis_modes: list[AnalysisMode] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    duration_band: str | None = None
    quality_band: str | None = None
    readiness_tiers: list[ReadinessTier] = Field(default_factory=list)
    role_presence: str | None = None
    projects: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class CohortKPI(BaseModel):
    key: str
    label: str
    value: float
    unit: str | None = None
    delta: float | None = None


class CohortTrendPoint(BaseModel):
    bucket: str
    run_count: int = 0
    usable_run_rate: float = 0.0
    avg_snr_db: float = 0.0
    hesitation_avg: float = 0.0
    friction_avg: float = 0.0
    rapport_avg: float = 0.0
    frustration_avg: float = 0.0


class CohortDistributionItem(BaseModel):
    key: str
    label: str
    value: float
    value_type: DistributionValueType = "count"


class CohortDistribution(BaseModel):
    key: str
    label: str
    items: list[CohortDistributionItem] = Field(default_factory=list)


class CohortPhaseSummary(BaseModel):
    phase: Literal["first_third", "middle_third", "final_third"]
    hesitation_avg: float = 0.0
    friction_avg: float = 0.0
    rapport_avg: float = 0.0
    frustration_avg: float = 0.0
    dominant_emotion: str = "unlabeled"


class CohortSessionRow(BaseModel):
    session_id: str
    title: str
    source_type: str
    dataset_id: str | None = None
    analysis_mode: AnalysisMode
    language: str | None = None
    duration_sec: float = 0.0
    readiness_tier: ReadinessTier = "blocked"
    usable: bool = False
    quality_band: str = "unknown"
    human_present: bool = False
    ai_present: bool = False
    top_signal: str | None = None


class CohortSummary(BaseModel):
    filters: CohortFilters = Field(default_factory=CohortFilters)
    kpis: list[CohortKPI] = Field(default_factory=list)
    phase_summaries: list[CohortPhaseSummary] = Field(default_factory=list)
    dominant_emotions: list[CohortDistributionItem] = Field(default_factory=list)
    runs: list[CohortSessionRow] = Field(default_factory=list)


class BenchmarkTaskDefinition(BaseModel):
    task_type: BenchmarkTaskType
    label: str
    metric_keys: list[str] = Field(default_factory=list)


class BenchmarkRegistryEntry(BaseModel):
    benchmark_id: str
    dataset_id: str
    title: str
    status: Literal["ready", "available", "gated", "missing"] = "available"
    tasks: list[BenchmarkTaskDefinition] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class BenchmarkMetricResult(BaseModel):
    key: str
    label: str
    value: float
    unit: str | None = None
    previous_value: float | None = None
    delta: float | None = None
    regressed: bool = False


class BenchmarkResult(BaseModel):
    benchmark_id: str
    dataset_id: str
    task_type: BenchmarkTaskType
    split: str = "default"
    status: Literal["ready", "skipped", "missing"] = "missing"
    metrics: list[BenchmarkMetricResult] = Field(default_factory=list)
    run_timestamp: str | None = None
    model_stack: list[str] = Field(default_factory=list)
    support_level: EvidenceClass = "heuristic_backed"
    regressed: bool = False
    notes: list[str] = Field(default_factory=list)
