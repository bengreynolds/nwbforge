from datetime import datetime
from pathlib import Path

from dateutil.tz import tzlocal
from pynwb import NWBHDF5IO, NWBFile
from pynwb.file import Subject

from nwbforge.domain.enums import ConversionPathway, IssueSeverity
from nwbforge.domain.models import ConversionSession, ProvenanceArtifact
from nwbforge.validation import NWBInspectorValidationService


def make_session() -> ConversionSession:
    return ConversionSession(session_id="sess-001", pathway=ConversionPathway.SUPPORTED)


def write_nwb_with_subject(path: Path) -> None:
    nwbfile = NWBFile(
        session_description="Validation test session",
        identifier="validation-test",
        session_start_time=datetime.now(tzlocal()),
        experimenter=["Researcher, Alice"],
        experiment_description="Test experiment",
        institution="Test University",
        keywords=["validation"],
    )
    nwbfile.subject = Subject(
        subject_id="mouse-01",
        species="Mus musculus",
        sex="U",
        age="P90D",
        description="Test subject",
    )
    with NWBHDF5IO(path=str(path), mode="w") as io:
        io.write(nwbfile)


def write_nwb_without_subject(path: Path) -> None:
    nwbfile = NWBFile(
        session_description="Validation test session",
        identifier="validation-test",
        session_start_time=datetime.now(tzlocal()),
    )
    with NWBHDF5IO(path=str(path), mode="w") as io:
        io.write(nwbfile)


def test_nwb_inspector_validation_accepts_complete_minimal_metadata(tmp_path: Path) -> None:
    nwb_path = tmp_path / "valid.nwb"
    write_nwb_with_subject(nwb_path)

    summary = NWBInspectorValidationService().validate(
        make_session(),
        (ProvenanceArtifact(artifact_type="nwb", location=nwb_path),),
    )

    assert summary.is_passing() is True


def test_nwb_inspector_validation_surfaces_critical_checks_as_errors(tmp_path: Path) -> None:
    nwb_path = tmp_path / "missing-subject.nwb"
    write_nwb_without_subject(nwb_path)

    summary = NWBInspectorValidationService().validate(
        make_session(),
        (ProvenanceArtifact(artifact_type="nwb", location=nwb_path),),
    )

    assert summary.is_passing() is False
    assert any(issue.severity == IssueSeverity.ERROR for issue in summary.issues)
    assert any(issue.code == "nwbinspector-check_subject_exists" for issue in summary.issues)


def test_nwb_inspector_validation_can_raise_importance_threshold(tmp_path: Path) -> None:
    nwb_path = tmp_path / "missing-subject-thresholded.nwb"
    write_nwb_without_subject(nwb_path)

    summary = NWBInspectorValidationService(importance_threshold="CRITICAL").validate(
        make_session(),
        (ProvenanceArtifact(artifact_type="nwb", location=nwb_path),),
    )

    assert summary.is_passing() is False
    assert all(issue.code == "nwbinspector-check_subject_exists" for issue in summary.issues)
