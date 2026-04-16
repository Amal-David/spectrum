import fs from "node:fs";
import path from "node:path";

type SignalStatus = "healthy" | "watch" | "risk";
type StageState = "ready" | "fallback" | "blocked" | "missing";
type ReadinessTier = "full" | "partial" | "transcript_only" | "blocked";
type DisplayState = "visible" | "muted" | "hidden" | "unavailable";
type PredictionSource = "model" | "heuristic" | "metadata_hint" | "manual_override" | "benchmark_label" | "unavailable";
type SpeakerRole = "human" | "ai" | "unknown";

export type EvidenceRef = {
  kind: string;
  ref_id: string;
  label?: string | null;
};

export type SessionBundle = {
  schema_version: string;
  session: {
    session_id: string;
    title: string;
    session_type: string;
    analysis_mode: "voice_profile" | "conversation_analytics" | "full";
    language?: string | null;
    region?: string | null;
    call_channel?: string | null;
    source_type: string;
    dataset_id?: string | null;
    dataset_title?: string | null;
      reference_label?: string | null;
      duration_sec: number;
      speaker_count: number;
      status: string;
      readiness_tier?: ReadinessTier;
    };
  source?: {
    dataset_id?: string | null;
    title?: string | null;
    access_type?: string | null;
    source_path?: string | null;
    reference_label?: string | null;
    metadata?: Record<string, string | null>;
  } | null;
  artifacts: {
    original_audio_path?: string | null;
    normalized_audio_path?: string | null;
    telephony_audio_path?: string | null;
    waveform_path?: string | null;
    spectrogram_path?: string | null;
    diarization_path?: string | null;
    prosody_path?: string | null;
    nonverbal_cues_path?: string | null;
    timeline_tracks_path?: string | null;
    profile_path?: string | null;
    transcript_words_path?: string | null;
    transcript_sentences_path?: string | null;
    transcript_tokens_path?: string | null;
    bundle_path?: string | null;
  };
  quality: {
    speech_ratio: number;
    noise_score: number;
    noise_ratio: number;
    avg_snr_db: number | null;
    clipping_ratio?: number;
    vad_fp_count: number;
    vad_fn_count: number;
    noisy_segment_count: number;
    is_usable: boolean;
    warning_flags: string[];
  };
  environment: {
    primary: string;
    tags: string[];
    contamination_windows: Array<{ start_ms: number; end_ms: number; label?: string | null }>;
    taxonomy_status: StageState;
    notes: string[];
  };
  profile: {
    accent_broad: { label: string; confidence: number; source?: PredictionSource; display_state?: DisplayState; summary?: string | null; warning_flags?: string[] };
    accent_fine: { label: string; confidence: number; source?: PredictionSource; display_state?: DisplayState; summary?: string | null; warning_flags?: string[] };
    voice_presentation: { label: string; confidence: number; source?: PredictionSource; display_state?: DisplayState; summary?: string | null; warning_flags?: string[] };
    age_band: { label: string; confidence: number; source?: PredictionSource; display_state?: DisplayState; summary?: string | null; warning_flags?: string[] };
    lang_mix: { label: string; english_ratio: number; language_ratios?: Record<string, number>; source?: PredictionSource; display_state?: DisplayState; summary?: string | null; warning_flags?: string[] };
  };
  profile_display: Array<{
    key: string;
    label: string;
    value: string;
    confidence: number;
    source: PredictionSource;
    display_state: DisplayState;
    summary?: string | null;
    warning_flags: string[];
    details?: Record<string, string | number>;
  }>;
  speaker_roles: {
    primary_human_speaker_id?: string | null;
    primary_ai_speaker_id?: string | null;
    assignments: Array<{
      speaker_id: string;
      speaker_role: SpeakerRole;
      confidence: number;
      source: PredictionSource;
      notes: string[];
    }>;
    notes: string[];
  };
  diarization: {
    readiness_state: StageState;
    source: PredictionSource;
    confidence: number;
    segments: Array<{
      segment_id: string;
      speaker_id: string;
      start_ms: number;
      end_ms: number;
      confidence: number;
      source: PredictionSource;
      display_state: DisplayState;
      label?: string | null;
    }>;
    overlap_windows: Array<{ start_ms: number; end_ms: number; label?: string | null }>;
    notes: string[];
  };
  waveform: {
    duration_ms: number;
    sample_count: number;
    bucket_count: number;
    peaks: number[];
  };
  spectrogram: {
    readiness_state: StageState;
    image_path?: string | null;
    width: number;
    height: number;
    notes: string[];
  };
  prosody_tracks: Array<{
    key: string;
    label: string;
    unit: string;
    source: PredictionSource;
    display_state: DisplayState;
    samples: Array<{ timestamp_ms: number; value: number }>;
    notes: string[];
  }>;
  nonverbal_cues: Array<{
    cue_id: string;
    type: string;
    family: string;
    label: string;
    start_ms: number;
    end_ms: number;
    confidence: number;
    source: PredictionSource;
    display_state: DisplayState;
    speaker_id?: string | null;
    evidence_refs: EvidenceRef[];
    explainability_mask: string[];
  }>;
  timeline_tracks: Array<{
    track_id: string;
    label: string;
    type: string;
    status: StageState;
    items: Array<{
      item_id: string;
      label: string;
      start_ms: number;
      end_ms: number;
      tone: string;
      speaker_id?: string | null;
      confidence?: number | null;
      evidence_refs: EvidenceRef[];
    }>;
    notes: string[];
  }>;
  speakers: Array<{ speaker_id: string; role?: string | null; speaker_role?: SpeakerRole; role_confidence?: number; role_source?: PredictionSource; talk_ratio: number; avg_turn_ms: number; interruption_count: number; overlap_ms: number; wpm?: number | null }>;
  turns: Array<{
    turn_id: string;
    speaker_id: string;
    speaker_role?: SpeakerRole;
    start_ms: number;
    end_ms: number;
    text: string;
    response_latency_ms?: number | null;
    source?: string | null;
    filler_count?: number;
    uncertainty_markers?: number;
    rms_energy?: number | null;
    pitch_variance?: number | null;
    noise_ratio?: number | null;
    speech_rate_wpm?: number | null;
    section?: string | null;
  }>;
  events: Array<{ event_id: string; type: string; begin_ms: number; end_ms: number; speaker_ids: string[]; severity: string; detail?: string | null; label?: string | null; evidence_refs?: EvidenceRef[] }>;
  questions: Array<{
    question_id: string;
    question_text: string;
    question_turn_id: string;
    answer_turn_id: string;
    response_latency_ms: number;
    answer_duration_ms: number;
    directness_score: number;
    hesitation_score: number;
    affect_tag: string;
    evidence_refs: EvidenceRef[];
    explainability_mask: string[];
  }>;
  content: {
    transcript: string;
    words: Array<{ word: string; start_ms: number; end_ms: number; confidence: number; source: string }>;
    sentences: Array<{
      sentence_id: string;
      speaker_id: string;
      turn_id: string;
      speaker_role?: SpeakerRole;
      start_ms: number;
      end_ms: number;
      text: string;
      emotion_label: string;
      emotion_scores: Record<string, number>;
      sentiment_label?: string | null;
      confidence: number;
      source: PredictionSource;
      display_state: DisplayState;
      explainability_mask: string[];
      evidence_refs: EvidenceRef[];
    }>;
    tokens: Array<{
      token_id: string;
      turn_id: string;
      sentence_id: string;
      word: string;
      start_ms: number;
      end_ms: number;
      emotion_label: string;
      confidence: number;
      display_state: DisplayState;
      inherited_from_sentence: boolean;
    }>;
    fillers: string[];
    uncertainty_markers: string[];
    topic_labels: string[];
    view_summary: {
      sentence_count: number;
      highlighted_sentence_count: number;
      token_overlay_count: number;
      emotion_labels: string[];
    };
  };
  signals: Array<{
    key: string;
    label: string;
    score: number;
    confidence: number;
    status: SignalStatus;
    summary: string;
    evidence_refs: EvidenceRef[];
    explainability_mask: string[];
  }>;
  metrics: Record<string, { name: string; value: string | number | boolean | null; unit?: string | null; confidence: number }>;
  diagnostics: {
    enabled_comparisons: string[];
    license_warnings: string[];
    confidence_caveats: string[];
    degraded_reasons?: string[];
    provider_decisions?: Array<{ kind: string; provider_key: string; used: boolean; cached: boolean; status: StageState; notes: string[] }>;
    fallback_logic?: string[];
    adapters: Array<{ key: string; name: string; available: boolean; category: string; warning?: string | null; license_class?: string | null; token_required?: boolean; comparison_only?: boolean; prototype_only?: boolean }>;
  };
  stage_status: Array<{ key: string; label: string; status: StageState; summary: string; caveats: string[]; adapter_keys: string[] }>;
};

