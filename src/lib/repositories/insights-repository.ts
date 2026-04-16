import { buildAnalysisDataset } from "@/lib/mock-data";
import type { AnalysisScope } from "@/lib/types";

export const insightsRepository = {
  getQuestionInsights(scope: AnalysisScope) {
    return buildAnalysisDataset(scope).questionInsights;
  },
  getEvidence(scope: AnalysisScope) {
    return buildAnalysisDataset(scope).evidenceRefs;
  },
};
