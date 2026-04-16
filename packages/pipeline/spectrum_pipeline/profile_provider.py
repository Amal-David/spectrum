from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


_ACCENT_LABEL_MAP = {
    "us": "american",
    "american": "american",
    "england": "british",
    "british": "british",
    "uk": "british",
    "australian": "australian",
    "india": "indian",
    "indian": "indian",
    "african": "african_english",
    "irish": "irish",
    "canadian": "canadian",
}


def _normalize_accent_label(label: str | None) -> str | None:
    if not label:
        return None
    lowered = re.sub(r"[^a-z]+", " ", label.lower()).strip()
    if not lowered:
        return None
    for token, normalized in _ACCENT_LABEL_MAP.items():
        if token in lowered:
            return normalized
    if "english" in lowered:
        return "english_other"
    return lowered.replace(" ", "_")


def infer_accent_broad_signal(
    audio_path: Path,
    metadata: dict[str, Any],
    *,
    trusted_metadata: bool,
    adapters: list[Any],
) -> dict[str, Any]:
    hint = (
        metadata.get("accent_broad_hint")
        or metadata.get("accent_hint")
        or metadata.get("accent_label")
        or metadata.get("reference_label")
    )
    normalized_hint = _normalize_accent_label(str(hint)) if hint else None
    if normalized_hint and trusted_metadata:
        return {
            "label": normalized_hint,
            "confidence": 0.76,
            "source": "benchmark_label" if metadata.get("dataset_id") in {"ravdess_speech_16k", "meld"} else "metadata_hint",
            "warning_flags": ["metadata_hint_not_model_inference"],
            "summary": "Broad accent is using trusted dataset or metadata hints for this session.",
        }

    speechbrain_available = any(getattr(adapter, "key", None) == "speechbrain_commonaccent" and getattr(adapter, "available", False) for adapter in adapters)
    repo_id = os.environ.get("SPECTRUM_COMMONACCENT_REPO_ID", "").strip()
    if speechbrain_available and repo_id:
        try:  # pragma: no cover - optional runtime path
            from speechbrain.inference.classifiers import EncoderClassifier  # type: ignore

            classifier = EncoderClassifier.from_hparams(source=repo_id, savedir=str(audio_path.parent / ".speechbrain-cache"))
            _out_prob, score, _index, text_lab = classifier.classify_file(str(audio_path))
            candidate = _normalize_accent_label(str(text_lab[0] if isinstance(text_lab, (list, tuple)) else text_lab))
            if candidate:
                return {
                    "label": candidate,
                    "confidence": float(score[0]) if hasattr(score, "__getitem__") else float(score),
                    "source": "model",
                    "warning_flags": [],
                    "summary": "Broad accent is using a configured SpeechBrain classifier.",
                }
        except Exception as error:  # pragma: no cover - optional runtime path
            return {
                "label": "unknown",
                "confidence": 0.0,
                "source": "unavailable",
                "warning_flags": [f"speechbrain_commonaccent_failed:{error.__class__.__name__}"],
                "summary": "Configured broad-accent inference failed at runtime.",
            }

    if normalized_hint:
        return {
            "label": normalized_hint,
            "confidence": 0.46,
            "source": "metadata_hint",
            "warning_flags": ["metadata_hint_not_model_inference"],
            "summary": "Broad accent hint is present but not trusted enough to show strongly on ad hoc uploads.",
        }
    return {
        "label": "unknown",
        "confidence": 0.0,
        "source": "unavailable",
        "warning_flags": ["accent_model_not_configured"] if speechbrain_available and not repo_id else [],
        "summary": "No broad-accent model or trusted benchmark hint was available.",
    }


def infer_voice_presentation_signal(
    metadata: dict[str, Any],
    *,
    trusted_metadata: bool,
) -> dict[str, Any]:
    voice_hint = metadata.get("voice_presentation_hint")
    if not voice_hint:
        speaker_hints = metadata.get("speaker_hints", {})
        if speaker_hints:
            first = next(iter(speaker_hints.values()))
            if isinstance(first, dict):
                voice_hint = first.get("voice_presentation")
    if not voice_hint:
        return {
            "label": "unknown",
            "confidence": 0.0,
            "source": "unavailable",
            "warning_flags": [],
            "summary": "No safe voice-presentation signal was available.",
        }
    return {
        "label": str(voice_hint).lower().replace(" ", "_"),
        "confidence": 0.66 if trusted_metadata else 0.38,
        "source": "metadata_hint",
        "warning_flags": ["metadata_hint_not_model_inference"],
        "summary": "Voice presentation is derived from metadata hints and remains a soft proxy.",
    }


def infer_age_signal(
    metadata: dict[str, Any],
    *,
    trusted_metadata: bool,
) -> dict[str, Any]:
    age_hint = metadata.get("age_hint")
    if age_hint is None:
        speaker_hints = metadata.get("speaker_hints", {})
        if speaker_hints:
            first = next(iter(speaker_hints.values()))
            if isinstance(first, dict):
                age_hint = first.get("age")
    if age_hint is None:
        return {
            "age": None,
            "confidence": 0.0,
            "source": "unavailable",
            "warning_flags": [],
            "summary": "No age-band signal was available.",
        }
    try:
        age_value = float(age_hint)
    except (TypeError, ValueError):
        return {
            "age": None,
            "confidence": 0.0,
            "source": "unavailable",
            "warning_flags": ["invalid_age_hint"],
            "summary": "Age hint could not be parsed safely.",
        }
    return {
        "age": age_value,
        "confidence": 0.64 if trusted_metadata else 0.34,
        "source": "metadata_hint" if trusted_metadata else "heuristic",
        "warning_flags": ["metadata_hint_not_model_inference"],
        "summary": "Age is surfaced only as a confidence-gated age band.",
    }
