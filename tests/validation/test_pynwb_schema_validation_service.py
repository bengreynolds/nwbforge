from datetime import datetime
from pathlib import Path

from dateutil.tz import tzlocal
from pynwb import NWBHDF5IO, NWBFile

from nwbforge.domain.enums import ConversionPathway
from nwbforge.domain.models import ConversionSession, ProvenanceArtifact
from nwbforge.validation import (
    ArtifactValidationService,
    CompositeValidationService,
    PyNWBSchemaValidationService,
)


def make_session() -> ConversionSession:
    return ConversionSession(session_id="sess-001", pathway=ConversionPathway.SUPPORTED)


def write_valid_nwb(path: Path) -> None:
    nwbfile = NWBFile(
        session_description="Validation test session",
        identifier="validation-test",
        session_start_time=datetime.now(tzlocal()),
    )
    with NWBHDF5IO(path=str(path), mode="w") as io:
        io.write(nwbfile)


def test_pynwb_schema_validation_accepts_valid_nwb(tmp_path: Path) -> None:
    nwb_path = tmp_path / "valid.nwb"
    write_valid_nwb(nwb_path)

    summary = PyNWBSchemaValidationService().validate(
        make_session(),
        (ProvenanceArtifact(artifact_type="nwb", location=nwb_path),),
    )

    assert summary.is_passing() is True


def test_pynwb_schema_validation_reports_unreadable_nwb_artifact(tmp_path: Path) -> None:
    nwb_path = tmp_path / "invalid.nwb"
    nwb_path.write_text("not an hdf5 file", encoding="utf-8")

    summary = PyNWBSchemaValidationService().validate(
        make_session(),
        (ProvenanceArtifact(artifact_type="nwb", location=nwb_path),),
    )

    assert summary.is_passing() is False
    assert summary.errors()[0].code == "pynwb-schema-exception"


def test_composite_validation_service_combines_artifact_and_schema_results(tmp_path: Path) -> None:
    empty_nwb = tmp_path / "empty.nwb"
    empty_nwb.write_bytes(b"")

    summary = CompositeValidationService(
        (ArtifactValidationService(), PyNWBSchemaValidationService())
    ).validate(
        make_session(),
        (ProvenanceArtifact(artifact_type="nwb", location=empty_nwb),),
    )

    error_codes = {issue.code for issue in summary.errors()}
    assert "empty-artifact" in error_codes
