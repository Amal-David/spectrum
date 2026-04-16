from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from spectrum_core.models import AnalysisMode, SessionResult

from .service import ProcessSessionOptions, create_session_result


def analyze_audio_file(
    audio_path: str | Path,
    *,
    analysis_mode: AnalysisMode = "full",
    metadata: dict | None = None,
    job_id: str | None = None,
) -> SessionResult:
    resolved = Path(audio_path).resolve()
    return create_session_result(
        job_id=job_id or f"ad-hoc-{uuid4().hex[:10]}",
        analysis_mode=analysis_mode,
        original_path=resolved,
        options=ProcessSessionOptions(metadata=metadata or {}),
    )
