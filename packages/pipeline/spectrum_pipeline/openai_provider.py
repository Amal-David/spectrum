from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

from spectrum_core.constants import REPO_ROOT

OPENAI_API_BASE_URL = "https://api.openai.com/v1"
DEFAULT_TRANSCRIBE_MODEL = "gpt-4o-transcribe"
DEFAULT_ANALYZE_MODEL = "gpt-4.1-mini"
_ENV_LOADED = False


def load_local_env() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        for raw_line in env_path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = value
    _ENV_LOADED = True


def openai_api_key() -> str | None:
    load_local_env()
    return os.environ.get("OPENAI_API_KEY")


def openai_enabled() -> bool:
    return bool(openai_api_key())


def _client() -> httpx.Client:
    api_key = openai_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return httpx.Client(
        base_url=OPENAI_API_BASE_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=httpx.Timeout(120.0, connect=20.0),
    )


def transcribe_audio_with_openai(audio_path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    api_key = openai_api_key()
    if not api_key:
        return None, ["openai_api_key_missing"]

    model = os.environ.get("SPECTRUM_OPENAI_MODEL_TRANSCRIBE", DEFAULT_TRANSCRIBE_MODEL)
    warnings: list[str] = []
    try:
        with _client() as client, audio_path.open("rb") as handle:
            response = client.post(
                "/audio/transcriptions",
                data={"model": model, "response_format": "json"},
                files={"file": (audio_path.name, handle, "audio/wav")},
            )
        response.raise_for_status()
        payload = response.json()
    except Exception as error:
        return None, [f"openai_transcription_failed:{error.__class__.__name__}"]

    if not isinstance(payload, dict):
        payload = {"text": str(payload)}
    transcript = str(payload.get("text") or "").strip()
    words = payload.get("words") or []
    segments = payload.get("segments") or []
    if not transcript:
        warnings.append("openai_transcript_empty")
    return {
        "transcript": transcript,
        "words": words,
        "segments": segments,
        "model": model,
        "raw": payload,
    }, warnings


def analyze_conversation_with_openai(
    transcript: str,
    turns: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    api_key = openai_api_key()
    if not api_key:
        return None, ["openai_api_key_missing"]
    if not transcript.strip():
        return None, ["openai_transcript_empty"]

    model = os.environ.get("SPECTRUM_OPENAI_MODEL_ANALYZE", DEFAULT_ANALYZE_MODEL)
    metadata = metadata or {}
    transcript_preview = "\n".join(
        f"[{turn.get('speaker_id', 'speaker_unknown')}] {turn.get('text', '').strip()}" for turn in turns if str(turn.get("text", "")).strip()
    ) or transcript

    schema = {
        "name": "human_ai_conversation_analysis",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "speaker_roles": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "speaker_id": {"type": "string"},
                            "speaker_role": {"type": "string", "enum": ["human", "ai", "unknown"]},
                            "confidence": {"type": "number"},
                            "notes": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["speaker_id", "speaker_role", "confidence", "notes"],
                    },
                },
                "turn_annotations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "turn_id": {"type": "string"},
                            "emotion_label": {"type": "string"},
                            "sentiment_label": {"type": "string"},
                            "confidence": {"type": "number"},
                            "notes": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["turn_id", "emotion_label", "sentiment_label", "confidence", "notes"],
                    },
                },
                "human_summary": {"type": "string"},
            },
            "required": ["speaker_roles", "turn_annotations", "human_summary"],
        },
    }

    prompt = (
        "You analyze a conversation between a human and an AI assistant. "
        "Classify each speaker as human, ai, or unknown. "
        "The output must be conservative: if unsure, return unknown. "
        "Then annotate each turn with a primary perceived emotion and sentiment. "
        "Make the human the primary subject of interpretation and keep the AI as context.\n\n"
        f"Metadata hints: {json.dumps({'human_speaker_hint': metadata.get('human_speaker_hint'), 'ai_speaker_hint': metadata.get('ai_speaker_hint'), 'speaker_role_hints': metadata.get('speaker_role_hints', {})})}\n\n"
        f"Turns:\n{transcript_preview}"
    )

    try:
        with _client() as client:
            response = client.post(
                "/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "Return only valid JSON that matches the provided schema."},
                        {"role": "user", "content": prompt},
                    ],
                    "response_format": {"type": "json_schema", "json_schema": schema},
                },
            )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        parsed = json.loads(content)
    except Exception as error:
        return None, [f"openai_analysis_failed:{error.__class__.__name__}"]

    parsed["model"] = model
    return parsed, []
