from __future__ import annotations

from pathlib import Path


EMOTION_MAP = {
    "01": "neutral",
    "02": "calm",
    "03": "happy",
    "04": "sad",
    "05": "angry",
    "06": "fearful",
    "07": "disgusted",
    "08": "surprised",
}


def parse_ravdess_reference(path: str | Path) -> dict[str, str] | None:
    filename = Path(path).name
    stem = filename.rsplit(".", 1)[0]
    parts = stem.split("-")
    if len(parts) != 7:
        return None

    emotion_code = parts[2]
    if emotion_code not in EMOTION_MAP:
        return None

    return {
        "reference_label": EMOTION_MAP[emotion_code],
        "intensity": "strong" if parts[3] == "02" else "normal",
        "actor_id": parts[6],
    }
