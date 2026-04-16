import { buildAnalysisDataset } from "@/lib/mock-data";
import type { AnalysisScope } from "@/lib/types";

export const analysisRepository = {
  getByScope(scope: AnalysisScope) {
    return buildAnalysisDataset(scope);
  },
};
