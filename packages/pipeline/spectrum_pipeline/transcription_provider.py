from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_transcription_cache(cache_path: Path) -> dict[str, Any] | None:
    if not cache_path.exists():
        return None
    try:
        return json.loads(cache_path.read_text())
    except json.JSONDecodeError:
        return None


def save_transcription_cache(cache_path: Path, payload: dict[str, Any]) -> None:
    cache_path.write_text(json.dumps(payload, indent=2) + "\n")


def normalize_word_records(words: list[dict[str, Any]], *, source: str = "model") -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for word in words:
        text = str(word.get("word") or "").strip()
        if not text:
            continue
        normalized.append(
            {
                "word": text,
                "start_ms": int(word.get("start_ms", word.get("start", 0))),
                "end_ms": int(word.get("end_ms", word.get("end", 0))),
                "confidence": float(word.get("confidence", 0.0)),
                "source": source,
                "speaker_id": word.get("speaker_id"),
            }
        )
    return normalized


def transcribe_with_faster_whisper(
    audio_path: Path,
    *,
    model_name: str = "tiny",
) -> tuple[str, list[dict[str, Any]], list[str]]:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError:
        return "", [], ["asr_model_unavailable"]

    try:
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(str(audio_path), vad_filter=True, word_timestamps=True)
        segment_list = list(segments)
    except Exception as error:  # pragma: no cover - optional runtime path
        return "", [], [f"asr_failed:{error.__class__.__name__}"]

    transcript = " ".join(segment.text.strip() for segment in segment_list if segment.text.strip())
    words: list[dict[str, Any]] = []
    for segment in segment_list:
        for word in list(getattr(segment, "words", []) or []):
            text = str(getattr(word, "word", "") or "").strip()
            if not text:
                continue
            words.append(
                {
                    "word": text,
                    "start_ms": int(float(getattr(word, "start", 0.0)) * 1000),
                    "end_ms": int(float(getattr(word, "end", 0.0)) * 1000),
                    "confidence": float(getattr(word, "probability", getattr(word, "confidence", 0.0)) or 0.0),
                    "source": "model",
                }
            )
    if not transcript:
        return "", [], ["asr_empty_output"]
    return transcript, words, []