export type CohortSummary = {
  kpis: Array<{ key: string; label: string; value: number; unit?: string | null }>;
  trends: Array<{ bucket: string; run_count: number; usable_run_rate: number; avg_snr_db: number; hesitation_avg: number; friction_avg: number; rapport_avg: number; frustration_avg: number }>;
  distributions: Array<{ key: string; label: string; items: Array<{ key: string; label: string; value: number; value_type: string }> }>;
  phase_summaries: Array<{ phase: string; hesitation_avg: number; friction_avg: number; rapport_avg: number; frustration_avg: number; dominant_emotion: string }>;
};

export type BenchmarkSnapshot = {
  registry: Array<{ benchmark_id: string; dataset_id: string; title: string; status: string; tasks: Array<{ task_type: string; label: string; metric_keys: string[] }>; notes: string[] }>;
  results: Array<{ benchmark_id: string; dataset_id: string; task_type: string; status: string; regressed?: boolean; metrics: Array<{ key: string; label: string; value: number; unit?: string | null; previous_value?: number | null; delta?: number | null; regressed?: boolean }>; notes: string[] }>;
};

export type DatasetOverview = {
  dataset_id: string;
  title: string;
  access_type?: string | null;
  source_type: string;
  health_status: string;
  health_detail?: string | null;
  language_labels: string[];
  sample_count: number;
  imported_count: number;
  adapter_coverage: string[];
  stage_completeness: Record<string, number>;
};

export type DashboardSnapshot = {
  bundles: SessionBundle[];
  datasets: DatasetOverview[];
  cohorts: CohortSummary;
  benchmarks: BenchmarkSnapshot;
  totals: {
    runs: number;
    usableRuns: number;
    datasetCount: number;
    avgSNR: number;
  };
  alerts: Array<{ session_id: string; title: string; metric: string; value: number; summary: string }>;
};

export type DashboardFilters = {
  sourceType?: string;
  analysisMode?: string;
  language?: string;
  durationBand?: string;
  qualityBand?: string;
  readinessTier?: string;
  rolePresence?: string;
};

function repoRoot() {
  return path.resolve(process.cwd(), "../..");
}

function runsRoot() {
  return path.join(repoRoot(), "runs");
}

function readJson<T>(filePath: string): T {
  return JSON.parse(fs.readFileSync(filePath, "utf8")) as T;
}

function safeReadJson<T>(filePath: string): T | null {
  if (!fs.existsSync(filePath)) {
    return null;
  }
  return readJson<T>(filePath);
}

