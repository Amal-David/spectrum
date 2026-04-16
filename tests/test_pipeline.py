from __future__ import annotations

import json
import math
import shutil
import wave
from pathlib import Path
from typing import Any

import numpy as np

from spectrum_api.cli import main as spectrum_cli_main
from spectrum_pipeline.importers import import_demo_pack
from spectrum_pipeline.analyzer import analyze_audio_file
from spectrum_pipeline.benchmarks import benchmark_results
from spectrum_pipeline.cohorts import cohort_summary
from spectrum_core.models import ProviderDecision
from spectrum_pipeline.service import JOB_STAGE_COUNT, JobProgressReporter, SessionStore, TranscriptionOutcome, apply_manual_role_overrides


def _write_test_wav(path: Path) -> None:
    sample_rate = 16000
    burst_1 = 0.22 * np.sin(2 * math.pi * 180 * np.linspace(0, 1.0, sample_rate, endpoint=False))
    pause = np.zeros(int(sample_rate * 1.4), dtype=np.float32)
    burst_2 = 0.35 * np.sin(2 * math.pi * 250 * np.linspace(0, 1.0, sample_rate, endpoint=False))
    samples = np.concatenate([burst_1, pause, burst_2]).astype(np.float32)
    pcm = np.clip(samples * 32767, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())


def test_analyzer_emits_profile_metrics_and_events(tmp_path: Path) -> None:
    audio_path = tmp_path / "synthetic.wav"
    _write_test_wav(audio_path)

    result = analyze_audio_file(
        audio_path,
        analysis_mode="full",
        metadata={
            "transcript_hint": "hello there this is a synthetic conversation sample",
            "dialogue_turns": ["hello there", "this is a synthetic conversation sample"],
            "speaker_sequence": ["speaker_0", "speaker_1"],
            "speaker_hints": {"speaker_0": {"voice_presentation": "female", "age": 32}},
        },
        job_id="test-synthetic-pipeline",
    )

    assert result.duration_sec > 2.0
    assert "speech_ratio" in result.metrics
    assert result.profile.voice_presentation.label == "female"
    assert result.turns
    assert result.events
    assert (Path("runs") / "test-synthetic-pipeline" / "bundle.json").exists()
    bundle_payload = json.loads((Path("runs") / "test-synthetic-pipeline" / "bundle.json").read_text())
    assert "questions" in bundle_payload
    assert "signals" in bundle_payload
    assert bundle_payload["profile_display"]
    assert "profile_coverage" in bundle_payload
    assert "hidden_fields" in bundle_payload["profile_coverage"]
    assert bundle_payload["content"]["sentences"]
    assert bundle_payload["content"]["view_summary"]["sentence_count"] >= 1
    assert bundle_payload["diarization"]["readiness_state"] == "fallback"
    assert bundle_payload["diarization"]["segments"]
    assert bundle_payload["waveform"]["bucket_count"] > 0
    assert bundle_payload["spectrogram"]["readiness_state"] in {"ready", "fallback"}
    assert bundle_payload["prosody_tracks"]
    assert bundle_payload["timeline_tracks"]
    voice_field = next(field for field in bundle_payload["profile_display"] if field["key"] == "voice_presentation")
    assert voice_field["display_state"] == "hidden"
    for track in bundle_payload["prosody_tracks"]:
        timestamps = [sample["timestamp_ms"] for sample in track["samples"]]
        assert timestamps == sorted(timestamps)
        assert all(0 <= timestamp <= round(result.duration_sec * 1000) for timestamp in timestamps)


def test_cli_analyze_creates_bundle(monkeypatch: Any, tmp_path: Path) -> None:
    audio_path = tmp_path / "cli.wav"
    _write_test_wav(audio_path)
    opened_urls: list[str] = []
    job_id = "cli-quickstart-test"
    run_root = Path("runs") / job_id
    if run_root.exists():
        shutil.rmtree(run_root)

    monkeypatch.setattr("spectrum_api.cli.uuid.uuid4", lambda: job_id)
    monkeypatch.setattr("spectrum_api.cli.webbrowser.open", lambda url: opened_urls.append(url))

    exit_code = spectrum_cli_main(["analyze", str(audio_path), "--dashboard-url", "http://127.0.0.1:3000", "--open"])

    assert exit_code == 0
    assert (run_root / "bundle.json").exists()
    assert opened_urls == [f"http://127.0.0.1:3000/sessions/{job_id}"]


