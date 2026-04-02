"""Machine-readable validation report generation."""

from __future__ import annotations

import json
from pathlib import Path

from nwbforge.domain.contracts import ValidationReportService
from nwbforge.domain.models import (
    ConversionSession,
    ProvenanceArtifact,
    ProvenanceRecord,
    ValidationReviewOutcome,
    ValidationSummary,
)


class JsonValidationReportService(ValidationReportService):
    """Write validation and provenance results as a JSON report artifact."""

    def __init__(self, filename: str = "validation-report.json") -> None:
        self._filename = filename

    def write_report(
        self,
        session: ConversionSession,
        provenance_record: ProvenanceRecord,
        validation_summary: ValidationSummary,
        review_outcome: ValidationReviewOutcome,
    ) -> ProvenanceArtifact:
        report_path = self._report_path(session, provenance_record)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(
                self._report_payload(session, provenance_record, validation_summary, review_outcome),
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return ProvenanceArtifact(
            artifact_type="validation_report",
            location=report_path,
            description="Machine-readable validation report.",
        )

    def _report_path(
        self,
        session: ConversionSession,
        provenance_record: ProvenanceRecord,
    ) -> Path:
        if provenance_record.generated_artifacts:
            return provenance_record.generated_artifacts[0].location.parent / self._filename
        return Path("artifacts") / session.session_id / self._filename

    @staticmethod
    def _report_payload(
        session: ConversionSession,
        provenance_record: ProvenanceRecord,
        validation_summary: ValidationSummary,
        review_outcome: ValidationReviewOutcome,
    ) -> dict[str, object]:
        return {
            "session_id": session.session_id,
            "pathway": str(session.pathway),
            "status": str(session.status),
            "is_passing": validation_summary.is_passing(),
            "review_outcome": {
                "status": str(review_outcome.status),
                "blocks_completion": review_outcome.blocks_completion,
                "requires_manual_review": review_outcome.requires_manual_review,
                "error_count": review_outcome.error_count,
                "warning_count": review_outcome.warning_count,
            },
            "adapter_ids": list(provenance_record.adapter_ids),
            "input_artifacts": [
                JsonValidationReportService._artifact_payload(artifact)
                for artifact in provenance_record.input_artifacts
            ],
            "generated_artifacts": [
                JsonValidationReportService._artifact_payload(artifact)
                for artifact in provenance_record.generated_artifacts
            ],
            "issues": [
                {
                    "code": issue.code,
                    "message": issue.message,
                    "severity": str(issue.severity),
                    "location": issue.location,
                    "tool": issue.tool,
                }
                for issue in validation_summary.issues
            ],
            "summary": {
                "error_count": len(validation_summary.errors()),
                "warning_count": len(validation_summary.warnings()),
            },
        }

    @staticmethod
    def _artifact_payload(artifact: ProvenanceArtifact) -> dict[str, object]:
        return {
            "artifact_type": artifact.artifact_type,
            "location": str(artifact.location),
            "description": artifact.description,
            "sha256": artifact.sha256,
        }
