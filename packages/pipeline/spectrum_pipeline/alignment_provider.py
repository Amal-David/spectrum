from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_alignment_cache(cache_path: Path) -> dict[str, Any] | None:
    if not cache_path.exists():
        return None
    try:
        payload = json.loads(cache_path.read_text())
    except json.JSONDecodeError:
        return None
    if payload.get("provider_key") != "whisperx":
        return None
    return payload


def save_alignment_cache(cache_path: Path, payload: dict[str, Any]) -> None:
    cache_path.write_text(json.dumps(payload, indent=2) + "\n")


def align_words_with_whisperx(audio_path: Path, words: list[dict[str, Any]], language: str | None = "en") -> tuple[list[dict[str, Any]], list[str]]:
    try:  # pragma: no cover - optional runtime path
        import whisperx  # type: ignore
    except ImportError:
        return words, ["alignment_missing"]

    if not words:
        return [], ["alignment_missing"]

    segments: list[dict[str, Any]] = []
    current_words: list[dict[str, Any]] = []
    current_start = int(words[0].get("start_ms", 0))
    current_end = int(words[0].get("end_ms", 0))
    for word in words:
        word_text = str(word.get("word") or "").strip()
        if not word_text:
            continue
        if current_words and word_text.endswith((".", "!", "?")):
            current_words.append(word)
            current_end = int(word.get("end_ms", current_end))
            segments.append(
                {
                    "start": current_start / 1000,
                    "end": current_end / 1000,
                    "text": " ".join(str(item.get("word") or "").strip() for item in current_words).strip(),
                }
            )
            current_words = []
            continue
        if not current_words:
            current_start = int(word.get("start_ms", 0))
        current_words.append(word)
        current_end = int(word.get("end_ms", current_end))
    if current_words:
        segments.append(
            {
                "start": current_start / 1000,
                "end": current_end / 1000,
                "text": " ".join(str(item.get("word") or "").strip() for item in current_words).strip(),
            }
        )

    if not segments:
        return words, ["alignment_missing"]

    try:  # pragma: no cover - optional runtime path
        model, metadata = whisperx.load_align_model(language_code=(language or "en")[:2], device="cpu")
        aligned = whisperx.align(segments, model, metadata, str(audio_path), device="cpu")
    except Exception as error:
        return words, [f"alignment_missing", f"whisperx_failed:{error.__class__.__name__}"]

    aligned_words: list[dict[str, Any]] = []
    aligned_segments = aligned.get("segments", []) if isinstance(aligned, dict) else []
    for segment in aligned_segments:
        for word in segment.get("words", []) or []:
            token = str(word.get("word") or "").strip()
            if not token:
                continue
            aligned_words.append(
                {
                    "word": token,
                    "start_ms": int(float(word.get("start", 0.0)) * 1000),
                    "end_ms": int(float(word.get("end", 0.0)) * 1000),
                    "confidence": float(word.get("score", 0.0) or 0.0),
                    "source": "model",
                    "speaker_id": word.get("speaker_id"),
                }
            )
    if not aligned_words:
        return words, ["alignment_missing"]
    return aligned_words, []