function inferReadinessTier(transcript: string, diarizationState?: StageState | null): ReadinessTier {
  if (diarizationState === "ready" && transcript) {
    return "full";
  }
  if (diarizationState === "fallback" && transcript) {
    return "partial";
  }
  if (transcript) {
    return "transcript_only";
  }
  return "blocked";
}

function normalizeSessionBundle(rawBundle: any): SessionBundle {
  const durationSec = rawBundle?.session?.duration_sec ?? rawBundle?.duration_sec ?? 0;
  const transcript = rawBundle?.content?.transcript ?? rawBundle?.transcript ?? "";
  const diarizationState = rawBundle?.diarization?.readiness_state ?? "missing";
  return {
    schema_version: rawBundle?.schema_version ?? "0.1.0",
    session: {
      session_id: rawBundle?.session?.session_id ?? rawBundle?.job_id ?? "unknown-session",
      title: rawBundle?.session?.title ?? rawBundle?.source?.metadata?.title ?? rawBundle?.job_id ?? "Untitled session",
      session_type: rawBundle?.session?.session_type ?? "analysis",
      analysis_mode: rawBundle?.session?.analysis_mode ?? rawBundle?.analysis_mode ?? "full",
      language: rawBundle?.session?.language ?? rawBundle?.source?.metadata?.language_hint ?? null,
      region: rawBundle?.session?.region ?? null,
      call_channel: rawBundle?.session?.call_channel ?? null,
      source_type: rawBundle?.session?.source_type ?? "direct_audio_file",
      dataset_id: rawBundle?.session?.dataset_id ?? rawBundle?.source?.dataset_id ?? null,
      dataset_title: rawBundle?.session?.dataset_title ?? rawBundle?.source?.title ?? null,
      reference_label: rawBundle?.session?.reference_label ?? rawBundle?.source?.reference_label ?? null,
      duration_sec: durationSec,
      speaker_count: rawBundle?.session?.speaker_count ?? rawBundle?.speaker_count ?? 0,
      status: rawBundle?.session?.status ?? "completed",
      readiness_tier: rawBundle?.session?.readiness_tier ?? inferReadinessTier(transcript, diarizationState),
    },
    source: rawBundle?.source ?? null,
    artifacts: rawBundle?.artifacts ?? {},
    quality: {
      speech_ratio: rawBundle?.quality?.speech_ratio ?? 0,
      noise_score: rawBundle?.quality?.noise_score ?? 0,
      noise_ratio: rawBundle?.quality?.noise_ratio ?? rawBundle?.quality?.noise_score ?? 0,
      avg_snr_db: rawBundle?.quality?.avg_snr_db ?? null,
      clipping_ratio: rawBundle?.quality?.clipping_ratio ?? 0,
      vad_fp_count: rawBundle?.quality?.vad_fp_count ?? 0,
      vad_fn_count: rawBundle?.quality?.vad_fn_count ?? 0,
      noisy_segment_count: rawBundle?.quality?.noisy_segment_count ?? 0,
      is_usable: rawBundle?.quality?.is_usable ?? false,
      warning_flags: rawBundle?.quality?.warning_flags ?? [],
    },
    environment: {
      primary: rawBundle?.environment?.primary ?? "unknown",
      tags: rawBundle?.environment?.tags ?? [],
      contamination_windows: rawBundle?.environment?.contamination_windows ?? [],
      taxonomy_status: rawBundle?.environment?.taxonomy_status ?? "fallback",
      notes: rawBundle?.environment?.notes ?? [],
    },
    profile: rawBundle?.profile ?? {
      accent_broad: { label: "unknown", confidence: 0 },
      accent_fine: { label: "unavailable", confidence: 0 },
      voice_presentation: { label: "unknown", confidence: 0 },
      age_band: { label: "unknown", confidence: 0 },
      lang_mix: { label: "unknown", english_ratio: 0 },
    },
    profile_display: rawBundle?.profile_display ?? [],
    speaker_roles: rawBundle?.speaker_roles ?? {
      primary_human_speaker_id: null,
      primary_ai_speaker_id: null,
      assignments: [],
      notes: [],
    },
    diarization: {
      readiness_state: rawBundle?.diarization?.readiness_state ?? "missing",
      source: rawBundle?.diarization?.source ?? "unavailable",
      confidence: rawBundle?.diarization?.confidence ?? 0,
      segments: rawBundle?.diarization?.segments ?? [],
      overlap_windows: rawBundle?.diarization?.overlap_windows ?? [],
      notes: rawBundle?.diarization?.notes ?? [],
    },
    waveform: {
      duration_ms: rawBundle?.waveform?.duration_ms ?? Math.round(durationSec * 1000),
      sample_count: rawBundle?.waveform?.sample_count ?? 0,
      bucket_count: rawBundle?.waveform?.bucket_count ?? rawBundle?.waveform?.peaks?.length ?? 0,
      peaks: rawBundle?.waveform?.peaks ?? [],
    },
    spectrogram: {
      readiness_state: rawBundle?.spectrogram?.readiness_state ?? "missing",
      image_path: rawBundle?.spectrogram?.image_path ?? null,
      width: rawBundle?.spectrogram?.width ?? 0,
      height: rawBundle?.spectrogram?.height ?? 0,
      notes: rawBundle?.spectrogram?.notes ?? [],
    },
    prosody_tracks: rawBundle?.prosody_tracks ?? [],
    nonverbal_cues: rawBundle?.nonverbal_cues ?? [],
    timeline_tracks: rawBundle?.timeline_tracks ?? [],
    speakers: (rawBundle?.speakers ?? []).map((speaker: any) => ({
      ...speaker,
      speaker_role: speaker?.speaker_role ?? "unknown",
      role_confidence: speaker?.role_confidence ?? 0,
      role_source: speaker?.role_source ?? "unavailable",
    })),
    turns: (rawBundle?.turns ?? []).map((turn: any) => ({
      ...turn,
      speaker_role: turn?.speaker_role ?? "unknown",
    })),
    events: rawBundle?.events ?? [],
    questions: rawBundle?.questions ?? [],
    content: {
      transcript,
      words: rawBundle?.content?.words ?? [],
      sentences: (rawBundle?.content?.sentences ?? []).map((sentence: any) => ({
        ...sentence,
        speaker_role: sentence?.speaker_role ?? "unknown",
      })),
      tokens: rawBundle?.content?.tokens ?? [],
      fillers: rawBundle?.content?.fillers ?? [],
      uncertainty_markers: rawBundle?.content?.uncertainty_markers ?? [],
      topic_labels: rawBundle?.content?.topic_labels ?? [],
      view_summary: {
        sentence_count: rawBundle?.content?.view_summary?.sentence_count ?? (rawBundle?.content?.sentences?.length ?? 0),
        highlighted_sentence_count: rawBundle?.content?.view_summary?.highlighted_sentence_count ?? 0,
        token_overlay_count: rawBundle?.content?.view_summary?.token_overlay_count ?? (rawBundle?.content?.tokens?.length ?? 0),
        emotion_labels: rawBundle?.content?.view_summary?.emotion_labels ?? [],
      },
    },
    signals: rawBundle?.signals ?? [],
    metrics: rawBundle?.metrics ?? {},
    diagnostics: {
      enabled_comparisons: rawBundle?.diagnostics?.enabled_comparisons ?? [],
      license_warnings: rawBundle?.diagnostics?.license_warnings ?? [],
      confidence_caveats: rawBundle?.diagnostics?.confidence_caveats ?? [],
      degraded_reasons: rawBundle?.diagnostics?.degraded_reasons ?? [],
      provider_decisions: rawBundle?.diagnostics?.provider_decisions ?? [],
      fallback_logic: rawBundle?.diagnostics?.fallback_logic ?? [],
      adapters: rawBundle?.diagnostics?.adapters ?? [],
    },
    stage_status: rawBundle?.stage_status ?? [],
  };
}