def test_benchmark_sentence_labels_drive_transcript_affect(tmp_path: Path) -> None:
    audio_path = tmp_path / "benchmark.wav"
    _write_test_wav(audio_path)

    analyze_audio_file(
        audio_path,
        analysis_mode="full",
        metadata={
            "transcript_hint": "I am happy to help.",
            "speaker_segments": [
                {
                    "turn_id": "benchmark-turn-0",
                    "speaker_id": "speaker_0",
                    "start_ms": 0,
                    "end_ms": 1800,
                    "text": "I am happy to help.",
                }
            ],
            "sentence_emotion_labels": [
                {
                    "benchmark_id": "meld:1:1",
                    "text": "I am happy to help.",
                    "emotion_label": "joy",
                    "sentiment_label": "positive",
                    "start_ms": 0,
                    "end_ms": 1800,
                    "confidence": 0.99,
                }
            ],
        },
        job_id="test-benchmark-transcript-affect",
    )

    bundle_payload = json.loads((Path("runs") / "test-benchmark-transcript-affect" / "bundle.json").read_text())
    sentence = bundle_payload["content"]["sentences"][0]
    assert sentence["emotion_label"] == "joy"
    assert sentence["source"] == "benchmark_label"
    assert bundle_payload["content"]["tokens"]


def test_benchmark_nonverbal_cues_map_into_visible_bundle_artifacts(tmp_path: Path) -> None:
    audio_path = tmp_path / "benchmark-cues.wav"
    _write_test_wav(audio_path)

    analyze_audio_file(
        audio_path,
        analysis_mode="full",
        metadata={
            "dataset_id": "ami_corpus",
            "source_type": "materialized_audio_dataset",
            "benchmark_diarization": True,
            "speaker_segments": [
                {
                    "turn_id": "ami-turn-0",
                    "speaker_id": "speaker_a",
                    "label": "Speaker A",
                    "start_ms": 0,
                    "end_ms": 1600,
                    "text": "that is actually pretty funny",
                }
            ],
            "benchmark_nonverbal_cues": [
                {
                    "benchmark_id": "ami:ES2002a:laugh",
                    "speaker_id": "speaker_a",
                    "type": "laugh",
                    "family": "vocal_sound",
                    "label": "laugh",
                    "start_ms": 640,
                    "end_ms": 1120,
                    "confidence": 0.99,
                }
            ],
        },
        job_id="test-benchmark-cues",
    )

    bundle_payload = json.loads((Path("runs") / "test-benchmark-cues" / "bundle.json").read_text())
    assert bundle_payload["diarization"]["readiness_state"] == "ready"
    laugh_cue = next(cue for cue in bundle_payload["nonverbal_cues"] if cue["type"] == "laugh")
    assert laugh_cue["speaker_id"] == "speaker_a"
    assert laugh_cue["source"] == "benchmark_label"
    assert any(track["track_id"] == "nonverbal" for track in bundle_payload["timeline_tracks"])


