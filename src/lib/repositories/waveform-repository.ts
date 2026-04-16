import { buildAnalysisDataset } from "@/lib/mock-data";
import type { AnalysisScope } from "@/lib/types";

export const waveformRepository = {
  getTracks(scope: AnalysisScope) {
    return buildAnalysisDataset(scope).waveformTracks;
  },
};
