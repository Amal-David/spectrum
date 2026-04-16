from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

from spectrum_core.models import (
    CohortDistribution,
    CohortDistributionItem,
    CohortFilters,
    CohortKPI,
    CohortPhaseSummary,
    CohortSessionRow,
    CohortSummary,
    CohortTrendPoint,
    SessionBundle,
)


def _bundle_timestamp(bundle: SessionBundle) -> datetime:
    bundle_path = bundle.artifacts.bundle_path
    if bundle_path and Path(bundle_path).exists():
        return datetime.fromtimestamp(Path(bundle_path).stat().st_mtime, tz=UTC)
    return datetime.now(tz=UTC)


def _duration_band(duration_sec: float) -> str:
    if duration_sec >= 1800:
        return "30m_plus"
    if duration_sec >= 600:
        return "10m_to_30m"
    if duration_sec >= 180:
        return "3m_to_10m"
    return "under_3m"


def _quality_band(bundle: SessionBundle) -> str:
    if bundle.quality.noise_ratio >= 0.35 or not bundle.quality.is_usable:
        return "risky"
    if bundle.quality.noise_ratio >= 0.2:
        return "watch"
    return "clean"


def _role_presence(bundle: SessionBundle) -> str:
    roles = {assignment.speaker_role for assignment in bundle.speaker_roles.assignments}
    if "human" in roles and "ai" in roles:
        return "human_ai"
    if "human" in roles:
        return "human_only"
    if "ai" in roles:
        return "ai_only"
    return "unknown"


def _project_tags(bundle: SessionBundle) -> tuple[str | None, list[str]]:
    metadata = bundle.source.metadata if bundle.source and bundle.source.metadata else {}
    project = metadata.get("project") if isinstance(metadata.get("project"), str) else None
    tags = metadata.get("tags")
    if isinstance(tags, list):
        return project, [str(tag) for tag in tags]
    if isinstance(tags, str):
        return project, [part.strip() for part in tags.split(",") if part.strip()]
    return project, []


def _matches_filters(bundle: SessionBundle, filters: CohortFilters) -> bool:
    bundle_time = _bundle_timestamp(bundle)
    if filters.date_from:
        if bundle_time.date() < datetime.fromisoformat(filters.date_from).date():
            return False
    if filters.date_to:
        if bundle_time.date() > datetime.fromisoformat(filters.date_to).date():
            return False
    if filters.dataset_ids and (bundle.session.dataset_id or "") not in set(filters.dataset_ids):
        return False
    if filters.source_types and bundle.session.source_type not in set(filters.source_types):
        return False
    if filters.analysis_modes and bundle.session.analysis_mode not in set(filters.analysis_modes):
        return False
    if filters.languages and (bundle.session.language or "") not in set(filters.languages):
        return False
    if filters.duration_band and _duration_band(bundle.session.duration_sec) != filters.duration_band:
        return False
    if filters.quality_band and _quality_band(bundle) != filters.quality_band:
        return False
    if filters.role_presence and _role_presence(bundle) != filters.role_presence:
        return False
    project, tags = _project_tags(bundle)
    if filters.projects and (project or "") not in set(filters.projects):
        return False
    if filters.tags and not (set(filters.tags) & set(tags)):
        return False
    return True


def filter_bundles(bundles: list[SessionBundle], filters: CohortFilters) -> list[SessionBundle]:
    return [bundle for bundle in bundles if _matches_filters(bundle, filters)]


def _signal_value(bundle: SessionBundle, key: str) -> float:
    for signal in bundle.signals:
        if signal.key == key:
            return float(signal.score)
    return 0.0


def _session_row(bundle: SessionBundle) -> CohortSessionRow:
    roles = {assignment.speaker_role for assignment in bundle.speaker_roles.assignments}
    return CohortSessionRow(
        session_id=bundle.session.session_id,
        title=bundle.session.title,
        source_type=bundle.session.source_type,
        dataset_id=bundle.session.dataset_id,
        analysis_mode=bundle.session.analysis_mode,
        language=bundle.session.language,
        duration_sec=bundle.session.duration_sec,
        readiness_tier=bundle.session.readiness_tier,
        usable=bundle.quality.is_usable,
        quality_band=_quality_band(bundle),
        human_present="human" in roles,
        ai_present="ai" in roles,
        top_signal=(bundle.signals[0].label if bundle.signals else None),
    )


