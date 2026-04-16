#!/usr/bin/env python3

from __future__ import annotations

import argparse
import concurrent.futures
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

try:
    from huggingface_hub import hf_hub_url, list_repo_files
except ImportError:  # pragma: no cover - optional for local-only commands
    hf_hub_url = None
    list_repo_files = None


ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "data" / "manifests" / "datasets.json"
RAW_ROOT = ROOT / "data" / "raw"
CACHE_ROOT = ROOT / "data" / "cache"
DOWNLOAD_ROOT = CACHE_ROOT / "downloads"
INVENTORY_ROOT = CACHE_ROOT / "inventory"
MEDIA_EXTENSIONS = {".wav", ".mp3", ".m4a", ".mp4", ".flac", ".ogg", ".aac"}
PARQUET_MEDIA_DIRNAME = "materialized_audio"
ARCHIVE_SUFFIXES = (".zip", ".tar", ".tar.gz", ".tgz")
PRINT_LOCK = threading.Lock()


def log(message: str) -> None:
    with PRINT_LOCK:
        print(message, flush=True)


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text())


def ensure_layout() -> None:
    for path in (RAW_ROOT, DOWNLOAD_ROOT, INVENTORY_ROOT):
        path.mkdir(parents=True, exist_ok=True)


def datasets_by_id(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {dataset["id"]: dataset for dataset in manifest["datasets"]}


def resolve_dataset_ids(manifest: dict[str, Any], args: argparse.Namespace) -> list[str]:
    if args.dataset:
        return args.dataset
    if getattr(args, "group", None):
        if args.group not in manifest["groups"]:
            valid_groups = ", ".join(sorted(manifest["groups"]))
            raise SystemExit(f"Unknown dataset group '{args.group}'. Valid groups: {valid_groups}")
        return manifest["groups"][args.group]
    if getattr(args, "all", False):
        return [dataset["id"] for dataset in manifest["datasets"]]
    return manifest["groups"]["wave1_open"]


def dataset_download_dir(dataset_id: str) -> Path:
    return DOWNLOAD_ROOT / dataset_id


def dataset_target_dir(dataset: dict[str, Any]) -> Path:
    return ROOT / dataset["target_dir"]


def inventory_path(dataset_id: str) -> Path:
    return INVENTORY_ROOT / f"{dataset_id}.json"


def parquet_materialization_manifest_path(dataset_id: str) -> Path:
    return INVENTORY_ROOT / f"{dataset_id}.materialized_audio.json"


def run_command(command: list[str]) -> None:
    subprocess.run(command, check=True)


def curl_download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "curl",
        "-L",
        "--fail",
        "--retry",
        "3",
        "--continue-at",
        "-",
        "--output",
        str(destination),
        url,
    ]
    run_command(command)


def snapshot_download_repo(snapshot_config: dict[str, Any], destination_dir: Path) -> None:
    if hf_hub_url is None or list_repo_files is None:
        raise RuntimeError(
            "huggingface_hub is required for snapshot downloads. "
            "Install it before running dataset fetch commands that use Hugging Face snapshots."
        )
    destination_dir.mkdir(parents=True, exist_ok=True)
    repo_id = snapshot_config["repo_id"]
    repo_type = snapshot_config.get("repo_type", "dataset")
    allow_patterns = snapshot_config.get("allow_patterns")
    ignore_patterns = snapshot_config.get("ignore_patterns")
    selected_files: list[str] = []
    for repo_file in sorted(list_repo_files(repo_id=repo_id, repo_type=repo_type)):
        if allow_patterns and not any(fnmatch.fnmatch(repo_file, pattern) for pattern in allow_patterns):
            continue
        if ignore_patterns and any(fnmatch.fnmatch(repo_file, pattern) for pattern in ignore_patterns):
            continue
        selected_files.append(repo_file)
    if not selected_files:
        raise RuntimeError(f"No files matched snapshot filters for {repo_id}")
    for repo_file in selected_files:
        destination = destination_dir / repo_file
        log(f"[hub:{repo_id}] downloading {repo_file}")
        curl_download(hf_hub_url(repo_id, repo_file, repo_type=repo_type), destination)


