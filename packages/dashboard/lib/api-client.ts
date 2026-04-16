import { backendUrl } from "./backend";
import { mapSessionBundle } from "./bundle-mappers";
import type { DatasetOverview, SessionBundle } from "./data";

export type SessionIndexRow = {
  session_id: string;
  title: string;
  analysis_mode: SessionBundle["session"]["analysis_mode"];
  source_type: string;
  dataset_id?: string | null;
  language?: string | null;
  duration_sec: number;
  usable: boolean;
  quality: {
    avg_snr_db: number | null;
    noise_ratio: number;
    is_usable?: boolean;
  };
  top_signal_keys: string[];
};

export type CohortTrendPoint = {
  bucket: string;
  run_count: number;
  usable_run_rate: number;
  avg_snr_db: number;
  hesitation_avg: number;
  friction_avg: number;
  rapport_avg: number;
  frustration_avg: number;
};

export type CohortDistribution = {
  key: string;
  label: string;
  items: Array<{
    key: string;
    label: string;
    value: number;
    value_type: string;
  }>;
};

export type CohortSessionRow = {
  session_id: string;
  title: string;
  source_type: string;
  dataset_id?: string | null;
  analysis_mode: SessionBundle["session"]["analysis_mode"];
  language?: string | null;
  duration_sec: number;
  readiness_tier: NonNullable<SessionBundle["session"]["readiness_tier"]>;
  usable: boolean;
  quality_band: string;
  human_present: boolean;
  ai_present: boolean;
  top_signal?: string | null;
};

export type CohortSummaryResponse = {
  kpis: Array<{ key: string; label: string; value: number; unit?: string | null }>;
  phase_summaries: Array<{
    phase: string;
    hesitation_avg: number;
    friction_avg: number;
    rapport_avg: number;
    frustration_avg: number;
    dominant_emotion: string;
  }>;
  dominant_emotions: Array<{ key: string; label: string; value: number; value_type: string }>;
  runs: CohortSessionRow[];
};

export type BenchmarkSnapshot = {
  registry: Array<{
    benchmark_id: string;
    dataset_id: string;
    title: string;
    status: string;
    tasks: Array<{ task_type: string; label: string; metric_keys: string[] }>;
    notes: string[];
  }>;
  results: Array<{
    benchmark_id: string;
    dataset_id: string;
    task_type: string;
    status: string;
    regressed?: boolean;
    support_level?: SessionBundle["signals"][number]["evidence_class"];
    metrics: Array<{
      key: string;
      label: string;
      value: number;
      unit?: string | null;
      previous_value?: number | null;
      delta?: number | null;
      regressed?: boolean;
    }>;
    notes: string[];
  }>;
};

type QueryValue = string | string[] | undefined;

function buildUrl(pathname: string, query?: Record<string, QueryValue>) {
  const url = new URL(backendUrl(pathname));
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value === undefined || value === "all" || value === "") {
      continue;
    }
    if (Array.isArray(value)) {
      for (const item of value) {
        if (item) url.searchParams.append(key, item);
      }
      continue;
    }
    url.searchParams.set(key, value);
  }
  return url.toString();
}

async function apiFetch<T>(pathname: string, query?: Record<string, QueryValue>): Promise<T> {
  const response = await fetch(buildUrl(pathname, query), { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Backend request failed for ${pathname} (${response.status})`);
  }
  return (await response.json()) as T;
}

export async function fetchSessionIndex(): Promise<SessionIndexRow[]> {
  return apiFetch<SessionIndexRow[]>("/api/v1/sessions");
}

export async function fetchSessionBundle(jobId: string): Promise<SessionBundle | null> {
  const response = await fetch(buildUrl(`/api/v1/sessions/${jobId}/bundle`), { cache: "no-store" });
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Backend request failed for session ${jobId} (${response.status})`);
  }
  return mapSessionBundle(await response.json());
}

export async function fetchSessionBundles(jobIds: string[]): Promise<SessionBundle[]> {
  const bundles = await Promise.all(jobIds.map((jobId) => fetchSessionBundle(jobId)));
  return bundles.filter((bundle): bundle is SessionBundle => bundle !== null);
}

export async function fetchDatasets(): Promise<DatasetOverview[]> {
  return apiFetch<DatasetOverview[]>("/api/v1/datasets");
}

export async function fetchCohortSummary(query?: Record<string, QueryValue>): Promise<CohortSummaryResponse> {
  return apiFetch<CohortSummaryResponse>("/api/v1/cohorts/summary", query);
}

export async function fetchCohortTrends(query?: Record<string, QueryValue>): Promise<CohortTrendPoint[]> {
  return apiFetch<CohortTrendPoint[]>("/api/v1/cohorts/trends", query);
}

export async function fetchCohortDistributions(query?: Record<string, QueryValue>): Promise<CohortDistribution[]> {
  return apiFetch<CohortDistribution[]>("/api/v1/cohorts/distributions", query);
}

export async function fetchCohortSessions(query?: Record<string, QueryValue>): Promise<CohortSessionRow[]> {
  return apiFetch<CohortSessionRow[]>("/api/v1/cohorts/sessions", query);
}

export async function fetchBenchmarks(): Promise<BenchmarkSnapshot> {
  return apiFetch<BenchmarkSnapshot>("/api/v1/benchmarks");
}
