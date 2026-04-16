from __future__ import annotations

import importlib.util
import os
import shutil
from pathlib import Path

from .models import AdapterRuntime, MetricDefinition


def _load_local_env() -> None:
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = value.strip().strip("'").strip('"')


def _token_present() -> bool:
    if os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN"):
        return True
    return any(
        path.exists()
        for path in [
            Path.home() / ".cache" / "huggingface" / "token",
            Path.home() / ".huggingface" / "token",
        ]
    )


def _openai_key_present() -> bool:
    _load_local_env()
    return bool(os.environ.get("OPENAI_API_KEY"))


def _module_available(module_name: str | None) -> bool:
    if not module_name:
        return False
    try:
        return importlib.util.find_spec(module_name) is not None
    except ModuleNotFoundError:
        return False


ADAPTER_SPECS = [
    {
        "key": "ffmpeg",
        "name": "FFmpeg",
        "category": "io",
        "command": "ffmpeg",
        "license_class": "GPL/LGPL mixed binary distribution",
        "enabled_by_default": True,
    },
    {
        "key": "silero_vad",
        "name": "Silero VAD",
        "category": "vad",
        "module": "silero_vad",
        "license_class": "MIT",
        "enabled_by_default": True,
        "warning": "Falls back to ffmpeg silence analysis when the Python package is unavailable.",
    },
    {
        "key": "faster_whisper",
        "name": "faster-whisper",
        "category": "asr",
        "module": "faster_whisper",
        "license_class": "MIT",
        "enabled_by_default": True,
    },
    {
        "key": "openai_audio_analysis",
        "name": "OpenAI Audio Analysis",
        "category": "provider",
        "license_class": "Hosted API",
        "enabled_by_default": True,
        "token_required": True,
        "env_key": "OPENAI_API_KEY",
        "warning": "Requires a local OPENAI_API_KEY for diarized transcription and human-vs-AI role analysis.",
    },
    {
        "key": "speechbrain_commonaccent",
        "name": "SpeechBrain CommonAccent",
        "category": "accent",
        "module": "speechbrain",
        "license_class": "MIT",
        "enabled_by_default": True,
    },
    {
        "key": "indiclid",
        "name": "IndicLID",
        "category": "language_mix",
        "license_class": "MIT-compatible external model",
        "enabled_by_default": True,
        "warning": "No local IndicLID package is wired yet; the scaffold reports availability once an adapter is installed.",
    },
    {
        "key": "librosa",
        "name": "librosa",
        "category": "prosody",
        "module": "librosa",
        "license_class": "ISC",
        "enabled_by_default": True,
    },
    {
        "key": "pyannote",
        "name": "pyannote speaker-diarization-3.1",
        "category": "diarization",
        "module": "pyannote.audio",
        "license_class": "MIT model package with Hugging Face access conditions",
        "enabled_by_default": False,
        "token_required": True,
        "warning": "Requires accepted model conditions and a Hugging Face token.",
    },
    {
        "key": "whisperx",
        "name": "WhisperX",
        "category": "comparison_asr",
        "module": "whisperx",
        "license_class": "BSD/MIT mixed upstream dependencies",
        "enabled_by_default": False,
        "comparison_only": True,
    },
    {
        "key": "yamnet",
        "name": "YAMNet",
        "category": "environment",
        "module": "tensorflow",
        "license_class": "Apache 2.0",
        "enabled_by_default": False,
        "comparison_only": True,
        "warning": "TensorFlow stack is intentionally optional.",
    },
    {
        "key": "panns",
        "name": "PANNs",
        "category": "environment",
        "license_class": "MIT-style research repo",
        "enabled_by_default": False,
        "comparison_only": True,
        "warning": "Bring-your-own installation path for PANNs remains to be completed.",
    },
    {
        "key": "opensmile",
        "name": "openSMILE",
        "category": "comparison_prosody",
        "license_class": "Research/non-commercial caveats apply",
        "enabled_by_default": False,
        "comparison_only": True,
        "warning": "Use only as an optional comparison adapter.",
    },
    {
        "key": "audeering_age_gender",
        "name": "audEERING wav2vec2 age-gender",
        "category": "prototype_profile",
        "license_class": "CC-BY-NC-SA-4.0",
        "enabled_by_default": False,
        "prototype_only": True,
        "warning": "Prototype-only path; do not enable for commercial deployment.",
    },
    {
        "key": "ecapa_fine_accent",
        "name": "ECAPA fine accent head",
        "category": "accent",
        "license_class": "Project-owned training scaffold",
        "enabled_by_default": False,
        "warning": "Training and checkpoint materialization are scaffolded but not yet populated.",
    },
]


