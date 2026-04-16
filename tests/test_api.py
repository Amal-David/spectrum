from __future__ import annotations

import math
import time
import wave
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

from spectrum_api.main import app


def _write_test_wav(path: Path) -> None:
    sample_rate = 16000
    tone = (0.2 * np.sin(2 * math.pi * 220 * np.linspace(0, 1.0, sample_rate, endpoint=False))).astype(np.float32)
    pcm = np.clip(tone * 32767, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())


def _wait_for_terminal_status(client: TestClient, job_id: str, timeout: float = 20.0) -> dict:
    deadline = time.time() + timeout
    latest: dict = {}
    while time.time() < deadline:
        response = client.get(f"/api/v1/sessions/{job_id}/status")
        assert response.status_code == 200
        latest = response.json()
        if latest["status"] in {"completed", "failed"}:
            return latest
        time.sleep(0.2)
    raise AssertionError(f"Job {job_id} did not reach a terminal state in time. Last status: {latest}")


def test_session_create_upload_and_process_flow(tmp_path: Path) -> None:
    audio_path = tmp_path / "api-audio.wav"
    _write_test_wav(audio_path)

    client = TestClient(app)
    created = client.post("/api/v1/sessions", json={"analysis_mode": "voice_profile", "metadata": {"language_hint": "english"}})
    assert created.status_code == 200
    job_id = created.json()["job_id"]

    with audio_path.open("rb") as handle:
        uploaded = client.post(f"/api/v1/sessions/{job_id}/upload", files={"file": ("api-audio.wav", handle, "audio/wav")})
    assert uploaded.status_code == 200

    processed = client.post(
        f"/api/v1/sessions/{job_id}/process",
        json={"metadata": {"transcript_hint": "hello there from spectrum", "voice_presentation_hint": "male"}},
    )
    assert processed.status_code == 200

    result = client.get(f"/api/v1/sessions/{job_id}/results")
    assert result.status_code == 200
    payload = result.json()
    assert payload["profile"]["voice_presentation"]["label"] == "male"
    assert payload["transcript"] == "hello there from spectrum"

    bundle = client.get(f"/api/v1/sessions/{job_id}/bundle")
    assert bundle.status_code == 200
    bundle_payload = bundle.json()
    assert bundle_payload["session"]["session_id"] == job_id
    assert "questions" in bundle_payload
    assert "signals" in bundle_payload
    assert bundle_payload["profile_display"]
    assert bundle_payload["content"]["sentences"]

    questions = client.get(f"/api/v1/sessions/{job_id}/questions")
    assert questions.status_code == 200

    signals = client.get(f"/api/v1/sessions/{job_id}/signals")
    assert signals.status_code == 200

    transcript = client.get(f"/api/v1/sessions/{job_id}/transcript")
    assert transcript.status_code == 200
    assert transcript.json()["sentences"]

    profile = client.get(f"/api/v1/sessions/{job_id}/profile")
    assert profile.status_code == 200
    assert profile.json()["profile_display"]

    roles = client.get(f"/api/v1/sessions/{job_id}/roles")
    assert roles.status_code == 200
    assert "assignments" in roles.json()

    diarization = client.get(f"/api/v1/sessions/{job_id}/diarization")
    assert diarization.status_code == 200
    assert "readiness_state" in diarization.json()

    nonverbal = client.get(f"/api/v1/sessions/{job_id}/nonverbal-cues")
    assert nonverbal.status_code == 200

    prosody = client.get(f"/api/v1/sessions/{job_id}/prosody")
    assert prosody.status_code == 200
    assert isinstance(prosody.json(), list)

    waveform = client.get(f"/api/v1/sessions/{job_id}/waveform")
    assert waveform.status_code == 200
    assert waveform.json()["bucket_count"] > 0

    spectrogram = client.get(f"/api/v1/sessions/{job_id}/spectrogram")
    assert spectrogram.status_code == 200
    assert spectrogram.headers["content-type"] == "image/png"


