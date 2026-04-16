from __future__ import annotations

import json
from pathlib import Path

from spectrum_core.constants import RUNS_DIR
from spectrum_core.models import SessionBundle, SessionResult

from .service import bundle_from_result, run_file


def result_path_for(job_id: str) -> Path:
    return RUNS_DIR / job_id / "result.json"


def bundle_path_for(job_id: str) -> Path:
    return RUNS_DIR / job_id / "bundle.json"


def load_saved_session(job_id: str) -> SessionResult:
    return SessionResult.model_validate_json(result_path_for(job_id).read_text())


def load_saved_bundle(job_id: str) -> SessionBundle:
    bundle_path = bundle_path_for(job_id)
    if bundle_path.exists():
        return SessionBundle.model_validate_json(bundle_path.read_text())
    result = load_saved_session(job_id)
    metadata_path = run_file(job_id, "metadata.json")
    metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
    return bundle_from_result(result, metadata=metadata)


def save_saved_bundle(job_id: str, bundle: SessionBundle) -> None:
    bundle_path_for(job_id).write_text(bundle.model_dump_json(indent=2) + "\n")


def save_saved_session(job_id: str, result: SessionResult) -> None:
    result_path_for(job_id).write_text(result.model_dump_json(indent=2) + "\n")


def list_saved_sessions() -> list[SessionResult]:
    sessions: list[SessionResult] = []
    if not RUNS_DIR.exists():
        return sessions
    for path in sorted(RUNS_DIR.glob("*/result.json")):
        sessions.append(SessionResult.model_validate(json.loads(path.read_text())))
    return sessions


def list_saved_bundles() -> list[SessionBundle]:
    bundles: list[SessionBundle] = []
    if not RUNS_DIR.exists():
        return bundles
    for bundle_path in sorted(RUNS_DIR.glob("*/bundle.json")):
        bundles.append(SessionBundle.model_validate(json.loads(bundle_path.read_text())))
    if bundles:
        return bundles
    for result_path in sorted(RUNS_DIR.glob("*/result.json")):
        result = SessionResult.model_validate(json.loads(result_path.read_text()))
        metadata_path = result_path.parent / "metadata.json"
        metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
        bundles.append(bundle_from_result(result, metadata=metadata))
    return bundles