def build_adapter_inventory() -> list[AdapterRuntime]:
    token_present = _token_present()
    openai_present = _openai_key_present()
    inventory: list[AdapterRuntime] = []
    for spec in ADAPTER_SPECS:
        available = False
        if command := spec.get("command"):
            available = shutil.which(command) is not None
        elif module := spec.get("module"):
            available = _module_available(module)
        elif spec.get("env_key") == "OPENAI_API_KEY":
            available = openai_present
        inventory.append(
            AdapterRuntime(
                key=spec["key"],
                name=spec["name"],
                category=spec["category"],
                available=available,
                enabled_by_default=spec["enabled_by_default"],
                token_required=spec.get("token_required", False),
                token_present=openai_present if spec.get("env_key") == "OPENAI_API_KEY" else (token_present if spec.get("token_required") else False),
                comparison_only=spec.get("comparison_only", False),
                prototype_only=spec.get("prototype_only", False),
                license_class=spec["license_class"],
                warning=spec.get("warning"),
            )
        )
    return inventory


def metric_catalog() -> list[MetricDefinition]:
    return [
        MetricDefinition(
            key="speech_ratio",
            label="Speech Ratio",
            unit="ratio",
            description="Share of the clip that is treated as non-silent speech after preprocessing.",
        ),
        MetricDefinition(
            key="noise_score",
            label="Noise Score",
            unit="ratio",
            description="Heuristic noise estimate derived from silence burden, clipping, and dynamic range.",
        ),
        MetricDefinition(
            key="noise_ratio",
            label="Noise Ratio",
            unit="ratio",
            description="Environmental contamination estimate used to discount question and signal interpretation.",
        ),
        MetricDefinition(
            key="avg_snr_db",
            label="Average SNR",
            unit="dB",
            description="Approximate signal-to-noise ratio estimate for the normalized waveform.",
        ),
        MetricDefinition(
            key="speech_rate_wpm",
            label="Speech Rate",
            unit="wpm",
            description="Estimated words per minute using the transcript and detected speech duration.",
        ),
        MetricDefinition(
            key="talk_ratio",
            label="Talk Ratio",
            unit="ratio",
            description="Share of total talking time attributed to a speaker.",
        ),
        MetricDefinition(
            key="avg_turn_ms",
            label="Average Turn Length",
            unit="ms",
            description="Average turn duration for a speaker or the dominant speaker fallback.",
        ),
        MetricDefinition(
            key="interruption_count",
            label="Interruption Count",
            unit="count",
            description="Count of interruption events attributed to the session.",
        ),
        MetricDefinition(
            key="overlap_ms",
            label="Overlap",
            unit="ms",
            description="Total duration of overlapping speech windows when diarization is enabled.",
        ),
        MetricDefinition(
            key="response_latency_ms",
            label="Response Latency",
            unit="ms",
            description="Latency between the end of one turn and the start of the next turn.",
        ),
        MetricDefinition(
            key="hesitation_score",
            label="Hesitation Score",
            unit="score",
            description="Blended hesitation proxy from latency, fillers, and uncertainty markers across derived question moments.",
        ),
    ]