def test_async_process_reports_status_and_completes(tmp_path: Path) -> None:
    audio_path = tmp_path / "async-audio.wav"
    _write_test_wav(audio_path)

    client = TestClient(app)
    created = client.post("/api/v1/sessions", json={"analysis_mode": "full", "metadata": {"language_hint": "english"}})
    assert created.status_code == 200
    job_id = created.json()["job_id"]

    with audio_path.open("rb") as handle:
        uploaded = client.post(f"/api/v1/sessions/{job_id}/upload", files={"file": ("async-audio.wav", handle, "audio/wav")})
    assert uploaded.status_code == 200

    started = client.post(
        f"/api/v1/sessions/{job_id}/process-async",
        json={"metadata": {"transcript_hint": "hello there from async spectrum"}},
    )
    assert started.status_code == 200

    terminal = _wait_for_terminal_status(client, job_id)
    assert terminal["status"] == "completed"
    assert terminal["percent_complete"] == 100
    assert terminal["history"]

    bundle = client.get(f"/api/v1/sessions/{job_id}/bundle")
    assert bundle.status_code == 200
    assert bundle.json()["content"]["transcript"] == "hello there from async spectrum"
    assert bundle.json()["timeline_tracks"]


def test_role_override_endpoint_updates_bundle(tmp_path: Path) -> None:
    audio_path = tmp_path / "roles-api.wav"
    _write_test_wav(audio_path)

    client = TestClient(app)
    created = client.post("/api/v1/sessions", json={"analysis_mode": "full", "metadata": {"language_hint": "english"}})
    job_id = created.json()["job_id"]

    with audio_path.open("rb") as handle:
        uploaded = client.post(f"/api/v1/sessions/{job_id}/upload", files={"file": ("roles-api.wav", handle, "audio/wav")})
    assert uploaded.status_code == 200

    processed = client.post(
        f"/api/v1/sessions/{job_id}/process",
        json={
            "metadata": {
                "transcript_hint": "hello there. i need help now.",
                "dialogue_turns": ["hello there.", "i need help now."],
                "speaker_sequence": ["speaker_0", "speaker_1"],
                "speaker_role_hints": {"speaker_0": "ai", "speaker_1": "human"},
            }
        },
    )
    assert processed.status_code == 200

    updated = client.post(f"/api/v1/sessions/{job_id}/roles", json={"assignments": {"speaker_0": "human", "speaker_1": "ai"}})
    assert updated.status_code == 200
    payload = updated.json()
    assert payload["speaker_roles"]["primary_human_speaker_id"] == "speaker_0"
    assert payload["speaker_roles"]["primary_ai_speaker_id"] == "speaker_1"


def test_cohort_and_benchmark_endpoints_respond(tmp_path: Path) -> None:
    audio_path = tmp_path / "cohort-api.wav"
    _write_test_wav(audio_path)

    client = TestClient(app)
    created = client.post("/api/v1/sessions", json={"analysis_mode": "full", "metadata": {"language_hint": "english", "project": "demo"}})
    job_id = created.json()["job_id"]

    with audio_path.open("rb") as handle:
        uploaded = client.post(f"/api/v1/sessions/{job_id}/upload", files={"file": ("cohort-api.wav", handle, "audio/wav")})
    assert uploaded.status_code == 200

    processed = client.post(
        f"/api/v1/sessions/{job_id}/process",
        json={"metadata": {"transcript_hint": "hello there from cohort analytics", "language_hint": "english"}},
    )
    assert processed.status_code == 200

    summary = client.get("/api/v1/cohorts/summary")
    assert summary.status_code == 200
    assert summary.json()["kpis"]

    trends = client.get("/api/v1/cohorts/trends")
    assert trends.status_code == 200
    assert isinstance(trends.json(), list)

    distributions = client.get("/api/v1/cohorts/distributions")
    assert distributions.status_code == 200
    assert isinstance(distributions.json(), list)

    sessions = client.get("/api/v1/cohorts/sessions")
    assert sessions.status_code == 200
    assert any(item["session_id"] == job_id for item in sessions.json())

    benchmarks = client.get("/api/v1/benchmarks")
    assert benchmarks.status_code == 200
    payload = benchmarks.json()
    assert payload["registry"]
    assert payload["results"]