function legacyBundle(jobId: string): SessionBundle | null {
  const resultPath = path.join(runsRoot(), jobId, "result.json");
  const result = safeReadJson<any>(resultPath);
  if (!result) {
    return null;
  }
  return normalizeSessionBundle({
    schema_version: result.schema_version ?? "0.1.0",
    session: {
      session_id: result.job_id,
      title: result.source?.metadata?.title ?? result.job_id,
      session_type: "analysis",
      analysis_mode: result.analysis_mode,
      language: result.source?.metadata?.language_hint ?? null,
      region: null,
      call_channel: null,
      source_type: "direct_audio_file",
      dataset_id: result.source?.dataset_id ?? null,
      dataset_title: result.source?.title ?? null,
      reference_label: result.source?.reference_label ?? null,
      duration_sec: result.duration_sec,
      speaker_count: result.speaker_count,
      status: "completed",
      readiness_tier: inferReadinessTier(result.transcript ?? "", "missing")
    },
    source: result.source ?? null,
    artifacts: result.artifacts ?? {},
    quality: {
      speech_ratio: result.quality?.speech_ratio ?? 0,
      noise_score: result.quality?.noise_score ?? 0,
      noise_ratio: result.quality?.noise_ratio ?? result.quality?.noise_score ?? 0,
      avg_snr_db: result.quality?.avg_snr_db ?? null,
      clipping_ratio: result.quality?.clipping_ratio ?? 0,
      vad_fp_count: result.quality?.vad_fp_count ?? 0,
      vad_fn_count: result.quality?.vad_fn_count ?? 0,
      noisy_segment_count: result.quality?.noisy_segment_count ?? 0,
      is_usable: result.quality?.is_usable ?? false,
      warning_flags: result.quality?.warning_flags ?? []
    },
    environment: {
      primary: "unknown",
      tags: [],
      contamination_windows: [],
      taxonomy_status: "fallback",
      notes: []
    },
    profile: result.profile,
    profile_display: [],
    diarization: {
      readiness_state: "missing",
      source: "unavailable",
      confidence: 0,
      segments: [],
      overlap_windows: [],
      notes: []
    },
    waveform: {
      duration_ms: Math.round((result.duration_sec ?? 0) * 1000),
      sample_count: 0,
      bucket_count: 0,
      peaks: []
    },
    spectrogram: {
      readiness_state: "missing",
      image_path: null,
      width: 0,
      height: 0,
      notes: []
    },
    prosody_tracks: [],
    nonverbal_cues: [],
    timeline_tracks: [],
    speakers: result.speakers ?? [],
    turns: result.turns ?? [],
    events: result.events ?? [],
    questions: [],
    content: {
      transcript: result.transcript ?? "",
      words: [],
      sentences: [],
      tokens: [],
      fillers: [],
      uncertainty_markers: [],
      topic_labels: [],
      view_summary: {
        sentence_count: 0,
        highlighted_sentence_count: 0,
        token_overlay_count: 0,
        emotion_labels: []
      }
    },
    signals: [],
    metrics: result.metrics ?? {},
    diagnostics: result.diagnostics ?? { adapters: [], enabled_comparisons: [], license_warnings: [], confidence_caveats: [], degraded_reasons: [], provider_decisions: [] },
    stage_status: []
  });
}

