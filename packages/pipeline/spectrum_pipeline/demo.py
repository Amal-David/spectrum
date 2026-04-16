from __future__ import annotations

import argparse
import ast
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from spectrum_core.constants import FIXTURES_DIR, REPO_ROOT
from spectrum_core.datasets import list_dataset_records, load_demo_manifest
from spectrum_core.ravdess import parse_ravdess_reference

from .service import ProcessSessionOptions, SessionStore, create_session_result


def _dataset_index() -> dict[str, dict[str, Any]]:
    return {record["id"]: record for record in list_dataset_records()}


def _statement_from_ravdess_filename(path: Path) -> str:
    parts = path.stem.split("-")
    if len(parts) != 7:
        return ""
    return {
        "01": "Kids are talking by the door.",
        "02": "Dogs are sitting by the door.",
    }.get(parts[4], "")


def _voice_hint_from_ravdess_filename(path: Path) -> str:
    parts = path.stem.split("-")
    if len(parts) != 7:
        return "unknown"
    actor_id = int(parts[6])
    return "male" if actor_id % 2 == 1 else "female"


def _ensure_demo_audio_dir() -> Path:
    audio_dir = FIXTURES_DIR / "demo_samples" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    return audio_dir


def _materialize_direct_file(sample: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    source_path = Path(sample["absolute_source_path"])
    metadata = {
        "title": sample["title"],
        "dataset_id": sample.get("source_dataset"),
        "language_hint": sample.get("language"),
        "notes": sample.get("notes"),
        "analysis_label": sample.get("analysis_label"),
    }
    if sample.get("source_dataset") == "ravdess_speech_16k":
        metadata["transcript_hint"] = _statement_from_ravdess_filename(source_path)
        metadata["voice_presentation_hint"] = _voice_hint_from_ravdess_filename(source_path)
        metadata["reference_label"] = (parse_ravdess_reference(source_path) or {}).get("reference_label")
    return source_path, metadata


def _load_pyarrow():
    try:
        import pyarrow.parquet as pq  # type: ignore
    except ImportError as error:  # pragma: no cover
        raise RuntimeError(
            "pyarrow is required for parquet-backed demo samples. Install it with `uv pip install -e \".[demo]\"`."
        ) from error
    return pq


def _pick_parquet_row(dataset_root: Path, selector_language: str) -> tuple[Path, dict[str, Any]]:
    pq = _load_pyarrow()
    for path in sorted(dataset_root.glob("*.parquet")):
        table = pq.read_table(path)
        for row in table.to_pylist():
            if str(row.get("language", "")).strip().lower() == selector_language:
                return path, row
    raise RuntimeError(f"No parquet row matched language '{selector_language}' in {dataset_root}.")


def _materialize_conversation_sample(sample: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    dataset_root = REPO_ROOT / "data" / "raw" / "indic_audio_natural_conversations_sample"
    selector_language = sample.get("selector", {}).get("language")
    if not selector_language:
        raise RuntimeError(f"Sample {sample['job_id']} is missing a language selector.")

    _source_parquet, row = _pick_parquet_row(dataset_root, selector_language)
    target_path = _ensure_demo_audio_dir() / f"{sample['job_id']}.wav"
    target_path.write_bytes(row["audio"]["bytes"])

    dialogue_turns = ast.literal_eval(row["dialogue"])
    turns = ast.literal_eval(row["turns"])
    speaker_sequence = [
        f"speaker_{turn % 2}" if isinstance(turn, int) else f"speaker_{index % 2}"
        for index, turn in enumerate(turns)
    ]
    speaker_hints = {
        "speaker_0": {
            "voice_presentation": "female" if str(row.get("user_gender_side_0", "")).lower() == "woman" else "male",
            "age": row.get("user_age_side_0"),
        },
        "speaker_1": {
            "voice_presentation": "female" if str(row.get("user_gender_side_1", "")).lower() == "woman" else "male",
            "age": row.get("user_age_side_1"),
        },
    }
    metadata = {
        "title": sample["title"],
        "dataset_id": sample.get("source_dataset"),
        "dataset_title": "Indic Audio Natural Conversations Sample",
        "access_type": "gated_huggingface",
        "language_hint": selector_language,
        "transcript_hint": " ".join(dialogue_turns),
        "dialogue_turns": dialogue_turns,
        "speaker_sequence": speaker_sequence,
        "speaker_hints": speaker_hints,
        "notes": sample.get("notes"),
        "reference_label": f"{selector_language}-conversation",
    }
    return target_path, metadata


def _ami_words_root(meeting_id: str, channel: str) -> ET.Element:
    path = REPO_ROOT / "data" / "raw" / "ami_corpus" / "words" / f"{meeting_id}.{channel}.words.xml"
    return ET.parse(path).getroot()


def _ami_speaker_id(channel: str) -> str:
    return f"speaker_{channel.lower()}"


def _ami_speaker_label(channel: str) -> str:
    return f"Speaker {channel.upper()}"


def _group_ami_segments(
    meeting_id: str,
    channel: str,
    *,
    start_sec: float,
    end_sec: float,
    gap_threshold_sec: float = 0.9,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    root = _ami_words_root(meeting_id, channel)
    speaker_id = _ami_speaker_id(channel)
    segments: list[dict[str, Any]] = []
    cues: list[dict[str, Any]] = []
    current_segment: dict[str, Any] | None = None

    def flush_segment() -> None:
        nonlocal current_segment
        if current_segment and current_segment["text"].strip():
            segments.append(current_segment)
        current_segment = None

    for index, child in enumerate(root.iter()):
        tag = child.tag.split("}")[-1]
        raw_start = float(child.attrib.get("starttime", 0.0))
        raw_end = float(child.attrib.get("endtime", raw_start))
        if raw_end < start_sec or raw_start > end_sec:
            continue

        relative_start_ms = max(0, int(round((raw_start - start_sec) * 1000)))
        relative_end_ms = max(relative_start_ms, int(round((raw_end - start_sec) * 1000)))
        if tag == "w":
            text = (child.text or "").strip()
            if not text:
                continue
            if child.attrib.get("punc") == "true":
                if current_segment and current_segment["text"]:
                    current_segment["text"] = f"{current_segment['text']}{text}"
                    current_segment["end_ms"] = relative_end_ms
                continue

            if current_segment is None or (relative_start_ms - current_segment["end_ms"]) > int(gap_threshold_sec * 1000):
                flush_segment()
                current_segment = {
                    "turn_id": f"{meeting_id}-{channel.lower()}-{len(segments)}",
                    "speaker_id": speaker_id,
                    "label": _ami_speaker_label(channel),
                    "start_ms": relative_start_ms,
                    "end_ms": relative_end_ms,
                    "text": text,
                    "source": "benchmark_label",
                    "confidence": 0.96,
                }
            else:
                current_segment["text"] = f"{current_segment['text']} {text}"
                current_segment["end_ms"] = relative_end_ms
            continue

        if tag == "vocalsound":
            cue_type = str(child.attrib.get("type", "vocal_sound")).strip().replace(" ", "_")
            cues.append(
                {
                    "cue_id": f"{meeting_id}-{channel.lower()}-cue-{index}",
                    "benchmark_id": str(child.attrib.get("{http://nite.sourceforge.net/}id", f"{meeting_id}:{channel}:{index}")),
                    "type": cue_type,
                    "family": "vocal_sound",
                    "label": cue_type.replace("_", " "),
                    "speaker_id": speaker_id,
                    "start_ms": relative_start_ms,
                    "end_ms": relative_end_ms,
                    "confidence": 0.99 if cue_type == "laugh" else 0.9,
                }
            )

    flush_segment()
    return segments, cues


def _materialize_ami_benchmark_sample(sample: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    selector = sample.get("selector", {})
    meeting_id = selector.get("meeting_id", "ES2002a")
    start_sec = float(selector.get("start_sec", 236.0))
    duration_sec = float(selector.get("duration_sec", 18.0))
    end_sec = start_sec + duration_sec
    source_path = REPO_ROOT / "data" / "raw" / "ami_corpus" / "amicorpus" / meeting_id / "audio" / f"{meeting_id}.Mix-Headset.wav"
    target_path = _ensure_demo_audio_dir() / f"{sample['job_id']}.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start_sec}",
            "-t",
            f"{duration_sec}",
            "-i",
            str(source_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-vn",
            "-c:a",
            "pcm_s16le",
            str(target_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    all_segments: list[dict[str, Any]] = []
    all_cues: list[dict[str, Any]] = []
    speaker_roles: dict[str, str] = {}
    for channel in ("A", "B", "C", "D"):
        segments, cues = _group_ami_segments(meeting_id, channel, start_sec=start_sec, end_sec=end_sec)
        all_segments.extend(segments)
        all_cues.extend(cues)
        speaker_roles[_ami_speaker_id(channel)] = _ami_speaker_label(channel)

    all_segments.sort(key=lambda segment: (segment["start_ms"], segment["speaker_id"]))
    all_cues.sort(key=lambda cue: (cue["start_ms"], cue["speaker_id"] or ""))
    transcript_hint = " ".join(segment["text"] for segment in all_segments).strip()

    metadata = {
        "title": sample["title"],
        "dataset_id": sample.get("source_dataset"),
        "dataset_title": "AMI Corpus",
        "access_type": "local_corpus",
        "language_hint": sample.get("language", "en"),
        "transcript_hint": transcript_hint,
        "speaker_segments": all_segments,
        "speaker_roles": speaker_roles,
        "benchmark_diarization": True,
        "benchmark_nonverbal_cues": all_cues,
        "reference_label": f"{meeting_id}:{start_sec:.1f}-{end_sec:.1f}",
        "source_type": "materialized_audio_dataset",
        "session_type": "meeting_benchmark",
        "call_channel": "meeting_room",
        "notes": sample.get("notes"),
    }
    return target_path, metadata


def materialize_demo_audio() -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for sample in load_demo_manifest():
        strategy = sample.get("fixture_strategy", "direct_file")
        if strategy == "direct_file":
            source_path, metadata = _materialize_direct_file(sample)
        elif strategy == "conversation_parquet_language_pick":
            source_path, metadata = _materialize_conversation_sample(sample)
        elif strategy == "ami_benchmark_pick":
            source_path, metadata = _materialize_ami_benchmark_sample(sample)
        else:  # pragma: no cover
            raise RuntimeError(f"Unknown fixture strategy '{strategy}' for {sample['job_id']}.")
        prepared.append({**sample, "materialized_source_path": str(source_path), "metadata": metadata})
    return prepared


def bootstrap_demo_runs() -> list[Path]:
    dataset_index = _dataset_index()
    store = SessionStore()
    written_paths: list[Path] = []

    for sample in materialize_demo_audio():
        dataset_record = dataset_index.get(sample.get("source_dataset", ""), {})
        metadata = {
            **sample["metadata"],
            "dataset_title": dataset_record.get("title", sample["metadata"].get("dataset_title")),
            "access_type": dataset_record.get("access_type", sample["metadata"].get("access_type")),
            "title": sample["title"],
        }
        store.seed_session(sample["job_id"], sample["analysis_mode"], metadata=metadata)
        store.save_upload(sample["job_id"], Path(sample["materialized_source_path"]).name, Path(sample["materialized_source_path"]))
        store.set_processing(sample["job_id"])
        create_session_result(
            job_id=sample["job_id"],
            analysis_mode=sample["analysis_mode"],
            original_path=Path(sample["materialized_source_path"]),
            options=ProcessSessionOptions(metadata=metadata),
        )
        store.set_completed(sample["job_id"], Path("runs") / sample["job_id"] / "result.json")
        written_paths.append(Path("runs") / sample["job_id"] / "result.json")
    return written_paths


def clean_demo_runs() -> None:
    for sample in load_demo_manifest():
        run_dir = REPO_ROOT / "runs" / sample["job_id"]
        if run_dir.exists():
            shutil.rmtree(run_dir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Spectrum demo analysis helpers")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("bootstrap", help="Materialize demo samples and write result bundles")
    subparsers.add_parser("materialize", help="Materialize demo audio files only")
    subparsers.add_parser("clean", help="Remove generated demo run folders")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "bootstrap":
        for written_path in bootstrap_demo_runs():
            print(written_path)
        return 0
    if args.command == "materialize":
        print(json.dumps(materialize_demo_audio(), indent=2))
        return 0
    if args.command == "clean":
        clean_demo_runs()
        return 0
    parser.error("Unknown command")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
