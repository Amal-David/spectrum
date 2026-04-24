import type { CohortDistribution, CohortSessionRow, CohortSummaryResponse, CohortTrendPoint } from "./api-client";
import { fetchCohortDistributions, fetchCohortSessions, fetchCohortSummary, fetchCohortTrends } from "./api-client";
import type { DashboardFilters } from "./data";

type QueryValue = string | string[] | undefined;

function filtersToQuery(filters: DashboardFilters): Record<string, QueryValue> {
  return {
    source_types: filters.sourceType,
    analysis_modes: filters.analysisMode,
    languages: filters.language,
    duration_band: filters.durationBand,
    quality_band: filters.qualityBand,
    readiness_tiers: filters.readinessTier,
    role_presence: filters.rolePresence,
  };
}

export async function loadCohortSummary(filters: DashboardFilters): Promise<CohortSummaryResponse> {
  return fetchCohortSummary(filtersToQuery(filters));
}

export async function loadCohortTrends(filters: DashboardFilters): Promise<CohortTrendPoint[]> {
  return fetchCohortTrends(filtersToQuery(filters));
}

export async function loadCohortDistributions(filters: DashboardFilters): Promise<CohortDistribution[]> {
  return fetchCohortDistributions(filtersToQuery(filters));
}

export async function loadCohortSessions(filters: DashboardFilters): Promise<CohortSessionRow[]> {
  return fetchCohortSessions(filtersToQuery(filters));
}