def md5_for_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksum(path: Path, checksum_md5: str) -> None:
    actual = md5_for_file(path)
    if actual != checksum_md5:
        raise RuntimeError(f"Checksum mismatch for {path.name}: expected {checksum_md5}, got {actual}")


def extraction_marker_path(archive_path: Path) -> Path:
    return archive_path.with_suffix(archive_path.suffix + ".extracted.json")


def extraction_is_current(archive_path: Path) -> bool:
    marker = extraction_marker_path(archive_path)
    if not marker.exists():
        return False
    try:
        payload = json.loads(marker.read_text())
    except json.JSONDecodeError:
        return False
    stat = archive_path.stat()
    return payload.get("size") == stat.st_size and payload.get("mtime") == stat.st_mtime


def mark_extracted(archive_path: Path) -> None:
    stat = archive_path.stat()
    extraction_marker_path(archive_path).write_text(
        json.dumps({"size": stat.st_size, "mtime": stat.st_mtime}, indent=2)
    )


def extract_archive(archive_path: Path, target_dir: Path) -> None:
    if extraction_is_current(archive_path):
        return
    target_dir.mkdir(parents=True, exist_ok=True)
    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(target_dir)
    elif tarfile.is_tarfile(archive_path):
        with tarfile.open(archive_path) as archive:
            archive.extractall(target_dir)
    else:
        raise RuntimeError(f"Unsupported archive format: {archive_path}")
    mark_extracted(archive_path)


def is_archive_path(path: Path) -> bool:
    name = path.name.lower()
    return any(name.endswith(suffix) for suffix in ARCHIVE_SUFFIXES)


def extract_nested_archives(base_dir: Path) -> dict[str, Any]:
    extracted = 0
    errors: list[dict[str, str]] = []
    changed = True
    while changed:
        changed = False
        archive_paths = [path for path in sorted(base_dir.rglob("*")) if path.is_file() and is_archive_path(path)]
        for archive_path in archive_paths:
            if extraction_is_current(archive_path):
                continue
            try:
                extract_archive(archive_path, archive_path.parent)
                extracted += 1
                changed = True
            except Exception as error:
                errors.append(
                    {
                        "archive_path": str(archive_path.relative_to(ROOT)),
                        "error": str(error),
                    }
                )
    return {"archives_extracted": extracted, "errors": errors}