def cohort_summary(bundles: list[SessionBundle], filters: CohortFilters | None = None) -> CohortSummary:
    filters = filters or CohortFilters()
    matched = filter_bundles(bundles, filters)
    hesitation_values = [_signal_value(bundle, "hesitation") for bundle in matched]
    friction_values = [_signal_value(bundle, "friction") for bundle in matched]
    rapport_values = [_signal_value(bundle, "rapport") for bundle in matched]
    frustration_values = [_signal_value(bundle, "frustration_risk") for bundle in matched]
    snr_values = [bundle.quality.avg_snr_db for bundle in matched if bundle.quality.avg_snr_db is not None]
    usable_rate = (sum(1 for bundle in matched if bundle.quality.is_usable) / len(matched) * 100) if matched else 0.0

    emotion_counts = Counter(
        sentence.emotion_label
        for bundle in matched
        for sentence in bundle.content.sentences
        if sentence.speaker_role == "human" and sentence.emotion_label and sentence.emotion_label != "unlabeled"
    )

    return CohortSummary(
        filters=filters,
        kpis=[
            CohortKPI(key="run_count", label="Run count", value=len(matched)),
            CohortKPI(key="usable_run_rate", label="Usable-run rate", value=round(usable_rate, 1), unit="%"),
            CohortKPI(key="avg_snr_db", label="Average SNR", value=round(mean(snr_values), 2) if snr_values else 0.0, unit="dB"),
            CohortKPI(key="hesitation_avg", label="Human hesitation", value=round(mean(hesitation_values), 1) if hesitation_values else 0.0),
            CohortKPI(key="friction_avg", label="Human friction", value=round(mean(friction_values), 1) if friction_values else 0.0),
            CohortKPI(key="rapport_avg", label="Rapport", value=round(mean(rapport_values), 1) if rapport_values else 0.0),
            CohortKPI(key="frustration_avg", label="Frustration risk", value=round(mean(frustration_values), 1) if frustration_values else 0.0),
        ],
        phase_summaries=phase_summaries(matched),
        dominant_emotions=[
            CohortDistributionItem(key=emotion, label=emotion.replace("_", " "), value=count, value_type="count")
            for emotion, count in emotion_counts.most_common(6)
        ],
        runs=[_session_row(bundle) for bundle in matched],
    )


def trend_series(bundles: list[SessionBundle], filters: CohortFilters | None = None) -> list[CohortTrendPoint]:
    filters = filters or CohortFilters()
    matched = filter_bundles(bundles, filters)
    by_day: dict[str, list[SessionBundle]] = defaultdict(list)
    for bundle in matched:
        by_day[_bundle_timestamp(bundle).date().isoformat()].append(bundle)
    points: list[CohortTrendPoint] = []
    for bucket in sorted(by_day):
        cohort = by_day[bucket]
        points.append(
            CohortTrendPoint(
                bucket=bucket,
                run_count=len(cohort),
                usable_run_rate=round(sum(1 for bundle in cohort if bundle.quality.is_usable) / len(cohort) * 100, 1),
                avg_snr_db=round(mean([bundle.quality.avg_snr_db for bundle in cohort if bundle.quality.avg_snr_db is not None]) if any(bundle.quality.avg_snr_db is not None for bundle in cohort) else 0.0, 2),
                hesitation_avg=round(mean([_signal_value(bundle, "hesitation") for bundle in cohort]), 1),
                friction_avg=round(mean([_signal_value(bundle, "friction") for bundle in cohort]), 1),
                rapport_avg=round(mean([_signal_value(bundle, "rapport") for bundle in cohort]), 1),
                frustration_avg=round(mean([_signal_value(bundle, "frustration_risk") for bundle in cohort]), 1),
            )
        )
    return points