def test_uploaded_sessions_gate_speaker_attribution_without_strong_diarization(tmp_path: Path) -> None:
    audio_path = tmp_path / "upload-gated.wav"
    _write_test_wav(audio_path)

    analyze_audio_file(
        audio_path,
        analysis_mode="full",
        metadata={
            "transcript_hint": "hello there",
            "benchmark_nonverbal_cues": [
                {
                    "benchmark_id": "demo:laugh",
                    "speaker_id": "speaker_0",
                    "type": "laugh",
                    "family": "vocal_sound",
                    "label": "laugh",
                    "start_ms": 400,
                    "end_ms": 900,
                    "confidence": 0.98,
                }
            ],
        },
        job_id="test-upload-gated-cues",
    )

    bundle_payload = json.loads((Path("runs") / "test-upload-gated-cues" / "bundle.json").read_text())
    assert bundle_payload["diarization"]["readiness_state"] == "fallback"
    assert bundle_payload["diarization"]["segments"]
    laugh_cue = next(cue for cue in bundle_payload["nonverbal_cues"] if cue["type"] == "laugh")
    assert laugh_cue["display_state"] == "muted"
    assert laugh_cue["speaker_id"] is None
    assert laugh_cue["attribution_state"] == "unassigned"
    assert "speaker_attribution_blocked" in laugh_cue["explainability_mask"]
    speaker_track = next(track for track in bundle_payload["timeline_tracks"] if track["track_id"] == "speaker-lanes")
    assert speaker_track["status"] == "fallback"
    assert bundle_payload["session"]["readiness_tier"] == "partial"


def test_textual_nonverbal_cues_surface_for_uploaded_audio(tmp_path: Path) -> None:
    audio_path = tmp_path / "upload-textual-cues.wav"
    _write_test_wav(audio_path)

    analyze_audio_file(
        audio_path,
        analysis_mode="full",
        metadata={
            "transcript_hint": "haha yes okay i can help with that",
            "dialogue_turns": ["haha", "okay", "okay i can help with that"],
            "speaker_sequence": ["speaker_0", "speaker_1", "speaker_1"],
        },
        job_id="test-upload-textual-cues",
    )

    bundle_payload = json.loads((Path("runs") / "test-upload-textual-cues" / "bundle.json").read_text())
    cue_types = {cue["type"] for cue in bundle_payload["nonverbal_cues"]}
    assert "laugh" in cue_types
    assert "backchannel" in cue_types


def test_openai_role_hints_drive_human_focused_bundle(monkeypatch: Any, tmp_path: Path) -> None:
    audio_path = tmp_path / "openai-human-ai.wav"
    _write_test_wav(audio_path)

    monkeypatch.setattr("spectrum_pipeline.service.openai_enabled", lambda: True)
    monkeypatch.setattr(
        "spectrum_pipeline.service.transcribe_audio_with_openai",
        lambda _audio_path: (
            {
                "transcript": "Hello and welcome. Hi, I need help with pricing. I am an AI assistant and can help.",
                "words": [
                    {"word": "Hello", "start": 0.0, "end": 0.2, "speaker": 1, "confidence": 0.9},
                    {"word": "welcome", "start": 0.2, "end": 0.5, "speaker": 1, "confidence": 0.9},
                    {"word": "Hi", "start": 0.55, "end": 0.7, "speaker": 0, "confidence": 0.88},
                    {"word": "pricing", "start": 0.7, "end": 1.0, "speaker": 0, "confidence": 0.88},
                    {"word": "assistant", "start": 1.1, "end": 1.5, "speaker": 1, "confidence": 0.87},
                ],
                "segments": [],
            },
            [],
        ),
    )
    monkeypatch.setattr(
        "spectrum_pipeline.service.analyze_conversation_with_openai",
        lambda _transcript, turns, _metadata: (
            {
                "speaker_roles": [
                    {"speaker_id": "speaker_0", "speaker_role": "human", "confidence": 0.95, "notes": ["pricing request"]},
                    {"speaker_id": "speaker_1", "speaker_role": "ai", "confidence": 0.94, "notes": ["assistant phrasing"]},
                ],
                "turn_annotations": [
                    {
                        "turn_id": turns[0]["turn_id"],
                        "emotion_label": "calm",
                        "sentiment_label": "neutral",
                        "confidence": 0.73,
                        "notes": ["assistant opening"],
                    },
                    {
                        "turn_id": turns[1]["turn_id"],
                        "emotion_label": "fear",
                        "sentiment_label": "negative",
                        "confidence": 0.82,
                        "notes": ["human pricing concern"],
                    },
                ],
                "human_summary": "The human sounds uncertain about pricing.",
            },
            [],
        ),
    )

    analyze_audio_file(audio_path, analysis_mode="full", metadata={"source_type": "direct_audio_file", "provider_override": "openai"}, job_id="test-openai-human-ai")

    bundle_payload = json.loads((Path("runs") / "test-openai-human-ai" / "bundle.json").read_text())
    assert bundle_payload["speaker_roles"]["primary_human_speaker_id"] == "speaker_0"
    assert bundle_payload["speaker_roles"]["primary_ai_speaker_id"] == "speaker_1"
    human_sentence = next(sentence for sentence in bundle_payload["content"]["sentences"] if sentence["speaker_role"] == "human")
    assert human_sentence["source"] == "model"
    assert any(signal["key"] == "hesitation" for signal in bundle_payload["signals"])
    assert all("evidence_class" in signal for signal in bundle_payload["signals"])
    assert bundle_payload["metrics"]["talk_ratio"]["value"] <= 1


