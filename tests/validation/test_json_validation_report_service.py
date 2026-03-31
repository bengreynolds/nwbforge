import json
from pathlib import Path

from nwbforge.domain.enums import ConversionPathway, IssueSeverity, SessionStatus
from nwbforge.domain.models import (
    ConversionSession,
    ProvenanceArtifact,
    ProvenanceRecord,
    ValidationIssue,
    ValidationSummary,
)
from nwbforge.validation import JsonValidationReportService


def test_json_validation_report_service_writes_machine_readable_report(tmp_path: Path) -> None:
    session = ConversionSession(
        session_id="sess-001",
        pathway=ConversionPathway.SUPPORTED,
        status=SessionStatus.COMPLETED,
    )
    provenance_record = ProvenanceRecord(
        session_id=session.session_id,
        pathway=session.pathway,
        input_artifacts=(ProvenanceArtifact(artifact_type="input", location=tmp_path / "input.bin"),),
        generated_artifacts=(ProvenanceArtifact(artifact_type="nwb", location=tmp_path / "session.nwb"),),
        adapter_ids=("session_manifest",),
    )
    validation_summary = ValidationSummary(
        issues=(
            ValidationIssue(
                code="demo-warning",
                message="Example warning.",
                severity=IssueSeverity.WARNING,
                tool="nwbinspector",
            ),
        )
    )

    artifact = JsonValidationReportService().write_report(
        session,
        provenance_record,
        validation_summary,
    )

    payload = json.loads(artifact.location.read_text(encoding="utf-8"))
    assert artifact.artifact_type == "validation_report"
    assert payload["session_id"] == "sess-001"
    assert payload["is_passing"] is True
    assert payload["summary"]["warning_count"] == 1
    assert payload["generated_artifacts"][0]["artifact_type"] == "nwb"
