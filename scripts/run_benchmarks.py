from __future__ import annotations

import argparse
import json
from pathlib import Path

from spectrum_core.models import BenchmarkResult
from spectrum_pipeline.benchmarks import (
    benchmark_snapshot_payload,
    load_benchmark_snapshot,
    save_benchmark_snapshot,
)
from spectrum_pipeline.store import list_saved_bundles


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Spectrum benchmark snapshots against saved bundles.")
    parser.add_argument("--fail-on-regression", action="store_true", help="Exit non-zero when any metric regresses against the previous snapshot.")
    args = parser.parse_args()

    bundles = list_saved_bundles()
    previous_snapshot = load_benchmark_snapshot()
    previous_results = (
        [BenchmarkResult.model_validate(item) for item in previous_snapshot.get("results", [])]
        if isinstance(previous_snapshot, dict)
        else None
    )
    payload = benchmark_snapshot_payload(bundles, previous_results=previous_results)
    output_path = Path("runs") / "benchmark_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2) + "\n"
    output_path.write_text(encoded)
    versioned_path, latest_path = save_benchmark_snapshot(payload)
    if args.fail_on_regression:
        regressed = any(
            result.get("regressed")
            for result in payload.get("results", [])
            if isinstance(result, dict)
        )
        if regressed:
            print(encoded)
            raise SystemExit("Benchmark regression detected. See runs/benchmarks/latest.json for details.")
    print(f"Saved benchmark snapshot to {versioned_path} and {latest_path}.")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
