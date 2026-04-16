from __future__ import annotations

import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from spectrum_core.datasets import list_dataset_records
from spectrum_core.models import AnalysisMode, DatasetOverview, SessionBundle, SessionJobStatus, SessionRecord, SessionResult, SpeakerRole
from spectrum_core.registry import build_adapter_inventory, metric_catalog
from spectrum_pipeline.importers import CURATED_DATASET_IDS, import_demo_pack, import_materialized_dataset_samples
from spectrum_pipeline.openai_provider import load_local_env
from spectrum_pipeline.service import (
    JOB_STAGE_COUNT,
    JobProgressReporter,
    ProcessSessionOptions,
    SessionStore,
    apply_manual_role_overrides,
    create_session_result,
    run_file,
)
from spectrum_pipeline.store import load_saved_bundle, load_saved_session, list_saved_bundles


class CreateSessionRequest(BaseModel):
    analysis_mode: AnalysisMode = "full"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProcessSessionRequest(BaseModel):
    prototype_noncommercial: bool = False
    enable_comparisons: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class RoleOverrideRequest(BaseModel):
    assignments: dict[str, SpeakerRole] = Field(default_factory=dict)


class DatasetImportRequest(BaseModel):
    dataset_ids: list[str] = Field(default_factory=lambda: list(CURATED_DATASET_IDS))
    samples_per_dataset: int = 2


load_local_env()

app = FastAPI(title="Spectrum API", version="0.2.0")
store = SessionStore()


def _process_job(job_id: str, request: ProcessSessionRequest) -> SessionResult:
    record = store.get_session(job_id)
    original_path = run_file(job_id, "input", record.original_filename or "")
    reporter = JobProgressReporter.from_audio_path(store, job_id, original_path)
    reporter.queue()
    store.set_queued(job_id)
    try:
        store.set_processing(job_id)
        result = create_session_result(
            job_id=job_id,
            analysis_mode=record.analysis_mode,
            original_path=original_path,
            options=ProcessSessionOptions(
                prototype_noncommercial=request.prototype_noncommercial,
                enable_comparisons=request.enable_comparisons,
                metadata=request.metadata,
            ),
            progress=reporter.stage,
        )
    except Exception as error:  # pragma: no cover
        reporter.fail(error)
        store.set_failed(job_id, str(error))
        raise
    reporter.complete()
    store.set_completed(job_id, Path("runs") / job_id / "result.json")
    return result


def _ensure_original_audio(job_id: str) -> tuple[SessionRecord, Path]:
    try:
        record = store.get_session(job_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Session not found") from error
    original_path = run_file(job_id, "input", record.original_filename or "")
    if not original_path.exists():
        raise HTTPException(status_code=400, detail="Audio upload is required before processing.")
    return record, original_path


@app.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/session-records", response_model=list[SessionRecord])
def list_session_records() -> list[SessionRecord]:
    return store.list_sessions()


@app.get("/api/v1/sessions")
def list_sessions() -> list[dict[str, Any]]:
    bundles = list_saved_bundles()
    return [
        {
            "session_id": bundle.session.session_id,
            "title": bundle.session.title,
            "analysis_mode": bundle.session.analysis_mode,
            "source_type": bundle.session.source_type,
            "dataset_id": bundle.session.dataset_id,
            "language": bundle.session.language,
            "duration_sec": bundle.session.duration_sec,
            "usable": bundle.quality.is_usable,
            "quality": bundle.quality.model_dump(mode="json"),
            "top_signal_keys": [signal.key for signal in bundle.signals[:3]],
        }
        for bundle in sorted(bundles, key=lambda item: item.session.session_id)
    ]


@app.post("/api/v1/sessions", response_model=SessionRecord)
def create_session(request: CreateSessionRequest) -> SessionRecord:
    return store.create_session(request.analysis_mode, metadata=request.metadata)


@app.post("/api/v1/sessions/{job_id}/upload", response_model=SessionRecord)
async def upload_audio(job_id: str, file: UploadFile = File(...)) -> SessionRecord:
    try:
        store.get_session(job_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Session not found") from error
    destination = run_file(job_id, "input", file.filename or "upload.bin")
    with destination.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)
    return store.save_upload(job_id, file.filename or destination.name, destination)


@app.post("/api/v1/sessions/{job_id}/process")
def process_session(job_id: str, request: ProcessSessionRequest) -> dict[str, Any]:
    _ensure_original_audio(job_id)
    try:
        result = _process_job(job_id, request)
    except Exception as error:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(error)) from error
    return {"status": "completed", "job_id": job_id, "result_path": f"runs/{job_id}/result.json", "duration_sec": result.duration_sec}


