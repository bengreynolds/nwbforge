from pathlib import Path

from nwbforge.domain.enums import ConversionPathway, ReviewStatus, SourceType, ValueOrigin
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
            "acquisition_streams.0.stream_id": ExtractedField(
                "acquisition_streams.0.stream_id",
                "lick-trace",
                "source-1",
            ),
            "acquisition_streams.0.name": ExtractedField(
                "acquisition_streams.0.name",
                "Lick Trace",
                "source-1",
            ),
            "acquisition_streams.0.modality": ExtractedField(
                "acquisition_streams.0.modality",
                "behavior",
                "source-1",
            ),
            "acquisition_streams.0.description": ExtractedField(
                "acquisition_streams.0.description",
                "Example lick signal",
                "source-1",
            ),
            "acquisition_streams.0.data": ExtractedField(
                "acquisition_streams.0.data",
                [0.1, 0.2, 0.3],
                "source-1",
            ),
            "acquisition_streams.0.unit": ExtractedField(
                "acquisition_streams.0.unit",
                "a.u.",
                "source-1",
            ),
            "acquisition_streams.0.rate": ExtractedField(
                "acquisition_streams.0.rate",
                10.0,
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
    assert len(bundle.acquisition_streams) == 1
    assert bundle.acquisition_streams[0].stream_id == "lick-trace"
    assert bundle.acquisition_streams[0].name.value == "Lick Trace"
    assert bundle.acquisition_streams[0].metadata["unit"].value == "a.u."
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


def test_rule_based_normalizer_prefers_primary_source_over_supplemental_on_conflict() -> None:
    session = ConversionSession(
        session_id="sess-roles-001",
        pathway=ConversionPathway.HYBRID,
        sources=(
            SourceReference(
                source_id="supplemental-source",
                location=Path("data/source-supplemental"),
                source_type=SourceType.DIRECTORY,
                label="supplemental source",
                role="supplemental",
            ),
            SourceReference(
                source_id="primary-source",
                location=Path("data/source-primary"),
                source_type=SourceType.DIRECTORY,
                label="primary source",
                role="primary",
            ),
        ),
    )
    extraction_results = (
        ExtractionResult(
            source_id="supplemental-source",
            adapter_id="custom_json_session",
            record_type="custom",
            fields={
                "subject.subject_id": ExtractedField(
                    "subject.subject_id",
                    "supplemental-mouse-01",
                    "supplemental-source",
                ),
            },
        ),
        ExtractionResult(
            source_id="primary-source",
            adapter_id="session_manifest",
            record_type="manifest",
            fields={
                "subject.subject_id": ExtractedField(
                    "subject.subject_id",
                    "primary-mouse-01",
                    "primary-source",
                ),
            },
        ),
    )

    bundle = RuleBasedNormalizationService().normalize(session, extraction_results)

    assert bundle.subject.subject_id is not None
    assert bundle.subject.subject_id.value == "primary-mouse-01"
    assert bundle.subject.subject_id.review_status is ReviewStatus.NEEDS_REVIEW
    assert bundle.subject.subject_id.source_ids == ("supplemental-source", "primary-source")
    assert "Retained value from primary source over supplemental source." in bundle.subject.subject_id.notes


def test_rule_based_normalizer_applies_session_wide_metadata_overrides_after_normalization() -> None:
    session = ConversionSession(
        session_id="sess-overrides-001",
        pathway=ConversionPathway.HYBRID,
        sources=(
            SourceReference(
                source_id="source-1",
                location=Path("data/source-1"),
                source_type=SourceType.DIRECTORY,
                label="source 1",
            ),
        ),
        metadata_overrides={
            "subject.subject_id": "override-mouse-01",
            "session.experimenter": "Researcher, Alice",
        },
    )
    extraction = ExtractionResult(
        source_id="source-1",
        adapter_id="alpha",
        record_type="session",
        fields={
            "subject.subject_id": ExtractedField("subject.subject_id", "source-mouse-01", "source-1"),
            "session.experimenter": ExtractedField("session.experimenter", "Source, Bob", "source-1"),
        },
    )

    bundle = RuleBasedNormalizationService().normalize(session, (extraction,))

    assert bundle.subject.subject_id is not None
    assert bundle.subject.subject_id.value == "override-mouse-01"
    assert bundle.subject.subject_id.origin is ValueOrigin.USER_SUPPLIED
    assert bundle.subject.subject_id.review_status is ReviewStatus.NOT_REVIEWED
    assert "Applied from session-wide metadata override." in bundle.subject.subject_id.notes
    assert bundle.session.experimenter is not None
    assert bundle.session.experimenter.value == "Researcher, Alice"
    assert bundle.session.experimenter.origin is ValueOrigin.USER_SUPPLIED


def test_rule_based_normalizer_falls_back_to_conversion_session_id() -> None:
    bundle = RuleBasedNormalizationService().normalize(make_session(), ())

    assert bundle.session.session_id is not None
    assert bundle.session.session_id.value == "sess-001"
