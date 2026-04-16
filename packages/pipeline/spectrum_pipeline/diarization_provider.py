from __future__ import annotations

import json
import os
from pathlib import Path

from spectrum_core.models import DiarizationSegment


def load_diarization_cache(cache_path: Path) -> list[DiarizationSegment] | None:
    if not cache_path.exists():
        return None
    try:
        payload = json.loads(cache_path.read_text())
    except json.JSONDecodeError:
        return None
    if payload.get("provider_key") != "pyannote":
        return None
    return [DiarizationSegment.model_validate(item) for item in payload.get("segments", [])]


def save_diarization_cache(cache_path: Path, segments: list[DiarizationSegment]) -> None:
    cache_path.write_text(
        json.dumps(
            {
                "provider_key": "pyannote",
                "segments": [segment.model_dump(mode="json") for segment in segments],
            },
            indent=2,
        )
        + "\n"
    )


def diarize_with_pyannote(audio_path: Path) -> tuple[list[DiarizationSegment], list[str]]:
    try:  # pragma: no cover - optional runtime path
        from pyannote.audio import Pipeline  # type: ignore
    except ImportError:
        return [], ["pyannote_missing"]

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    if not token:
        return [], ["pyannote_token_missing"]

    try:  # pragma: no cover - optional runtime path
        pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", use_auth_token=token)
        diarization = pipeline(str(audio_path))
    except Exception as error:
        return [], [f"pyannote_failed:{error.__class__.__name__}"]

    segments: list[DiarizationSegment] = []
    for index, (window, _track, speaker) in enumerate(diarization.itertracks(yield_label=True)):
        start_ms = int(window.start * 1000)
        end_ms = int(window.end * 1000)
        segments.append(
            DiarizationSegment(
                segment_id=f"pyannote-{index}",
                speaker_id=str(speaker),
                start_ms=start_ms,
                end_ms=end_ms,
                confidence=0.81,
                source="model",
                display_state="visible",
                label=str(speaker),
            )
        )
    return segments, []