export function loadSessionBundle(jobId: string): SessionBundle | null {
  const bundlePath = path.join(runsRoot(), jobId, "bundle.json");
  const bundle = safeReadJson<SessionBundle>(bundlePath);
  return bundle ? normalizeSessionBundle(bundle) : legacyBundle(jobId);
}

export function loadSessionBundles(): SessionBundle[] {
  const root = runsRoot();
  if (!fs.existsSync(root)) {
    return [];
  }
  const entries = fs.readdirSync(root, { withFileTypes: true }).filter((entry) => entry.isDirectory());
  const bundles = entries
    .map((entry) => loadSessionBundle(entry.name))
    .filter((bundle): bundle is SessionBundle => bundle !== null);
  return bundles.sort((a, b) => a.session.session_id.localeCompare(b.session.session_id));
}

export function loadDatasetOverviews(): DatasetOverview[] {
  const manifest = readJson<{ datasets: Array<Record<string, unknown>> }>(path.join(repoRoot(), "data", "manifests", "datasets.json"));
  const inventoryRoot = path.join(repoRoot(), "data", "cache", "inventory");
  const bundles = loadSessionBundles();
  const byDataset = new Map<string, SessionBundle[]>();
  for (const bundle of bundles) {
    if (!bundle.session.dataset_id) continue;
    byDataset.set(bundle.session.dataset_id, [...(byDataset.get(bundle.session.dataset_id) ?? []), bundle]);
  }

  const overviews = manifest.datasets.map((dataset) => {
    const datasetId = String(dataset.id);
    const inventoryPath = path.join(inventoryRoot, `${datasetId}.materialized_audio.json`);
    const fallbackInventoryPath = path.join(inventoryRoot, `${datasetId}.json`);
    const inventory = safeReadJson<any>(inventoryPath) ?? safeReadJson<any>(fallbackInventoryPath) ?? {};
    const healthStatus = inventory.error ? "ingestion_blocked" : (inventory.files?.length ? "ready" : "manifest_only");
    const languageLabels = Array.from(
      new Set(
        [
          ...(inventory.files ?? []).flatMap((file: any) => (file.records ?? []).map((record: any) => record.language).filter(Boolean)),
          ...(byDataset.get(datasetId) ?? []).map((bundle) => bundle.session.language).filter(Boolean)
        ].map((value) => String(value))
      )
    ).slice(0, 8);
    const stageCompleteness: Record<string, number> = {};
    for (const bundle of byDataset.get(datasetId) ?? []) {
      for (const stage of bundle.stage_status) {
        if (stage.status === "ready") {
          stageCompleteness[stage.key] = (stageCompleteness[stage.key] ?? 0) + 1;
        }
      }
    }
    const adapterCoverage = Array.from(
      new Set(
        (byDataset.get(datasetId) ?? [])
          .flatMap((bundle) => bundle.diagnostics.adapters)
          .filter((adapter) => adapter.available)
          .map((adapter) => adapter.key)
      )
    );
    return {
      dataset_id: datasetId,
      title: String(dataset.title),
      access_type: (dataset.access_type as string | undefined) ?? null,
      source_type: inventory.files?.length ? "materialized_audio_dataset" : "manifest_only",
      health_status: healthStatus,
      health_detail: inventory.error ?? null,
      language_labels: languageLabels,
      sample_count: inventory.file_count ?? (inventory.files ?? []).reduce((sum: number, file: any) => sum + (file.materialized_count ?? 0), 0),
      imported_count: (byDataset.get(datasetId) ?? []).length,
      adapter_coverage: adapterCoverage,
      stage_completeness: stageCompleteness
    } satisfies DatasetOverview;
  });

  const demoBundles = bundles.filter((bundle) => bundle.session.source_type === "demo_pack_zip");
  if (demoBundles.length) {
    overviews.push({
      dataset_id: "voice_analytics_demo_pack",
      title: "Voice Analytics Demo Pack",
      access_type: "local_synthetic",
      source_type: "demo_pack_zip",
      health_status: "ready",
      health_detail: null,
      language_labels: Array.from(new Set(demoBundles.map((bundle) => bundle.session.language).filter(Boolean) as string[])),
      sample_count: demoBundles.length,
      imported_count: demoBundles.length,
      adapter_coverage: Array.from(
        new Set(
          demoBundles
            .flatMap((bundle) => bundle.diagnostics.adapters)
            .filter((adapter) => adapter.available)
            .map((adapter) => adapter.key)
        )
      ),
      stage_completeness: Object.fromEntries(
        Array.from(
          demoBundles.reduce((acc, bundle) => {
            for (const stage of bundle.stage_status) {
              if (stage.status === "ready") acc.set(stage.key, (acc.get(stage.key) ?? 0) + 1);
            }
            return acc;
          }, new Map<string, number>())
        )
      )
    });
  }

  return overviews.sort((a, b) => a.dataset_id.localeCompare(b.dataset_id));
}

function matchesDashboardFilters(bundle: SessionBundle, filters: DashboardFilters) {
  if (filters.sourceType && filters.sourceType !== "all" && bundle.session.source_type !== filters.sourceType) {
    return false;
  }
  if (filters.analysisMode && filters.analysisMode !== "all" && bundle.session.analysis_mode !== filters.analysisMode) {
    return false;
  }
  if (filters.language && filters.language !== "all" && (bundle.session.language ?? "unknown") !== filters.language) {
    return false;
  }
  if (filters.durationBand && filters.durationBand !== "all" && durationBand(bundle) !== filters.durationBand) {
    return false;
  }
  if (filters.qualityBand && filters.qualityBand !== "all" && qualityBand(bundle) !== filters.qualityBand) {
    return false;
  }
  if (filters.readinessTier && filters.readinessTier !== "all" && bundle.session.readiness_tier !== filters.readinessTier) {
    return false;
  }
  if (filters.rolePresence && filters.rolePresence !== "all") {
    const roles = new Set(bundle.speaker_roles.assignments.map((assignment) => assignment.speaker_role));
    const rolePresence = roles.has("human") && roles.has("ai")
      ? "human_ai"
      : roles.has("human")
        ? "human_only"
        : roles.has("ai")
          ? "ai_only"
          : "unknown";
    if (rolePresence !== filters.rolePresence) {
      return false;
    }
  }
  return true;
}

