from pathlib import Path

from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ConversionSession, ExtractedField, ExtractionResult, SourceReference
from nwbforge.normalization import RuleBasedNormalizationService


def make_session() -> ConversionSession:
    return ConversionSession(
        session_id="sess-001",
        pathway=ConversionPathway.SUPPORTED,
        sources=(
            SourceReference(
                source_id="source-1",
                location=Path("data/source-1"),
                source_type=SourceType.DIRECTORY,
                label="source 1",
            ),
        ),
    )


def test_rule_based_normalizer_maps_subject_and_session_fields() -> None:
    extraction = ExtractionResult(
        source_id="source-1",
        adapter_id="alpha",
        record_type="session",
        fields={
            "subject_id": ExtractedField("subject_id", "mouse-01", "source-1"),
            "subject.sex": ExtractedField("subject.sex", "U", "source-1"),
            "subject.age": ExtractedField("subject.age", "P90D", "source-1"),
            "subject.description": ExtractedField("subject.description", "Test subject", "source-1"),
            "description": ExtractedField("description", "Visual task", "source-1"),
            "experiment_description": ExtractedField(
                "experiment_description",
                "Visual stimulation task",
                "source-1",
            ),
            "devices.0.device_id": ExtractedField("devices.0.device_id", "camera-1", "source-1"),
            "devices.0.name": ExtractedField("devices.0.name", "Camera One", "source-1"),
            "devices.0.description": ExtractedField(
                "devices.0.description",
                "Behavior camera",
                "source-1",
            ),
            "devices.0.manufacturer": ExtractedField(
                "devices.0.manufacturer",
                "Acme Imaging",
                "source-1",
            ),
            "keywords": ExtractedField("keywords", "vision, behavior", "source-1"),
        },
    )

    bundle = RuleBasedNormalizationService().normalize(make_session(), (extraction,))

    assert bundle.subject.subject_id is not None
    assert bundle.subject.subject_id.value == "mouse-01"
    assert bundle.subject.sex is not None
    assert bundle.subject.sex.value == "U"
    assert bundle.subject.age is not None
    assert bundle.subject.age.value == "P90D"
    assert bundle.subject.description is not None
    assert bundle.subject.description.value == "Test subject"
    assert bundle.session.session_description is not None
    assert bundle.session.session_description.value == "Visual task"
    assert bundle.session.experiment_description is not None
    assert bundle.session.experiment_description.value == "Visual stimulation task"
    assert len(bundle.devices) == 1
    assert bundle.devices[0].device_id == "camera-1"
    assert bundle.devices[0].name.value == "Camera One"
    assert tuple(keyword.value for keyword in bundle.session.keywords) == ("vision", "behavior")


def test_rule_based_normalizer_marks_unknown_fields_for_review() -> None:
    extraction = ExtractionResult(
        source_id="source-1",
        adapter_id="alpha",
        record_type="session",
        fields={
            "operator_note": ExtractedField("operator_note", "check alignment", "source-1"),
        },
    )

    bundle = RuleBasedNormalizationService().normalize(make_session(), (extraction,))

    assert "operator_note" in bundle.additional_metadata
    assert bundle.additional_metadata["operator_note"].needs_review is True


def test_rule_based_normalizer_marks_duplicate_aliases_for_review() -> None:
    extraction = ExtractionResult(
        source_id="source-1",
        adapter_id="alpha",
        record_type="session",
        fields={
            "session_id": ExtractedField("session_id", "s-one", "source-1"),
            "recording_id": ExtractedField("recording_id", "s-two", "source-1"),
        },
    )

    bundle = RuleBasedNormalizationService().normalize(make_session(), (extraction,))

    assert bundle.session.session_id is not None
    assert bundle.session.session_id.value == "s-two"
    assert bundle.session.session_id.needs_review is True


def test_rule_based_normalizer_falls_back_to_conversion_session_id() -> None:
    bundle = RuleBasedNormalizationService().normalize(make_session(), ())

    assert bundle.session.session_id is not None
    assert bundle.session.session_id.value == "sess-001"