def copy_to_target(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size == source.stat().st_size:
        return
    shutil.copy2(source, target)


def find_matches(base_dir: Path, patterns: list[str]) -> list[Path]:
    matches: list[Path] = []
    if not base_dir.exists():
        return matches
    for path in base_dir.rglob("*"):
        if not path.is_file():
            continue
        relative_path = path.relative_to(base_dir).as_posix()
        for pattern in patterns:
            if fnmatch.fnmatch(relative_path, pattern):
                matches.append(path)
                break
    return matches


def probe_media(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    payload = json.loads(result.stdout or "{}")
    audio_stream = next(
        (stream for stream in payload.get("streams", []) if stream.get("codec_type") == "audio"),
        None,
    )
    format_info = payload.get("format", {})
    return {
        "path": str(path.relative_to(ROOT)),
        "codec_name": audio_stream.get("codec_name") if audio_stream else None,
        "sample_rate": int(audio_stream["sample_rate"]) if audio_stream and audio_stream.get("sample_rate") else None,
        "channels": audio_stream.get("channels") if audio_stream else None,
        "duration_sec": float(format_info["duration"]) if format_info.get("duration") else None,
    }


def probe_huggingface_first_rows(probe_config: dict[str, Any]) -> dict[str, Any]:
    query = urllib.parse.urlencode(
        {
            "dataset": probe_config["dataset"],
            "config": probe_config["config"],
            "split": probe_config["split"],
        }
    )
    with urllib.request.urlopen(
        f"https://datasets-server.huggingface.co/first-rows?{query}",
        timeout=30,
    ) as response:
        payload = json.load(response)
    first_row = payload["rows"][0]["row"]
    audio_field = probe_config.get("audio_field", "audio")
    audio_value = first_row.get(audio_field)
    media_src = None
    media_type = None
    if isinstance(audio_value, list) and audio_value and isinstance(audio_value[0], dict):
        media_src = audio_value[0].get("src")
        media_type = audio_value[0].get("type")
    elif isinstance(audio_value, dict):
        media_src = audio_value.get("src")
        media_type = audio_value.get("type")
    start_field = probe_config.get("start_field")
    end_field = probe_config.get("end_field")
    duration_sec = None
    if start_field and end_field:
        start = first_row.get(start_field)
        end = first_row.get(end_field)
        if isinstance(start, (int, float)) and isinstance(end, (int, float)):
            duration_sec = end - start
    return {
        "path": media_src or f"hf://datasets/{probe_config['dataset']}/{probe_config['config']}/{probe_config['split']}",
        "codec_name": media_type.split("/", 1)[1] if isinstance(media_type, str) and "/" in media_type else media_type,
        "sample_rate": probe_config.get("sample_rate"),
        "channels": probe_config.get("channels"),
        "duration_sec": duration_sec,
    }


def load_optional_pyarrow() -> tuple[Any, Any]:
    try:
        import pyarrow as pa  # type: ignore
        import pyarrow.parquet as pq  # type: ignore
    except ImportError as error:
        raise RuntimeError(
            "pyarrow is required to materialize parquet-backed datasets. "
            "Run this command with `uv run --extra demo python scripts/download_datasets.py ...`."
        ) from error
    return pa, pq


def slugify(value: str, fallback: str = "item") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    cleaned = cleaned.strip("-._")
    return cleaned or fallback


def guess_extension_from_bytes(payload: bytes) -> str:
    if payload.startswith(b"RIFF") and payload[8:12] == b"WAVE":
        return ".wav"
    if payload.startswith(b"ID3") or payload[:2] == b"\xff\xfb":
        return ".mp3"
    if payload.startswith(b"fLaC"):
        return ".flac"
    if payload.startswith(b"OggS"):
        return ".ogg"
    if len(payload) > 8 and payload[4:8] == b"ftyp":
        return ".m4a"
    return ".bin"


def media_extension_for_audio_value(audio_value: dict[str, Any]) -> str:
    source_path = audio_value.get("path")
    if isinstance(source_path, str) and source_path:
        suffix = Path(source_path).suffix.lower()
        if suffix:
            return suffix
    payload = audio_value.get("bytes")
    if isinstance(payload, (bytes, bytearray)):
        return guess_extension_from_bytes(bytes(payload))
    return ".bin"


def parquet_output_filename(row: dict[str, Any], row_index: int, extension: str) -> str:
    candidates = [
        row.get("id"),
        row.get("speaker_id"),
        row.get("source_podcast"),
    ]
    audio_value = row.get("audio")
    if isinstance(audio_value, dict):
        audio_path = audio_value.get("path")
        if isinstance(audio_path, str) and audio_path:
            candidates.insert(0, Path(audio_path).stem)
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            stem = slugify(candidate)
            return f"{row_index:06d}-{stem}{extension}"
    return f"{row_index:06d}{extension}"


def write_bytes_if_needed(destination: Path, payload: bytes) -> bool:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size == len(payload):
        return False
    destination.write_bytes(payload)
    return True


def materialize_parquet_file(
    parquet_path: Path,
    output_dir: Path,
    dataset_root: Path,
    batch_size: int,
) -> dict[str, Any]:
    pa, pq = load_optional_pyarrow()
    parquet_file = pq.ParquetFile(parquet_path)
    rows_seen = 0
    files_written = 0
    extracted_records: list[dict[str, Any]] = []
    relative_parquet = parquet_path.relative_to(dataset_root)
    target_dir = output_dir / relative_parquet.parent / parquet_path.stem
    for batch in parquet_file.iter_batches(batch_size=batch_size):
        table = pa.Table.from_batches([batch])
        for row in table.to_pylist():
            audio_value = row.get("audio")
            row_index = rows_seen
            rows_seen += 1
            if not isinstance(audio_value, dict):
                continue
            payload = audio_value.get("bytes")
            if not isinstance(payload, (bytes, bytearray)) or not payload:
                continue
            extension = media_extension_for_audio_value(audio_value)
            filename = parquet_output_filename(row, row_index=row_index, extension=extension)
            destination = target_dir / filename
            written = write_bytes_if_needed(destination, bytes(payload))
            if written:
                files_written += 1
            extracted_records.append(
                {
                    "source_parquet": str(parquet_path.relative_to(ROOT)),
                    "row_index": row_index,
                    "output_path": str(destination.relative_to(ROOT)),
                    "source_audio_path": audio_value.get("path"),
                    "language": row.get("language"),
                    "start": row.get("start"),
                    "end": row.get("end"),
                    "speaker": row.get("speaker"),
                    "speaker_id": row.get("speaker_id"),
                }
            )
    return {
        "source_parquet": str(parquet_path.relative_to(ROOT)),
        "rows_seen": rows_seen,
        "files_written": files_written,
        "materialized_count": len(extracted_records),
        "records": extracted_records,
    }


def materialize_dataset_parquet_audio(dataset: dict[str, Any], batch_size: int) -> dict[str, Any]:
    target_dir = dataset_target_dir(dataset)
    parquet_files = sorted(target_dir.rglob("*.parquet"))
    manifest_payload = {
        "dataset_id": dataset["id"],
        "target_dir": str(target_dir.relative_to(ROOT)),
        "output_dir": str((target_dir / PARQUET_MEDIA_DIRNAME).relative_to(ROOT)),
        "generated_at_epoch": int(time.time()),
        "files": [],
        "errors": [],
    }
    if not parquet_files:
        parquet_materialization_manifest_path(dataset["id"]).write_text(json.dumps(manifest_payload, indent=2) + "\n")
        return {"dataset_id": dataset["id"], "parquet_files": 0, "rows_seen": 0, "files_written": 0}
    output_dir = target_dir / PARQUET_MEDIA_DIRNAME
    total_rows = 0
    total_written = 0
    for parquet_path in parquet_files:
        try:
            summary = materialize_parquet_file(
                parquet_path=parquet_path,
                output_dir=output_dir,
                dataset_root=target_dir,
                batch_size=batch_size,
            )
            total_rows += summary["rows_seen"]
            total_written += summary["files_written"]
            manifest_payload["files"].append(summary)
        except Exception as error:
            manifest_payload["errors"].append(
                {
                    "source_parquet": str(parquet_path.relative_to(ROOT)),
                    "error": str(error),
                }
            )
    parquet_materialization_manifest_path(dataset["id"]).write_text(json.dumps(manifest_payload, indent=2) + "\n")
    return {
        "dataset_id": dataset["id"],
        "parquet_files": len(parquet_files),
        "rows_seen": total_rows,
        "files_written": total_written,
        "errors": len(manifest_payload["errors"]),
    }


def unmanaged_parquet_datasets(selected_datasets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    managed_dirs = {dataset_target_dir(dataset).resolve() for dataset in selected_datasets}
    discovered: list[dict[str, Any]] = []
    for child in sorted(RAW_ROOT.iterdir() if RAW_ROOT.exists() else []):
        if not child.is_dir():
            continue
        if child.resolve() in managed_dirs:
            continue
        if not any(child.rglob("*.parquet")):
            continue
        discovered.append(
            {
                "id": child.name,
                "title": child.name.replace("_", " ").title(),
                "target_dir": str(child.relative_to(ROOT)),
                "source_url": "",
                "access_type": "local_only",
                "verification_rules": {},
            }
        )
    return discovered


def extract_local_archives(dataset: dict[str, Any]) -> dict[str, Any]:
    download_dir = dataset_download_dir(dataset["id"])
    target_dir = dataset_target_dir(dataset)
    target_dir.mkdir(parents=True, exist_ok=True)
    extracted = 0
    missing_archives: list[str] = []
    errors: list[dict[str, str]] = []
    for item in dataset.get("download", {}).get("items", []):
        if not item.get("extract"):
            continue
        archive_path = download_dir / item["filename"]
        if not archive_path.exists():
            missing_archives.append(str(archive_path.relative_to(ROOT)))
            continue
        try:
            extract_archive(archive_path, target_dir)
            extracted += 1
        except Exception as error:
            errors.append(
                {
                    "archive_path": str(archive_path.relative_to(ROOT)),
                    "error": str(error),
                }
            )
    return {
        "dataset_id": dataset["id"],
        "archives_considered": extracted + len(missing_archives) + len(errors),
        "archives_extracted": extracted,
        "missing_archives": missing_archives,
        "errors": errors,
    }


def tracked_dataset_files(target_dir: Path) -> list[Path]:
    files: list[Path] = []
    if not target_dir.exists():
        return files
    for path in target_dir.rglob("*"):
        if not path.is_file():
            continue
        relative_path = path.relative_to(target_dir).as_posix()
        if relative_path.startswith(".cache/huggingface/"):
            continue
        files.append(path)
    return sorted(files)


def build_inventory(dataset: dict[str, Any], status: str, error: str | None = None) -> dict[str, Any]:
    target_dir = dataset_target_dir(dataset)
    dataset_files = tracked_dataset_files(target_dir)
    media_files = [path for path in dataset_files if path.suffix.lower() in MEDIA_EXTENSIONS]
    parquet_files = [path for path in dataset_files if path.suffix.lower() == ".parquet"]
    verification = dataset.get("verification_rules", {})
    transcript_matches = find_matches(target_dir, verification.get("transcript_globs", []))
    label_matches = find_matches(target_dir, verification.get("label_globs", []))
    required_all = verification.get("required_all_globs", [])
    required_any = verification.get("required_any_globs", [])
    required_all_results = {
        pattern: [str(path.relative_to(ROOT)) for path in find_matches(target_dir, [pattern])]
        for pattern in required_all
    }
    required_any_results = {
        pattern: [str(path.relative_to(ROOT)) for path in find_matches(target_dir, [pattern])]
        for pattern in required_any
    }
    verification_errors: list[str] = []
    for pattern, matches in required_all_results.items():
        if not matches:
            verification_errors.append(f"Missing required pattern: {pattern}")
    if required_any and not any(required_any_results.values()):
        verification_errors.append(
            "Missing all of the required_any_globs patterns: " + ", ".join(required_any)
        )
    min_media_files = verification.get("min_media_files")
    if min_media_files is not None and len(media_files) < min_media_files:
        verification_errors.append(
            f"Expected at least {min_media_files} media files, found {len(media_files)}"
        )
    sample_probe = None
    if media_files:
        try:
            sample_probe = probe_media(media_files[0])
        except Exception as probe_error:  # pragma: no cover - best effort
            sample_probe = {
                "path": str(media_files[0].relative_to(ROOT)),
                "probe_error": str(probe_error),
            }
    elif dataset.get("inventory_probe", {}).get("type") == "huggingface_first_rows":
        try:
            sample_probe = probe_huggingface_first_rows(dataset["inventory_probe"])
        except Exception as probe_error:  # pragma: no cover - best effort
            sample_probe = {
                "path": str(parquet_files[0].relative_to(ROOT)) if parquet_files else str(target_dir.relative_to(ROOT)),
                "codec_name": "parquet",
                "probe_error": str(probe_error),
            }
    elif parquet_files:
        sample_probe = {
            "path": str(parquet_files[0].relative_to(ROOT)),
            "codec_name": "parquet",
            "sample_rate": None,
            "channels": None,
            "duration_sec": None,
        }
    inventory = {
        "dataset_id": dataset["id"],
        "title": dataset["title"],
        "status": status,
        "source_url": dataset["source_url"],
        "access_type": dataset["access_type"],
        "target_dir": str(target_dir.relative_to(ROOT)),
        "file_count": len(dataset_files),
        "total_bytes": sum(path.stat().st_size for path in dataset_files),
        "sample_audio_probe": sample_probe,
        "has_transcripts": bool(transcript_matches),
        "has_labels": bool(label_matches),
        "pipeline_coverage": dataset.get("pipeline_coverage", []),
        "verification": {
          "required_all_globs": required_all_results,
          "required_any_globs": required_any_results,
          "errors": verification_errors
        },
        "generated_at_epoch": int(time.time())
    }
    if error:
        inventory["error"] = error
    if "manual_access" in dataset:
        inventory["manual_access"] = dataset["manual_access"]
    return inventory


def write_inventory(dataset_id: str, inventory: dict[str, Any]) -> None:
    inventory_path(dataset_id).write_text(json.dumps(inventory, indent=2) + "\n")


def fetch_open_dataset(dataset: dict[str, Any]) -> dict[str, Any]:
    download_dir = dataset_download_dir(dataset["id"])
    target_dir = dataset_target_dir(dataset)
    download_dir.mkdir(parents=True, exist_ok=True)
    target_dir.mkdir(parents=True, exist_ok=True)
    snapshot_config = dataset.get("download", {}).get("snapshot")
    if snapshot_config:
        log(f"[{dataset['id']}] snapshotting {snapshot_config['repo_id']}")
        snapshot_download_repo(snapshot_config, target_dir)
    for item in dataset.get("download", {}).get("items", []):
        destination = download_dir / item["filename"]
        log(f"[{dataset['id']}] downloading {item['filename']}")
        curl_download(item["url"], destination)
        if item.get("checksum_md5"):
            verify_checksum(destination, item["checksum_md5"])
        if item.get("extract"):
            log(f"[{dataset['id']}] extracting {item['filename']}")
            extract_archive(destination, target_dir)
        if item.get("target_relpath"):
            copy_to_target(destination, target_dir / item["target_relpath"])
    inventory = build_inventory(dataset, status="downloaded")
    if inventory["verification"]["errors"]:
        inventory["status"] = "downloaded_with_warnings"
    write_inventory(dataset["id"], inventory)
    return inventory


def queue_manual_dataset(dataset: dict[str, Any]) -> dict[str, Any]:
    target_dir = dataset_target_dir(dataset)
    target_dir.mkdir(parents=True, exist_ok=True)
    inventory = build_inventory(dataset, status="queued_manual_access")
    write_inventory(dataset["id"], inventory)
    return inventory


def fetch_dataset(dataset: dict[str, Any]) -> dict[str, Any]:
    try:
        if dataset["access_type"] in {"open", "open_manual_download"}:
            return fetch_open_dataset(dataset)
        return queue_manual_dataset(dataset)
    except Exception as error:
        inventory = build_inventory(dataset, status="download_failed", error=str(error))
        write_inventory(dataset["id"], inventory)
        raise


def inventory_dataset(dataset: dict[str, Any]) -> dict[str, Any]:
    if dataset["access_type"] in {"open", "open_manual_download"}:
        status = "downloaded" if dataset_target_dir(dataset).exists() else "not_downloaded"
    else:
        status = "queued_manual_access"
    inventory = build_inventory(dataset, status=status)
    if inventory["verification"]["errors"] and status == "downloaded":
        inventory["status"] = "downloaded_with_warnings"
    write_inventory(dataset["id"], inventory)
    return inventory


def print_list(manifest: dict[str, Any]) -> None:
    for dataset in manifest["datasets"]:
        print(
            f"{dataset['id']}: access_type={dataset['access_type']} "
            f"grouped_target={dataset['target_dir']} source={dataset['source_url']}"
        )


def run_fetch(manifest: dict[str, Any], args: argparse.Namespace) -> int:
    ensure_layout()
    dataset_map = datasets_by_id(manifest)
    selected_ids = resolve_dataset_ids(manifest, args)
    selected_datasets = [dataset_map[dataset_id] for dataset_id in selected_ids]
    exit_code = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = {executor.submit(fetch_dataset, dataset): dataset for dataset in selected_datasets}
        for future in concurrent.futures.as_completed(futures):
            dataset = futures[future]
            try:
                inventory = future.result()
                log(
                    f"[{dataset['id']}] {inventory['status']} "
                    f"files={inventory['file_count']} bytes={inventory['total_bytes']}"
                )
            except Exception as error:
                exit_code = 1
                log(f"[{dataset['id']}] failed: {error}")
    return exit_code


def run_inventory(manifest: dict[str, Any], args: argparse.Namespace) -> int:
    ensure_layout()
    dataset_map = datasets_by_id(manifest)
    selected_ids = resolve_dataset_ids(manifest, args)
    for dataset_id in selected_ids:
        inventory = inventory_dataset(dataset_map[dataset_id])
        log(
            f"[{dataset_id}] {inventory['status']} files={inventory['file_count']} "
            f"bytes={inventory['total_bytes']}"
        )
    return 0


def run_materialize_local(manifest: dict[str, Any], args: argparse.Namespace) -> int:
    ensure_layout()
    dataset_map = datasets_by_id(manifest)
    selected_ids = resolve_dataset_ids(manifest, args)
    selected_datasets = [dataset_map[dataset_id] for dataset_id in selected_ids]
    worklist = selected_datasets + unmanaged_parquet_datasets(selected_datasets)
    exit_code = 0
    for dataset in worklist:
        dataset_id = dataset["id"]
        archive_summary = extract_local_archives(dataset)
        if archive_summary["archives_considered"]:
            log(
                f"[{dataset_id}] archives extracted={archive_summary['archives_extracted']} "
                f"missing={len(archive_summary['missing_archives'])} "
                f"errors={len(archive_summary['errors'])}"
            )
            for error in archive_summary["errors"]:
                log(f"[{dataset_id}] archive error: {error['archive_path']} :: {error['error']}")
            if archive_summary["errors"]:
                exit_code = 1
        nested_summary = extract_nested_archives(dataset_target_dir(dataset))
        if nested_summary["archives_extracted"] or nested_summary["errors"]:
            log(
                f"[{dataset_id}] nested archives extracted={nested_summary['archives_extracted']} "
                f"errors={len(nested_summary['errors'])}"
            )
            for error in nested_summary["errors"]:
                log(f"[{dataset_id}] nested archive error: {error['archive_path']} :: {error['error']}")
            if nested_summary["errors"]:
                exit_code = 1
        try:
            parquet_summary = materialize_dataset_parquet_audio(dataset, batch_size=args.batch_size)
            if parquet_summary["parquet_files"]:
                log(
                    f"[{dataset_id}] materialized parquet_files={parquet_summary['parquet_files']} "
                    f"rows={parquet_summary['rows_seen']} wrote={parquet_summary['files_written']} "
                    f"errors={parquet_summary['errors']}"
                )
                if parquet_summary["errors"]:
                    exit_code = 1
        except RuntimeError as error:
            if "pyarrow is required" in str(error):
                raise
            exit_code = 1
            log(f"[{dataset_id}] materialization failed: {error}")
        if dataset_id in dataset_map:
            inventory = inventory_dataset(dataset)
            log(
                f"[{dataset_id}] {inventory['status']} files={inventory['file_count']} "
                f"bytes={inventory['total_bytes']}"
            )
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manifest-driven dataset acquisition workflow.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List datasets in the manifest.")
    list_parser.set_defaults(handler=lambda manifest, args: print_list(manifest) or 0)

    fetch_parser = subparsers.add_parser("fetch", help="Download open datasets or queue manual-access datasets.")
    fetch_parser.add_argument("--dataset", action="append", help="Dataset id to fetch. Repeat as needed.")
    fetch_parser.add_argument("--group", help="Named dataset group to fetch.")
    fetch_parser.add_argument("--all", action="store_true", help="Fetch every dataset entry.")
    fetch_parser.add_argument("--jobs", type=int, default=4, help="Number of datasets to process in parallel.")
    fetch_parser.set_defaults(handler=run_fetch)

    inventory_parser = subparsers.add_parser("inventory", help="Generate inventory records from current files.")
    inventory_parser.add_argument("--dataset", action="append", help="Dataset id to inventory. Repeat as needed.")
    inventory_parser.add_argument("--group", help="Named dataset group to inventory.")
    inventory_parser.add_argument("--all", action="store_true", help="Inventory every dataset entry.")
    inventory_parser.set_defaults(handler=run_inventory)

    materialize_parser = subparsers.add_parser(
        "materialize-local",
        help="Extract downloaded archives and materialize parquet-backed audio into local media files.",
    )
    materialize_parser.add_argument("--dataset", action="append", help="Dataset id to process. Repeat as needed.")
    materialize_parser.add_argument("--group", help="Named dataset group to process.")
    materialize_parser.add_argument("--all", action="store_true", help="Process every dataset entry.")
    materialize_parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Rows to process per parquet batch when materializing audio.",
    )
    materialize_parser.set_defaults(handler=run_materialize_local)

    return parser


def main() -> int:
    manifest = load_manifest()
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(manifest, args)


if __name__ == "__main__":
    sys.exit(main())