@app.post("/api/v1/sessions/{job_id}/process-async", response_model=SessionJobStatus)
def process_session_async(job_id: str, request: ProcessSessionRequest) -> SessionJobStatus:
    record, _original_path = _ensure_original_audio(job_id)
    existing_status = store.read_job_status(job_id)
    if existing_status and existing_status.status in {"queued", "processing", "completed"}:
        return existing_status
    if record.status in {"queued", "processing", "completed"}:
        status = store.read_job_status(job_id)
        if status is not None:
            return status

    future = store.executor.submit(_process_job, job_id, request)
    store.register_background_job(job_id, future)
    return store.read_job_status(job_id) or SessionJobStatus(
        job_id=job_id,
        status="queued",
        stage_key="normalize",
        stage_label="Normalizing audio",
        stage_index=2,
        stage_count=JOB_STAGE_COUNT,
        percent_complete=10,
        message="Queued for analysis",
        eta_seconds=0,
        started_at=None,
        updated_at=record.updated_at,
    )


@app.get("/api/v1/sessions/{job_id}/status", response_model=SessionJobStatus)
def get_session_status(job_id: str) -> SessionJobStatus:
    try:
        store.get_session(job_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Session not found") from error
    status = store.read_job_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Status not found")
    return status


@app.get("/api/v1/sessions/{job_id}", response_model=SessionRecord)
def get_session_record(job_id: str) -> SessionRecord:
    try:
        return store.get_session(job_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Session not found") from error


@app.get("/api/v1/sessions/{job_id}/results")
def get_results(job_id: str) -> SessionResult:
    try:
        return load_saved_session(job_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Result not found") from error


@app.get("/api/v1/sessions/{job_id}/timeline")
def get_timeline(job_id: str) -> Any:
    path = run_file(job_id, "timeline.json")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Timeline not found")
    return json.loads(path.read_text())


@app.get("/api/v1/sessions/{job_id}/bundle", response_model=SessionBundle)
def get_session_bundle(job_id: str) -> SessionBundle:
    try:
        return load_saved_bundle(job_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Bundle not found") from error


@app.get("/api/v1/sessions/{job_id}/transcript")
def get_session_transcript(job_id: str) -> dict[str, Any]:
    bundle = get_session_bundle(job_id)
    return {
        "transcript": bundle.content.transcript,
        "view_summary": bundle.content.view_summary.model_dump(mode="json"),
        "sentences": [sentence.model_dump(mode="json") for sentence in bundle.content.sentences],
        "tokens": [token.model_dump(mode="json") for token in bundle.content.tokens],
        "words": [word.model_dump(mode="json") for word in bundle.content.words],
    }


@app.get("/api/v1/sessions/{job_id}/profile")
def get_session_profile(job_id: str) -> dict[str, Any]:
    bundle = get_session_bundle(job_id)
    return {
        "profile": bundle.profile.model_dump(mode="json"),
        "profile_display": [field.model_dump(mode="json") for field in bundle.profile_display],
    }


@app.get("/api/v1/sessions/{job_id}/roles")
def get_session_roles(job_id: str) -> dict[str, Any]:
    bundle = get_session_bundle(job_id)
    return bundle.speaker_roles.model_dump(mode="json")


@app.post("/api/v1/sessions/{job_id}/roles", response_model=SessionBundle)
def update_session_roles(job_id: str, request: RoleOverrideRequest) -> SessionBundle:
    try:
        return apply_manual_role_overrides(job_id, request.assignments)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Session not found") from error


@app.get("/api/v1/sessions/{job_id}/diarization")
def get_session_diarization(job_id: str) -> dict[str, Any]:
    bundle = get_session_bundle(job_id)
    return bundle.diarization.model_dump(mode="json")


@app.get("/api/v1/sessions/{job_id}/nonverbal-cues")
def get_session_nonverbal_cues(job_id: str) -> list[dict[str, Any]]:
    bundle = get_session_bundle(job_id)
    return [cue.model_dump(mode="json") for cue in bundle.nonverbal_cues]


@app.get("/api/v1/sessions/{job_id}/prosody")
def get_session_prosody(job_id: str) -> list[dict[str, Any]]:
    bundle = get_session_bundle(job_id)
    return [track.model_dump(mode="json") for track in bundle.prosody_tracks]


@app.get("/api/v1/sessions/{job_id}/waveform")
def get_session_waveform(job_id: str) -> dict[str, Any]:
    bundle = get_session_bundle(job_id)
    return bundle.waveform.model_dump(mode="json")


@app.get("/api/v1/sessions/{job_id}/spectrogram")
def get_session_spectrogram(job_id: str) -> FileResponse:
    bundle = get_session_bundle(job_id)
    image_path = bundle.spectrogram.image_path
    if not image_path:
        raise HTTPException(status_code=404, detail="Spectrogram not available")
    resolved = Path(image_path)
    if not resolved.exists():
        raise HTTPException(status_code=404, detail="Spectrogram not available")
    return FileResponse(resolved, media_type="image/png", filename=resolved.name)


@app.get("/api/v1/sessions/{job_id}/questions")
def get_session_questions(job_id: str) -> list[dict[str, Any]]:
    bundle = get_session_bundle(job_id)
    return [question.model_dump(mode="json") for question in bundle.questions]


@app.get("/api/v1/sessions/{job_id}/signals")
def get_session_signals(job_id: str) -> list[dict[str, Any]]:
    bundle = get_session_bundle(job_id)
    return [signal.model_dump(mode="json") for signal in bundle.signals]


@app.get("/api/v1/sessions/{job_id}/audio")
def get_session_audio(job_id: str) -> FileResponse:
    bundle = get_session_bundle(job_id)
    audio_path = bundle.artifacts.normalized_audio_path or bundle.artifacts.original_audio_path
    if not audio_path:
        raise HTTPException(status_code=404, detail="Audio not available")
    resolved = Path(audio_path)
    if not resolved.exists():
        raise HTTPException(status_code=404, detail="Audio not available")
    media_type = "audio/wav" if resolved.suffix.lower() == ".wav" else "audio/mpeg"
    return FileResponse(resolved, media_type=media_type, filename=resolved.name)


@app.get("/api/v1/datasets")
def list_datasets() -> list[DatasetOverview]:
    return _dataset_overviews()


@app.get("/api/v1/datasets/{dataset_id}")
def get_dataset(dataset_id: str) -> dict[str, Any]:
    overviews = {overview.dataset_id: overview for overview in _dataset_overviews()}
    if dataset_id not in overviews:
        raise HTTPException(status_code=404, detail="Dataset not found")
    bundles = [bundle for bundle in list_saved_bundles() if bundle.session.dataset_id == dataset_id]
    return {
        "dataset": overviews[dataset_id].model_dump(mode="json"),
        "sessions": [
            {
                "session_id": bundle.session.session_id,
                "title": bundle.session.title,
                "quality": bundle.quality.model_dump(mode="json"),
                "signals": [signal.key for signal in bundle.signals[:3]],
            }
            for bundle in bundles
        ],
    }


@app.post("/api/v1/import/demo-pack")
def import_demo_pack_endpoint() -> dict[str, Any]:
    bundles = import_demo_pack()
    return {"imported": len(bundles), "session_ids": [bundle.session.session_id for bundle in bundles]}


@app.post("/api/v1/import/dataset-samples")
def import_dataset_samples_endpoint(request: DatasetImportRequest) -> dict[str, Any]:
    results = import_materialized_dataset_samples(request.dataset_ids, samples_per_dataset=request.samples_per_dataset)
    return {"imported": len(results), "session_ids": [result.job_id for result in results]}


@app.get("/api/v1/compare")
def compare_sessions(session_ids: list[str] = Query(...)) -> dict[str, Any]:
    bundles = [get_session_bundle(session_id) for session_id in session_ids]
    return {
        "sessions": [
            {
                "session_id": bundle.session.session_id,
                "title": bundle.session.title,
                "quality": {
                    "avg_snr_db": bundle.quality.avg_snr_db,
                    "noise_ratio": bundle.quality.noise_ratio,
                    "usable": bundle.quality.is_usable,
                },
                "signals": {signal.key: signal.score for signal in bundle.signals},
                "metrics": {key: metric.value for key, metric in bundle.metrics.items()},
            }
            for bundle in bundles
        ]
    }


@app.get("/api/v1/registry/adapters")
def get_adapter_registry() -> dict[str, Any]:
    return {"adapters": [adapter.model_dump(mode="json") for adapter in build_adapter_inventory()]}


@app.get("/api/v1/registry/metrics")
def get_metric_registry() -> dict[str, Any]:
    return {"metrics": [metric.model_dump(mode="json") for metric in metric_catalog()]}


def _dataset_overviews() -> list[DatasetOverview]:
    bundles = list_saved_bundles()
    by_dataset: dict[str, list[SessionBundle]] = defaultdict(list)
    for bundle in bundles:
        if bundle.session.dataset_id:
            by_dataset[bundle.session.dataset_id].append(bundle)

    overviews: list[DatasetOverview] = []
    for record in list_dataset_records():
        dataset_id = record["id"]
        dataset_bundles = by_dataset.get(dataset_id, [])
        language_labels = sorted(set(record.get("language_labels") or []) | {bundle.session.language for bundle in dataset_bundles if bundle.session.language})
        stage_counter: Counter[str] = Counter()
        for bundle in dataset_bundles:
            for stage in bundle.stage_status:
                if stage.status == "ready":
                    stage_counter[stage.key] += 1
        adapter_keys = sorted(
            {
                adapter.key
                for bundle in dataset_bundles
                for adapter in bundle.diagnostics.adapters
                if adapter.available
            }
        )
        overviews.append(
            DatasetOverview(
                dataset_id=dataset_id,
                title=record["title"],
                access_type=record.get("access_type"),
                source_type="materialized_audio_dataset" if record.get("sample_count") else "manifest_only",
                health_status=record.get("health_status", "manifest_only"),
                health_detail=record.get("health_detail"),
                language_labels=language_labels,
                sample_count=int(record.get("sample_count", 0)),
                imported_count=len(dataset_bundles),
                adapter_coverage=adapter_keys,
                stage_completeness=dict(stage_counter),
            )
        )

    demo_bundles = [bundle for bundle in bundles if bundle.session.source_type == "demo_pack_zip"]
    if demo_bundles:
        overviews.append(
            DatasetOverview(
                dataset_id="voice_analytics_demo_pack",
                title="Voice Analytics Demo Pack",
                access_type="local_synthetic",
                source_type="demo_pack_zip",
                health_status="ready",
                language_labels=sorted({bundle.session.language for bundle in demo_bundles if bundle.session.language}),
                sample_count=len(demo_bundles),
                imported_count=len(demo_bundles),
                adapter_coverage=sorted({adapter.key for bundle in demo_bundles for adapter in bundle.diagnostics.adapters if adapter.available}),
                stage_completeness=dict(Counter(stage.key for bundle in demo_bundles for stage in bundle.stage_status if stage.status == "ready")),
            )
        )

    return sorted(overviews, key=lambda overview: overview.dataset_id)
