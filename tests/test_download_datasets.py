from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "download_datasets.py"
SPEC = importlib.util.spec_from_file_location("download_datasets", SCRIPT_PATH)
assert SPEC and SPEC.loader
download_datasets = importlib.util.module_from_spec(SPEC)
sys.modules.setdefault(
    "huggingface_hub",
    types.SimpleNamespace(
        hf_hub_url=lambda *args, **kwargs: "",
        list_repo_files=lambda *args, **kwargs: [],
    ),
)
sys.modules.setdefault("download_datasets", download_datasets)
SPEC.loader.exec_module(download_datasets)


@pytest.mark.skipif(importlib.util.find_spec("pyarrow") is None, reason="pyarrow is not installed")
def test_materialize_dataset_parquet_audio_writes_local_media(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    repo_root = tmp_path
    raw_root = repo_root / "data" / "raw"
    inventory_root = repo_root / "data" / "cache" / "inventory"
    dataset_root = raw_root / "sample_dataset"
    dataset_root.mkdir(parents=True)
    inventory_root.mkdir(parents=True)

    parquet_path = dataset_root / "clips.parquet"
    audio_bytes = (
        b"RIFF$\x00\x00\x00WAVEfmt "
        b"\x10\x00\x00\x00\x01\x00\x01\x00@\x1f\x00\x00\x80>\x00\x00\x02\x00\x10\x00"
        b"data\x00\x00\x00\x00"
    )
    table = pa.table(
        {
            "audio": [{"bytes": audio_bytes, "path": "example.wav"}],
            "language": ["en"],
            "speaker_id": ["speaker-1"],
        }
    )
    pq.write_table(table, parquet_path)

    monkeypatch.setattr(download_datasets, "ROOT", repo_root)
    monkeypatch.setattr(download_datasets, "RAW_ROOT", raw_root)
    monkeypatch.setattr(download_datasets, "INVENTORY_ROOT", inventory_root)

    dataset = {
        "id": "sample_dataset",
        "title": "Sample Dataset",
        "target_dir": "data/raw/sample_dataset",
        "source_url": "https://example.com/sample",
        "access_type": "open",
        "verification_rules": {},
    }

    summary = download_datasets.materialize_dataset_parquet_audio(dataset, batch_size=8)

    assert summary["parquet_files"] == 1
    assert summary["rows_seen"] == 1
    assert summary["files_written"] == 1

    output_file = dataset_root / download_datasets.PARQUET_MEDIA_DIRNAME / "clips" / "000000-example.wav"
    assert output_file.exists()
    assert output_file.read_bytes() == audio_bytes

    manifest_path = inventory_root / "sample_dataset.materialized_audio.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text())
    assert manifest["dataset_id"] == "sample_dataset"
    assert manifest["files"][0]["records"][0]["output_path"] == "data/raw/sample_dataset/materialized_audio/clips/000000-example.wav"