def test_local_asr_is_default_and_records_readiness(monkeypatch: Any, tmp_path: Path) -> None:
    audio_path = tmp_path / "local-asr-default.wav"
    _write_test_wav(audio_path)

    monkeypatch.setattr(
        "spectrum_pipeline.service.maybe_transcribe",
        lambda job_id, audio_path, transcript_hint=None: TranscriptionOutcome(
            transcript="hello there from the local whisper path",
            words=[{"word": "hello", "start_ms": 0, "end_ms": 220, "confidence": 0.91, "source": "model"}],
            warnings=[],
            provider=ProviderDecision(kind="transcription", provider_key="faster_whisper", used=True, cached=False, status="ready", notes=[]),
        ),
    )
    monkeypatch.setattr("spectrum_pipeline.service.openai_enabled", lambda: False)

    analyze_audio_file(audio_path, analysis_mode="full", metadata={"source_type": "direct_audio_file"}, job_id="test-local-asr-default")

    bundle_payload = json.loads((Path("runs") / "test-local-asr-default" / "bundle.json").read_text())
    assert bundle_payload["content"]["transcript"] == "hello there from the local whisper path"
    assert bundle_payload["content"]["words"]
    assert bundle_payload["session"]["readiness_tier"] in {"partial", "transcript_only"}
    provider_keys = [item["provider_key"] for item in bundle_payload["diagnostics"]["provider_decisions"]]
    assert provider_keys[0] == "faster_whisper"
    assert {"alignment", "nonverbal_cues", "profile"}.issubset({item["kind"] for item in bundle_payload["diagnostics"]["provider_decisions"]})
    assert "oss_first_local_pipeline" in bundle_payload["diagnostics"]["fallback_logic"]


def test_cohort_summary_filters_by_readiness_tier(tmp_path: Path) -> None:
    audio_path = tmp_path / "readiness-filter.wav"
    _write_test_wav(audio_path)

    analyze_audio_file(
        audio_path,
        analysis_mode="full",
        metadata={"transcript_hint": "hello there from readiness filter"},
        job_id="test-readiness-filter",
    )

    bundle_payload = json.loads((Path("runs") / "test-readiness-filter" / "bundle.json").read_text())
    from spectrum_core.models import CohortFilters, SessionBundle  # local import to avoid widening top imports

    summary = cohort_summary(
        [SessionBundle.model_validate(bundle_payload)],
        CohortFilters(readiness_tiers=[bundle_payload["session"]["readiness_tier"]]),
    )
    assert len(summary.runs) == 1
    empty = cohort_summary([SessionBundle.model_validate(bundle_payload)], CohortFilters(readiness_tiers=["blocked"]))
    assert not empty.runs


