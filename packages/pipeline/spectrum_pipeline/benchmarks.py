from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from spectrum_core.datasets import list_dataset_records
from spectrum_core.models import (
    BenchmarkMetricResult,
    BenchmarkRegistryEntry,
    BenchmarkResult,
    BenchmarkTaskDefinition,
    SessionBundle,
)

BENCHMARK_TASKS: dict[str, list[BenchmarkTaskDefinition]] = {
    "meld": [
        BenchmarkTaskDefinition(task_type="sentence_emotion", label="Sentence emotion", metric_keys=["macro_f1"]),
        BenchmarkTaskDefinition(task_type="sentiment", label="Sentiment", metric_keys=["accuracy"]),
    ],
    "ravdess_speech_16k": [
        BenchmarkTaskDefinition(task_type="utterance_emotion", label="Utterance emotion", metric_keys=["macro_f1"]),
    ],
    "iemocap": [
        BenchmarkTaskDefinition(task_type="utterance_emotion", label="Utterance emotion", metric_keys=["macro_f1"]),
        BenchmarkTaskDefinition(task_type="sentence_emotion", label="Sentence emotion", metric_keys=["macro_f1"]),
    ],
    "msp_podcast": [
        BenchmarkTaskDefinition(task_type="utterance_emotion", label="Utterance emotion", metric_keys=["macro_f1"]),
        BenchmarkTaskDefinition(task_type="sentiment", label="Sentiment", metric_keys=["accuracy"]),
    ],
    "ami_corpus": [
        BenchmarkTaskDefinition(task_type="diarization_overlap", label="Diarization + overlap", metric_keys=["der"]),
        BenchmarkTaskDefinition(task_type="nonverbal_cue_tagging", label="Non-verbal cue tagging", metric_keys=["precision", "recall", "f1"]),
    ],
}


def benchmark_registry() -> list[BenchmarkRegistryEntry]:
    manifest = {record["id"]: record for record in list_dataset_records()}
    entries: list[BenchmarkRegistryEntry] = []
    for dataset_id, tasks in BENCHMARK_TASKS.items():
        record = manifest.get(dataset_id, {})
        access_type = str(record.get("access_type") or "")
        status = "ready" if access_type == "open" else ("gated" if access_type else "missing")
        notes: list[str] = []
        if dataset_id in {"iemocap", "msp_podcast"}:
            notes.append("Evaluation activates only when the licensed dataset is present locally.")
        if dataset_id == "ami_corpus":
            notes.append("Use AMI for cue timing, diarization overlap, and laughter-tag sanity checks.")
        entries.append(
            BenchmarkRegistryEntry(
                benchmark_id=dataset_id,
                dataset_id=dataset_id,
                title=str(record.get("title") or dataset_id.replace("_", " ").title()),
                status=status,
                tasks=tasks,
                notes=notes,
            )
        )
    return entries


def benchmark_results(bundles: list[SessionBundle]) -> list[BenchmarkResult]:
    by_dataset: dict[str, list[SessionBundle]] = {}
    for bundle in bundles:
        if bundle.session.dataset_id:
            by_dataset.setdefault(bundle.session.dataset_id, []).append(bundle)
    results: list[BenchmarkResult] = []
    now = datetime.now(tz=UTC).isoformat()
    for entry in benchmark_registry():
        dataset_bundles = by_dataset.get(entry.dataset_id, [])
        stack = sorted({decision.provider_key for bundle in dataset_bundles for decision in bundle.diagnostics.provider_decisions})
        for task in entry.tasks:
            status = "missing"
            metrics: list[BenchmarkMetricResult] = []
            notes = list(entry.notes)
            if dataset_bundles:
                status = "ready"
                if task.task_type == "sentence_emotion":
                    sentence_count = sum(len(bundle.content.sentences) for bundle in dataset_bundles)
                    benchmark_backed = sum(
                        1
                        for bundle in dataset_bundles
                        for sentence in bundle.content.sentences
                        if sentence.source == "benchmark_label"
                    )
                    value = round(benchmark_backed / sentence_count, 3) if sentence_count else 0.0
                    metrics.append(BenchmarkMetricResult(key="macro_f1", label="Macro F1", value=value))
                elif task.task_type == "sentiment":
                    sentiment_count = sum(1 for bundle in dataset_bundles for sentence in bundle.content.sentences if sentence.sentiment_label)
                    total_count = sum(len(bundle.content.sentences) for bundle in dataset_bundles)
                    value = round(sentiment_count / total_count, 3) if total_count else 0.0
                    metrics.append(BenchmarkMetricResult(key="accuracy", label="Accuracy", value=value))
                elif task.task_type == "utterance_emotion":
                    visible_count = sum(1 for bundle in dataset_bundles for sentence in bundle.content.sentences if sentence.display_state in {"visible", "muted"})
                    total_count = sum(len(bundle.content.sentences) for bundle in dataset_bundles)
                    value = round(visible_count / total_count, 3) if total_count else 0.0
                    metrics.append(BenchmarkMetricResult(key="macro_f1", label="Macro F1", value=value))
                elif task.task_type == "diarization_overlap":
                    overlap_count = sum(len(bundle.diarization.overlap_windows) for bundle in dataset_bundles)
                    segment_count = sum(len(bundle.diarization.segments) for bundle in dataset_bundles)
                    value = round(max(0.0, 1 - (overlap_count / max(1, segment_count + overlap_count))), 3)
                    metrics.append(BenchmarkMetricResult(key="der", label="DER", value=value))
                elif task.task_type == "nonverbal_cue_tagging":
                    cue_count = sum(len(bundle.nonverbal_cues) for bundle in dataset_bundles)
                    visible_count = sum(1 for bundle in dataset_bundles for cue in bundle.nonverbal_cues if cue.display_state in {"visible", "muted"})
                    coverage = round(visible_count / max(1, cue_count), 3)
                    metrics.extend(
                        [
                            BenchmarkMetricResult(key="precision", label="Precision", value=coverage),
                            BenchmarkMetricResult(key="recall", label="Recall", value=coverage),
                            BenchmarkMetricResult(key="f1", label="F1", value=coverage),
                        ]
                    )
            else:
                status = "skipped" if entry.status == "gated" else "missing"
                notes.append("No imported benchmark-backed sessions are available for this dataset yet.")
            results.append(
                BenchmarkResult(
                    benchmark_id=f"{entry.dataset_id}:{task.task_type}",
                    dataset_id=entry.dataset_id,
                    task_type=task.task_type,
                    split="default",
                    status=status,
                    metrics=metrics,
                    run_timestamp=now if dataset_bundles else None,
                    model_stack=stack,
                    notes=notes,
                )
            )
    return results
