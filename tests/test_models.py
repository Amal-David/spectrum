from spectrum_core.constants import SCHEMA_VERSION
from spectrum_core.datasets import list_dataset_records, load_demo_manifest


def test_dataset_records_are_available() -> None:
    records = list_dataset_records()
    dataset_ids = {record["id"] for record in records}
    assert "ami_corpus" in dataset_ids
    assert "ravdess_speech_16k" in dataset_ids
    voxconverse = next(record for record in records if record["id"] == "voxconverse")
    assert voxconverse["health_status"] == "ready"


def test_demo_manifest_has_nine_samples() -> None:
    samples = load_demo_manifest()
    assert len(samples) == 9
    assert SCHEMA_VERSION == "0.2.0"
    assert any(sample["source_dataset"] == "indic_audio_natural_conversations_sample" for sample in samples)
    assert any(sample["source_dataset"] == "ami_corpus" for sample in samples)
