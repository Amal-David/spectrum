from spectrum_core.models import LabelPrediction, SessionResult
from spectrum_pipeline.service import derive_age_band


def test_derive_age_band_hides_exact_age_under_low_confidence() -> None:
    result = derive_age_band(27, confidence=0.2)
    assert result.label == "unknown"


def test_derive_age_band_maps_to_band() -> None:
    result = derive_age_band(27, confidence=0.9)
    assert result == LabelPrediction(label="25_34", confidence=0.9, warning_flags=[])


def test_session_result_schema_defaults() -> None:
    payload = SessionResult(job_id="job-1", analysis_mode="full", duration_sec=12.5, speaker_count=1)
    assert payload.schema_version == "0.2.0"
    assert payload.profile.accent_broad.label == "unknown"