def test_benchmark_results_compare_against_previous_snapshot() -> None:
    audio_path = Path("runs") / "test-benchmark-regression.wav"
    _write_test_wav(audio_path)
    analyze_audio_file(
        audio_path,
        analysis_mode="full",
        metadata={
            "dataset_id": "meld",
            "source_type": "materialized_audio_dataset",
            "transcript_hint": "I am happy to help.",
            "speaker_segments": [
                {
                    "turn_id": "benchmark-turn-0",
                    "speaker_id": "speaker_0",
                    "start_ms": 0,
                    "end_ms": 1800,
                    "text": "I am happy to help.",
                }
            ],
            "sentence_emotion_labels": [
                {
                    "benchmark_id": "meld:1:1",
                    "text": "I am happy to help.",
                    "emotion_label": "joy",
                    "sentiment_label": "positive",
                    "start_ms": 0,
                    "end_ms": 1800,
                    "confidence": 0.99,
                }
            ],
        },
        job_id="test-benchmark-regression",
    )
    from spectrum_core.models import SessionBundle  # local import to avoid widening top imports

    bundle_payload = json.loads((Path("runs") / "test-benchmark-regression" / "bundle.json").read_text())
    bundles = [SessionBundle.model_validate(bundle_payload)]
    current = benchmark_results(bundles)
    previous = [
        result.model_copy(
            update={
                "metrics": [
                    metric.model_copy(update={"value": metric.value + 0.2 if metric.key == "der" else max(0.0, metric.value - 0.2)})
                    for metric in result.metrics
                ]
            }
        )
        for result in current
    ]
    compared = benchmark_results(bundles, previous_results=previous)
    assert any(metric.delta is not None for result in compared for metric in result.metrics)
    assert all(result.support_level in {"benchmark_backed", "model_backed", "heuristic_backed", "metadata_backed"} for result in compared)


def test_manual_role_override_rebuilds_bundle(tmp_path: Path) -> None:
    audio_path = tmp_path / "manual-override.wav"
    _write_test_wav(audio_path)

    analyze_audio_file(
        audio_path,
        analysis_mode="full",
        metadata={
            "transcript_hint": "Hello there. Hi I need help.",
            "dialogue_turns": ["Hello there.", "Hi I need help."],
            "speaker_sequence": ["speaker_0", "speaker_1"],
            "speaker_role_hints": {"speaker_0": "ai", "speaker_1": "human"},
        },
        job_id="test-manual-role-override",
    )

    bundle = apply_manual_role_overrides("test-manual-role-override", {"speaker_0": "human", "speaker_1": "ai"})
    assert bundle.speaker_roles.primary_human_speaker_id == "speaker_0"
    assert bundle.speaker_roles.primary_ai_speaker_id == "speaker_1"
    assert any(turn.speaker_role == "human" for turn in bundle.turns)


def test_demo_pack_import_materializes_bundles() -> None:
    bundles = import_demo_pack()
    assert len(bundles) == 3
    support_bundle = next(bundle for bundle in bundles if bundle.session.session_id == "sess_support_001")
    assert support_bundle.questions
    assert any(signal.key == "friction" for signal in support_bundle.signals)


def test_job_status_history_is_monotonic(tmp_path: Path) -> None:
    audio_path = tmp_path / "job-status.wav"
    _write_test_wav(audio_path)

    store = SessionStore()
    record = store.create_session("full", metadata={"title": "Status check"})
    store.save_upload(record.job_id, audio_path.name, audio_path)

    reporter = JobProgressReporter.from_audio_path(store, record.job_id, audio_path)
    reporter.queue()
    reporter.stage("normalize")
    reporter.stage("quality")
    reporter.stage("structure")

    status = store.read_job_status(record.job_id)
    assert status is not None
    percents = [entry.percent_complete for entry in status.history] + [status.percent_complete]
    assert percents == sorted(percents)
    assert status.eta_seconds >= 0
    assert any(entry.stage_key == "upload" for entry in status.history)


def test_interrupted_processing_status_is_marked_failed() -> None:
    store = SessionStore()
    record = store.create_session("full", metadata={"title": "Interrupted job"})
    store.write_job_status(
        record.job_id,
        status="processing",
        stage_key="content",
        stage_label="Extracting transcript and content signals",
        stage_index=5,
        stage_count=JOB_STAGE_COUNT,
        percent_complete=55,
        message="Extracting transcript and content signals",
        eta_seconds=22,
        started_at="2026-04-16T00:00:00Z",
        error=None,
    )

    restarted_store = SessionStore()
    status = restarted_store.read_job_status(record.job_id)
    assert status is not None
    assert status.status == "failed"
    assert "interrupted" in (status.error or "")