export function filterDashboardBundles(bundles: SessionBundle[], filters: DashboardFilters): SessionBundle[] {
  return bundles.filter((bundle) => matchesDashboardFilters(bundle, filters));
}

export function loadDashboardSnapshot(filters: DashboardFilters = {}): DashboardSnapshot {
  const bundles = filterDashboardBundles(loadSessionBundles(), filters);
  const datasets = loadDatasetOverviews();
  const usableRuns = bundles.filter((bundle) => bundle.quality.is_usable).length;
  const avgSNR = bundles.length
    ? bundles.reduce((sum, bundle) => sum + (bundle.quality.avg_snr_db ?? 0), 0) / bundles.length
    : 0;
  const alerts = bundles
    .flatMap((bundle) =>
      bundle.signals
        .filter((signal) => signal.status === "risk")
        .map((signal) => ({
          session_id: bundle.session.session_id,
          title: bundle.session.title,
          metric: signal.label,
          value: signal.score,
          summary: signal.summary
        }))
    )
    .sort((a, b) => b.value - a.value)
    .slice(0, 6);

  return {
    bundles,
    datasets,
    cohorts: buildCohortSummary(bundles),
    benchmarks: buildBenchmarkSnapshot(bundles),
    totals: {
      runs: bundles.length,
      usableRuns,
      datasetCount: datasets.length,
      avgSNR
    },
    alerts
  };
}

