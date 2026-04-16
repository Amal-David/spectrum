from __future__ import annotations

import json
from pathlib import Path

from spectrum_pipeline.benchmarks import benchmark_registry, benchmark_results
from spectrum_pipeline.store import list_saved_bundles


def main() -> None:
    bundles = list_saved_bundles()
    payload = {
        "registry": [entry.model_dump(mode="json") for entry in benchmark_registry()],
        "results": [result.model_dump(mode="json") for result in benchmark_results(bundles)],
    }
    output_path = Path("runs") / "benchmark_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