def distributions(bundles: list[SessionBundle], filters: CohortFilters | None = None) -> list[CohortDistribution]:
    filters = filters or CohortFilters()
    matched = filter_bundles(bundles, filters)
    quality_counter = Counter(_quality_band(bundle) for bundle in matched)
    source_counter = Counter(bundle.session.source_type for bundle in matched)
    duration_counter = Counter(_duration_band(bundle.session.duration_sec) for bundle in matched)
    dominant_emotions = Counter(
        sentence.emotion_label
        for bundle in matched
        for sentence in bundle.content.sentences
        if sentence.speaker_role == "human" and sentence.emotion_label and sentence.emotion_label != "unlabeled"
    )
    return [
        CohortDistribution(
            key="quality_band_mix",
            label="Quality band mix",
            items=[CohortDistributionItem(key=key, label=key, value=value, value_type="count") for key, value in quality_counter.items()],
        ),
        CohortDistribution(
            key="source_mix",
            label="Source mix",
            items=[CohortDistributionItem(key=key, label=key.replace("_", " "), value=value, value_type="count") for key, value in source_counter.items()],
        ),
        CohortDistribution(
            key="duration_mix",
            label="Duration bands",
            items=[CohortDistributionItem(key=key, label=key.replace("_", " "), value=value, value_type="count") for key, value in duration_counter.items()],
        ),
        CohortDistribution(
            key="dominant_human_emotions",
            label="Dominant human emotions",
            items=[CohortDistributionItem(key=key, label=key.replace("_", " "), value=value, value_type="count") for key, value in dominant_emotions.most_common(8)],
        ),
    ]


def phase_summaries(bundles: list[SessionBundle]) -> list[CohortPhaseSummary]:
    phase_windows = [
        ("first_third", 0.0, 1 / 3),
        ("middle_third", 1 / 3, 2 / 3),
        ("final_third", 2 / 3, 1.0),
    ]
    summaries: list[CohortPhaseSummary] = []
    for phase, start_ratio, end_ratio in phase_windows:
        hesitation_samples: list[float] = []
        friction_samples: list[float] = []
        rapport_samples: list[float] = []
        frustration_samples: list[float] = []
        emotion_counter: Counter[str] = Counter()
        for bundle in bundles:
            start_ms = bundle.session.duration_sec * 1000 * start_ratio
            end_ms = bundle.session.duration_sec * 1000 * end_ratio
            phase_questions = []
            turn_lookup = {turn.turn_id: turn for turn in bundle.turns}
            for question in bundle.questions:
                answer_turn = turn_lookup.get(question.answer_turn_id)
                if answer_turn and start_ms <= answer_turn.start_ms < end_ms:
                    phase_questions.append(question)
            if phase_questions:
                hesitation_samples.append(mean(question.hesitation_score for question in phase_questions))
            phase_events = [event for event in bundle.events if start_ms <= event.begin_ms < end_ms and event.type in {"interruption", "noise_spike", "engagement_drop"}]
            friction_samples.append(min(100.0, len(phase_events) * 18.0))
            phase_speakers = [speaker for speaker in bundle.speakers if speaker.speaker_role == "human"] or bundle.speakers
            if phase_speakers:
                human_balance = phase_speakers[0].talk_ratio
                rapport_samples.append(max(10.0, 100.0 - abs((human_balance - 0.5) * 140.0)))
            frustration_samples.append(min(100.0, (friction_samples[-1] if friction_samples else 0.0) * 0.65 + (mean(question.hesitation_score for question in phase_questions) if phase_questions else 0.0) * 0.35))
            for sentence in bundle.content.sentences:
                if sentence.speaker_role == "human" and start_ms <= sentence.start_ms < end_ms and sentence.emotion_label != "unlabeled":
                    emotion_counter[sentence.emotion_label] += 1
        summaries.append(
            CohortPhaseSummary(
                phase=phase,
                hesitation_avg=round(mean(hesitation_samples), 1) if hesitation_samples else 0.0,
                friction_avg=round(mean(friction_samples), 1) if friction_samples else 0.0,
                rapport_avg=round(mean(rapport_samples), 1) if rapport_samples else 0.0,
                frustration_avg=round(mean(frustration_samples), 1) if frustration_samples else 0.0,
                dominant_emotion=emotion_counter.most_common(1)[0][0] if emotion_counter else "unlabeled",
            )
        )
    return summaries
