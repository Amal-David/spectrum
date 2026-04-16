import { buildAnalysisScope, callGroups, calls } from "@/lib/mock-data";
import type { AnalysisScope } from "@/lib/types";

type SearchValue = string | string[] | undefined;

function normalizeQueryValue(value: SearchValue) {
  if (Array.isArray(value)) {
    return value[0];
  }

  return value;
}

export function parseCallIdsFromSearchParams(
  searchParams: Record<string, SearchValue>
) {
  const directIds = normalizeQueryValue(searchParams.calls);

  if (directIds) {
    return directIds
      .split(",")
      .map((item) => item.trim())
      .filter((item) => calls.some((call) => call.id === item));
  }

  const groupId = normalizeQueryValue(searchParams.groupId);

  if (groupId) {
    const group = callGroups.find((item) => item.id === groupId);

    return group ? group.callIds : [];
  }

  const singleCallId = normalizeQueryValue(searchParams.callId);

  if (singleCallId && calls.some((call) => call.id === singleCallId)) {
    return [singleCallId];
  }

  return [calls[0].id];
}

export function parseAnalysisScope(
  searchParams: Record<string, SearchValue>
): AnalysisScope {
  const callIds = parseCallIdsFromSearchParams(searchParams);

  return buildAnalysisScope(callIds);
}

export function buildAnalysisHref(callIds: string[]) {
  const params = new URLSearchParams();

  if (callIds.length === 1) {
    params.set("callId", callIds[0]);
  } else if (callIds.length > 1) {
    params.set("calls", callIds.join(","));
  }

  return `/analysis?${params.toString()}`;
}
