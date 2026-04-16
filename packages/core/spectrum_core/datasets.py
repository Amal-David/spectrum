from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .constants import DATA_DIR, FIXTURES_DIR, REPO_ROOT


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def load_dataset_manifest() -> dict[str, Any]:
    return _read_json(DATA_DIR / "manifests" / "datasets.json")


def load_inventory(dataset_id: str) -> dict[str, Any]:
    inventory_path = DATA_DIR / "cache" / "inventory" / f"{dataset_id}.materialized_audio.json"
    if inventory_path.exists():
        return _read_json(inventory_path)
    inventory_path = DATA_DIR / "cache" / "inventory" / f"{dataset_id}.json"
    if inventory_path.exists():
        return _read_json(inventory_path)
    return {}


def _inventory_languages(inventory: dict[str, Any]) -> list[str]:
    counts: Counter[str] = Counter()
    for file_record in inventory.get("files", []):
        for record in file_record.get("records", []):
            language = str(record.get("language") or "").strip().lower()
            if language:
                counts[language] += 1
    return [language for language, _count in counts.most_common(6)]


def _inventory_sample_count(inventory: dict[str, Any]) -> int:
    if inventory.get("file_count"):
        return int(inventory.get("file_count", 0))
    return sum(int(file_record.get("materialized_count", 0)) for file_record in inventory.get("files", []))


def _health_status(inventory: dict[str, Any]) -> tuple[str, str | None]:
    if not inventory:
        return "manifest_only", None
    if error := inventory.get("error"):
        return "ingestion_blocked", str(error)
    if inventory.get("files"):
        return "ready", None
    status = str(inventory.get("status", "manifest_only"))
    return status, None


def list_dataset_records() -> list[dict[str, Any]]:
    manifest = load_dataset_manifest()
    records: list[dict[str, Any]] = []
    for dataset in manifest.get("datasets", []):
        inventory = load_inventory(dataset["id"])
        status, health_detail = _health_status(inventory)
        sample_audio = inventory.get("sample_audio_probe") or {}
        records.append(
            {
                "id": dataset["id"],
                "title": dataset["title"],
                "access_type": dataset.get("access_type"),
                "license": dataset.get("license"),
                "modalities": dataset.get("modalities", []),
                "pipeline_coverage": dataset.get("pipeline_coverage", []),
                "target_dir": dataset.get("target_dir"),
                "status": inventory.get("status", status),
                "health_status": status,
                "health_detail": health_detail,
                "file_count": inventory.get("file_count", 0),
                "sample_count": _inventory_sample_count(inventory),
                "language_labels": _inventory_languages(inventory),
                "total_bytes": inventory.get("total_bytes", 0),
                "has_transcripts": inventory.get("has_transcripts"),
                "has_labels": inventory.get("has_labels"),
                "sample_audio_path": sample_audio.get("path"),
                "sample_duration_sec": sample_audio.get("duration_sec"),
                "inventory": inventory,
            }
        )

    return records


def list_materialized_records(dataset_id: str) -> list[dict[str, Any]]:
    inventory = load_inventory(dataset_id)
    output: list[dict[str, Any]] = []
    for file_record in inventory.get("files", []):
        for record in file_record.get("records", []):
            candidate = {**record}
            output_path = record.get("output_path")
            if output_path:
                candidate["absolute_output_path"] = str((REPO_ROOT / output_path).resolve())
            output.append(candidate)
    return output


def load_demo_manifest() -> list[dict[str, Any]]:
    manifest = _read_json(FIXTURES_DIR / "demo_samples" / "manifest.json")
    samples = manifest.get("samples", [])
    for sample in samples:
        if source_path := sample.get("source_path"):
            sample["absolute_source_path"] = str((REPO_ROOT / source_path).resolve())
        if fixture_path := sample.get("fixture_path"):
            sample["absolute_fixture_path"] = str((REPO_ROOT / fixture_path).resolve())
    return samples