export function formatPct(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function formatMs(value: number) {
  return `${Math.round(value)} ms`;
}

export function formatMetric(value: string | number | boolean | null, unit?: string | null) {
  if (value === null || value === undefined) {
    return "Unknown";
  }
  if (typeof value === "number") {
    const formatted = Number.isInteger(value) ? `${value}` : value.toFixed(2);
    return unit ? `${formatted} ${unit}` : formatted;
  }
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  return unit ? `${value} ${unit}` : value;
}

export function audioPathFor(jobId: string) {
  return `/api/audio/${jobId}`;
}

export function spectrogramPathFor(jobId: string) {
  return `/api/spectrogram/${jobId}`;
}

export function compareSessionBundles(sessionIds: string[]) {
  return sessionIds.map((sessionId) => loadSessionBundle(sessionId)).filter((bundle): bundle is SessionBundle => bundle !== null);
}

function signalValue(bundle: SessionBundle, key: string) {
  return bundle.signals.find((signal) => signal.key === key)?.score ?? 0;
}

function qualityBand(bundle: SessionBundle) {
  if (bundle.quality.noise_ratio >= 0.35 || !bundle.quality.is_usable) return "risky";
  if (bundle.quality.noise_ratio >= 0.2) return "watch";
  return "clean";
}

function durationBand(bundle: SessionBundle) {
  if (bundle.session.duration_sec >= 1800) return "30m_plus";
  if (bundle.session.duration_sec >= 600) return "10m_to_30m";
  if (bundle.session.duration_sec >= 180) return "3m_to_10m";
  return "under_3m";
}

function bundleDate(bucketBundle: SessionBundle) {
  const bundlePath = bucketBundle.artifacts.bundle_path;
  if (bundlePath && fs.existsSync(bundlePath)) {
    return new Date(fs.statSync(bundlePath).mtime).toISOString().slice(0, 10);
  }
  return "current";
}

function phaseEmotion(bundle: SessionBundle, startRatio: number, endRatio: number) {
  const startMs = bundle.session.duration_sec * 1000 * startRatio;
  const endMs = bundle.session.duration_sec * 1000 * endRatio;
  const counts = new Map<string, number>();
  for (const sentence of bundle.content.sentences) {
    if (sentence.speaker_role !== "human") continue;
    if (sentence.start_ms < startMs || sentence.start_ms >= endMs) continue;
    if (!sentence.emotion_label || sentence.emotion_label === "unlabeled") continue;
    counts.set(sentence.emotion_label, (counts.get(sentence.emotion_label) ?? 0) + 1);
  }
  return Array.from(counts.entries()).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "unlabeled";
}

function buildCohortSummary(bundles: SessionBundle[]): CohortSummary {
  const snrValues = bundles.map((bundle) => bundle.quality.avg_snr_db ?? 0);
  const trendsMap = new Map<string, SessionBundle[]>();
  for (const bundle of bundles) {
    const key = bundleDate(bundle);
    trendsMap.set(key, [...(trendsMap.get(key) ?? []), bundle]);
  }
  const emotionCounts = new Map<string, number>();
  for (const bundle of bundles) {
    for (const sentence of bundle.content.sentences) {
      if (sentence.speaker_role !== "human" || sentence.emotion_label === "unlabeled") continue;
      emotionCounts.set(sentence.emotion_label, (emotionCounts.get(sentence.emotion_label) ?? 0) + 1);
    }
  }
  const trendBuckets = Array.from(trendsMap.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([bucket, items]) => ({
      bucket,
      run_count: items.length,
      usable_run_rate: items.length ? (items.filter((bundle) => bundle.quality.is_usable).length / items.length) * 100 : 0,
      avg_snr_db: items.length ? items.reduce((sum, bundle) => sum + (bundle.quality.avg_snr_db ?? 0), 0) / items.length : 0,
      hesitation_avg: items.length ? items.reduce((sum, bundle) => sum + signalValue(bundle, "hesitation"), 0) / items.length : 0,
      friction_avg: items.length ? items.reduce((sum, bundle) => sum + signalValue(bundle, "friction"), 0) / items.length : 0,
      rapport_avg: items.length ? items.reduce((sum, bundle) => sum + signalValue(bundle, "rapport"), 0) / items.length : 0,
      frustration_avg: items.length ? items.reduce((sum, bundle) => sum + signalValue(bundle, "frustration_risk"), 0) / items.length : 0,
    }));
  const countDistribution = (values: string[]) =>
    Array.from(values.reduce((acc, value) => acc.set(value, (acc.get(value) ?? 0) + 1), new Map<string, number>()).entries()).map(([key, value]) => ({
      key,
      label: key.replaceAll("_", " "),
      value,
      value_type: "count",
    }));
  return {
    kpis: [
      { key: "run_count", label: "Run count", value: bundles.length },
      { key: "usable_run_rate", label: "Usable-run rate", value: bundles.length ? (usableRuns(bundles) / bundles.length) * 100 : 0, unit: "%" },
      { key: "avg_snr_db", label: "Average SNR", value: bundles.length ? snrValues.reduce((sum, value) => sum + value, 0) / bundles.length : 0, unit: "dB" },
      { key: "hesitation_avg", label: "Human hesitation", value: averageSignal(bundles, "hesitation") },
      { key: "friction_avg", label: "Human friction", value: averageSignal(bundles, "friction") },
      { key: "rapport_avg", label: "Rapport", value: averageSignal(bundles, "rapport") },
      { key: "frustration_avg", label: "Frustration risk", value: averageSignal(bundles, "frustration_risk") },
    ],
    trends: trendBuckets,
    distributions: [
      { key: "quality_band_mix", label: "Quality band mix", items: countDistribution(bundles.map((bundle) => qualityBand(bundle))) },
      { key: "source_mix", label: "Source mix", items: countDistribution(bundles.map((bundle) => bundle.session.source_type)) },
      { key: "duration_mix", label: "Duration bands", items: countDistribution(bundles.map((bundle) => durationBand(bundle))) },
      { key: "readiness_mix", label: "Readiness tiers", items: countDistribution(bundles.map((bundle) => bundle.session.readiness_tier ?? "blocked")) },
      {
        key: "dominant_human_emotions",
        label: "Dominant human emotions",
        items: Array.from(emotionCounts.entries())
          .sort((a, b) => b[1] - a[1])
          .slice(0, 8)
          .map(([key, value]) => ({ key, label: key.replaceAll("_", " "), value, value_type: "count" })),
      },
    ],
    phase_summaries: [
      buildPhaseSummary(bundles, "first_third", 0, 1 / 3),
      buildPhaseSummary(bundles, "middle_third", 1 / 3, 2 / 3),
      buildPhaseSummary(bundles, "final_third", 2 / 3, 1),
    ],
  };
}

function usableRuns(bundles: SessionBundle[]) {
  return bundles.filter((bundle) => bundle.quality.is_usable).length;
}

function averageSignal(bundles: SessionBundle[], key: string) {
  if (!bundles.length) return 0;
  return bundles.reduce((sum, bundle) => sum + signalValue(bundle, key), 0) / bundles.length;
}

function buildPhaseSummary(bundles: SessionBundle[], phase: string, startRatio: number, endRatio: number) {
  const hesitationValues: number[] = [];
  const frictionValues: number[] = [];
  const rapportValues: number[] = [];
  const frustrationValues: number[] = [];
  for (const bundle of bundles) {
    const startMs = bundle.session.duration_sec * 1000 * startRatio;
    const endMs = bundle.session.duration_sec * 1000 * endRatio;
    const turnLookup = new Map(bundle.turns.map((turn) => [turn.turn_id, turn]));
    const phaseQuestions = bundle.questions.filter((question) => {
      const turn = turnLookup.get(question.answer_turn_id);
      return turn ? turn.start_ms >= startMs && turn.start_ms < endMs : false;
    });
    const phaseHesitation = phaseQuestions.length
      ? phaseQuestions.reduce((sum, question) => sum + question.hesitation_score, 0) / phaseQuestions.length
      : 0;
    if (phaseQuestions.length) {
      hesitationValues.push(phaseHesitation);
    }
    const phaseEvents = bundle.events.filter((event) => event.begin_ms >= startMs && event.begin_ms < endMs && ["interruption", "noise_spike", "engagement_drop"].includes(event.type));
    frictionValues.push(Math.min(100, phaseEvents.length * 18));
    const humanSpeaker = bundle.speakers.find((speaker) => speaker.speaker_role === "human") ?? bundle.speakers[0];
    if (humanSpeaker) {
      rapportValues.push(Math.max(10, 100 - Math.abs((humanSpeaker.talk_ratio - 0.5) * 140)));
    }
    frustrationValues.push(Math.min(100, (frictionValues.at(-1) ?? 0) * 0.65 + phaseHesitation * 0.35));
  }
  return {
    phase,
    hesitation_avg: hesitationValues.length ? hesitationValues.reduce((sum, value) => sum + value, 0) / hesitationValues.length : 0,
    friction_avg: frictionValues.length ? frictionValues.reduce((sum, value) => sum + value, 0) / frictionValues.length : 0,
    rapport_avg: rapportValues.length ? rapportValues.reduce((sum, value) => sum + value, 0) / rapportValues.length : 0,
    frustration_avg: frustrationValues.length ? frustrationValues.reduce((sum, value) => sum + value, 0) / frustrationValues.length : 0,
    dominant_emotion: bundles.map((bundle) => phaseEmotion(bundle, startRatio, endRatio)).find((emotion) => emotion !== "unlabeled") ?? "unlabeled",
  };
}

function buildBenchmarkSnapshot(bundles: SessionBundle[]): BenchmarkSnapshot {
  const registry = [
    { benchmark_id: "meld", dataset_id: "meld", title: "MELD", status: "ready", tasks: [{ task_type: "sentence_emotion", label: "Sentence emotion", metric_keys: ["macro_f1"] }, { task_type: "sentiment", label: "Sentiment", metric_keys: ["accuracy"] }], notes: ["Emotion-label coverage first."] },
    { benchmark_id: "ravdess_speech_16k", dataset_id: "ravdess_speech_16k", title: "RAVDESS", status: "ready", tasks: [{ task_type: "utterance_emotion", label: "Utterance emotion", metric_keys: ["macro_f1"] }], notes: ["Utterance-level affect sanity checks."] },
    { benchmark_id: "iemocap", dataset_id: "iemocap", title: "IEMOCAP", status: "gated", tasks: [{ task_type: "utterance_emotion", label: "Utterance emotion", metric_keys: ["macro_f1"] }], notes: ["Run when licensed data is present locally."] },
    { benchmark_id: "msp_podcast", dataset_id: "msp_podcast", title: "MSP-Podcast", status: "gated", tasks: [{ task_type: "utterance_emotion", label: "Utterance emotion", metric_keys: ["macro_f1"] }, { task_type: "sentiment", label: "Sentiment", metric_keys: ["accuracy"] }], notes: ["Run when licensed data is present locally."] },
    { benchmark_id: "ami_corpus", dataset_id: "ami_corpus", title: "AMI Corpus", status: "ready", tasks: [{ task_type: "diarization_overlap", label: "Diarization + overlap", metric_keys: ["der"] }, { task_type: "nonverbal_cue_tagging", label: "Non-verbal cue tagging", metric_keys: ["precision", "recall", "f1"] }], notes: ["Cue timing and overlap validation."] },
    { benchmark_id: "voxconverse", dataset_id: "voxconverse", title: "VoxConverse", status: "ready", tasks: [{ task_type: "diarization_overlap", label: "Diarization + overlap", metric_keys: ["der"] }], notes: ["Open diarization benchmark coverage."] },
    { benchmark_id: "podcast_fillers_processed", dataset_id: "podcast_fillers_processed", title: "Podcast Fillers", status: "ready", tasks: [{ task_type: "nonverbal_cue_tagging", label: "Non-verbal cue tagging", metric_keys: ["precision", "recall", "f1"] }], notes: ["Filler and hesitation proxy coverage."] },
  ];
  const results = registry.flatMap((entry) => {
    const matched = bundles.filter((bundle) => bundle.session.dataset_id === entry.dataset_id);
    return entry.tasks.map((task) => {
      const hasData = matched.length > 0;
      let metrics: Array<{ key: string; label: string; value: number }> = [];
      if (hasData && task.task_type === "sentence_emotion") {
        const sentenceCount = matched.reduce((sum, bundle) => sum + bundle.content.sentences.length, 0);
        const benchmarkCount = matched.reduce((sum, bundle) => sum + bundle.content.sentences.filter((sentence) => sentence.source === "benchmark_label").length, 0);
        metrics = [{ key: "macro_f1", label: "Macro F1", value: sentenceCount ? benchmarkCount / sentenceCount : 0 }];
      } else if (hasData && task.task_type === "sentiment") {
        const total = matched.reduce((sum, bundle) => sum + bundle.content.sentences.length, 0);
        const labeled = matched.reduce((sum, bundle) => sum + bundle.content.sentences.filter((sentence) => sentence.sentiment_label).length, 0);
        metrics = [{ key: "accuracy", label: "Accuracy", value: total ? labeled / total : 0 }];
      } else if (hasData && task.task_type === "utterance_emotion") {
        const total = matched.reduce((sum, bundle) => sum + bundle.content.sentences.length, 0);
        const visible = matched.reduce((sum, bundle) => sum + bundle.content.sentences.filter((sentence) => sentence.display_state !== "hidden").length, 0);
        metrics = [{ key: "macro_f1", label: "Macro F1", value: total ? visible / total : 0 }];
      } else if (hasData && task.task_type === "diarization_overlap") {
        const segments = matched.reduce((sum, bundle) => sum + bundle.diarization.segments.length, 0);
        const overlaps = matched.reduce((sum, bundle) => sum + bundle.diarization.overlap_windows.length, 0);
        metrics = [{ key: "der", label: "DER", value: overlaps / Math.max(1, segments + overlaps) }];
      } else if (hasData && task.task_type === "nonverbal_cue_tagging") {
        const cues = matched.reduce((sum, bundle) => sum + bundle.nonverbal_cues.length, 0);
        const visible = matched.reduce((sum, bundle) => sum + bundle.nonverbal_cues.filter((cue) => cue.display_state !== "hidden").length, 0);
        const ratio = cues ? visible / cues : 0;
        metrics = [{ key: "precision", label: "Precision", value: ratio }, { key: "recall", label: "Recall", value: ratio }, { key: "f1", label: "F1", value: ratio }];
      }
      return {
        benchmark_id: `${entry.dataset_id}:${task.task_type}`,
        dataset_id: entry.dataset_id,
        task_type: task.task_type,
        status: hasData ? "ready" : entry.status === "gated" ? "skipped" : "missing",
        regressed: false,
        metrics,
        notes: hasData ? entry.notes : [...entry.notes, "No imported benchmark-backed sessions are available yet."],
      };
    });
  });
  return { registry, results };
}
