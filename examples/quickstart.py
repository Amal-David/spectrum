from __future__ import annotations

from pathlib import Path

import httpx


API_BASE = "http://127.0.0.1:8000"
SAMPLE_PATH = Path(__file__).with_name("sample.wav")


def main() -> None:
    if not SAMPLE_PATH.exists():
        raise SystemExit(f"Sample audio not found at {SAMPLE_PATH}")

    with httpx.Client(base_url=API_BASE, timeout=120.0) as client:
        created = client.post("/api/v1/sessions", json={"analysis_mode": "full", "metadata": {"title": "Quickstart sample"}})
        created.raise_for_status()
        job_id = created.json()["job_id"]

        with SAMPLE_PATH.open("rb") as handle:
            uploaded = client.post(
                f"/api/v1/sessions/{job_id}/upload",
                files={"file": (SAMPLE_PATH.name, handle, "audio/wav")},
            )
            uploaded.raise_for_status()

        processed = client.post(f"/api/v1/sessions/{job_id}/process", json={"metadata": {}})
        processed.raise_for_status()

        bundle = client.get(f"/api/v1/sessions/{job_id}/bundle")
        bundle.raise_for_status()

    print(f"Created session: {job_id}")
    print(f"Dashboard: http://127.0.0.1:3000/sessions/{job_id}")
    print(f"Bundle endpoint: {API_BASE}/api/v1/sessions/{job_id}/bundle")


if __name__ == "__main__":
    main()
