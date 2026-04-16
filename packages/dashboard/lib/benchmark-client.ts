import type { BenchmarkSnapshot } from "./api-client";
import { fetchBenchmarks } from "./api-client";

export async function loadBenchmarkSnapshot(): Promise<BenchmarkSnapshot> {
  return fetchBenchmarks();
}
