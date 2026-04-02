from pathlib import Path

from nwbforge.domain.enums import ConversionPathway, IssueSeverity
from nwbforge.domain.models import ConversionSession, ProvenanceArtifact
from nwbforge.validation import ArtifactValidationService, ValidationPolicy


def make_session() -> ConversionSession:
    return ConversionSession(session_id="sess-001", pathway=ConversionPathway.SUPPORTED)


def test_validation_service_errors_when_no_artifacts_are_produced() -> None:
    summary = ArtifactValidationService().validate(make_session(), ())

    assert summary.is_passing() is False
    assert summary.errors()[0].code == "no-output-artifacts"


def test_validation_service_accepts_existing_nwb_artifact(tmp_path: Path) -> None:
    nwb_file = tmp_path / "session.nwb"
    nwb_file.write_bytes(b"not-real-nwb-yet")
    artifact = ProvenanceArtifact(artifact_type="nwb", location=nwb_file)

    summary = ArtifactValidationService().validate(make_session(), (artifact,))

    assert summary.is_passing() is True


def test_validation_service_flags_missing_or_empty_artifacts(tmp_path: Path) -> None:
    empty_file = tmp_path / "session.nwb"
    empty_file.write_bytes(b"")
    missing_file = tmp_path / "report.json"
    summary = ArtifactValidationService().validate(
        make_session(),
        (
            ProvenanceArtifact(artifact_type="nwb", location=empty_file),
            ProvenanceArtifact(artifact_type="report", location=missing_file),
        ),
    )

    error_codes = {issue.code for issue in summary.errors()}
    assert "empty-artifact" in error_codes
    assert "artifact-missing" in error_codes


def test_validation_service_can_warn_on_multiple_nwb_outputs(tmp_path: Path) -> None:
    first_nwb = tmp_path / "first.nwb"
    second_nwb = tmp_path / "second.nwb"
    first_nwb.write_bytes(b"abc")
    second_nwb.write_bytes(b"def")

    summary = ArtifactValidationService().validate(
        make_session(),
        (
            ProvenanceArtifact(artifact_type="nwb", location=first_nwb),
            ProvenanceArtifact(artifact_type="nwb", location=second_nwb),
        ),
    )

    warning_codes = {issue.code for issue in summary.warnings()}
    assert "multiple-nwb-outputs" in warning_codes


def test_validation_policy_can_disable_required_nwb_output(tmp_path: Path) -> None:
    report_file = tmp_path / "report.json"
    report_file.write_text("{}")
    summary = ArtifactValidationService(
        policy=ValidationPolicy(require_nwb_output=False)
    ).validate(
        make_session(),
        (ProvenanceArtifact(artifact_type="report", location=report_file),),
    )

    assert summary.is_passing() is True
    assert not any(issue.severity == IssueSeverity.ERROR for issue in summary.issues)
