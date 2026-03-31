"""Concrete validation services."""

from __future__ import annotations

from pathlib import Path

from nwbforge.domain.contracts import ValidationService
from nwbforge.domain.enums import IssueSeverity
from nwbforge.domain.models import ConversionSession, ProvenanceArtifact, ValidationIssue, ValidationSummary
from nwbforge.validation.policies import ValidationPolicy


class ArtifactValidationService(ValidationService):
    """Validate that generated artifacts meet basic output policy expectations."""

    def __init__(self, policy: ValidationPolicy | None = None) -> None:
        self._policy = policy or ValidationPolicy()

    def validate(
        self,
        session: ConversionSession,
        output_artifacts: tuple[ProvenanceArtifact, ...],
    ) -> ValidationSummary:
        issues: list[ValidationIssue] = []

        if not output_artifacts:
            issues.append(
                ValidationIssue(
                    code="no-output-artifacts",
                    message=f"Session '{session.session_id}' produced no output artifacts.",
                    severity=IssueSeverity.ERROR,
                    tool="artifact_validation",
                )
            )
            return ValidationSummary(issues=tuple(issues))

        nwb_artifacts = [artifact for artifact in output_artifacts if self._is_nwb_artifact(artifact)]

        if self._policy.require_nwb_output and not nwb_artifacts:
            issues.append(
                ValidationIssue(
                    code="missing-nwb-output",
                    message="No NWB output artifact was produced.",
                    severity=IssueSeverity.ERROR,
                    tool="artifact_validation",
                )
            )

        if len(nwb_artifacts) > 1:
            issues.append(
                ValidationIssue(
                    code="multiple-nwb-outputs",
                    message="Multiple NWB artifacts were produced; review which output is canonical.",
                    severity=IssueSeverity.WARNING,
                    tool="artifact_validation",
                )
            )

        for artifact in output_artifacts:
            issues.extend(self._validate_artifact(artifact))

        return ValidationSummary(issues=tuple(issues))

    def _validate_artifact(self, artifact: ProvenanceArtifact) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        artifact_path = artifact.location

        if self._policy.require_existing_files and not artifact_path.exists():
            issues.append(
                ValidationIssue(
                    code="artifact-missing",
                    message=f"Expected artifact does not exist: {artifact_path}",
                    severity=IssueSeverity.ERROR,
                    location=str(artifact_path),
                    tool="artifact_validation",
                )
            )
            return issues

        if self._is_nwb_artifact(artifact) and artifact_path.suffix.lower() not in self._policy.allowed_nwb_suffixes:
            issues.append(
                ValidationIssue(
                    code="unexpected-nwb-extension",
                    message=f"NWB artifact does not use an allowed extension: {artifact_path.name}",
                    severity=IssueSeverity.ERROR,
                    location=str(artifact_path),
                    tool="artifact_validation",
                )
            )

        if self._policy.reject_empty_files and artifact_path.exists() and artifact_path.is_file():
            if artifact_path.stat().st_size == 0:
                issues.append(
                    ValidationIssue(
                        code="empty-artifact",
                        message=f"Artifact is empty: {artifact_path}",
                        severity=IssueSeverity.ERROR,
                        location=str(artifact_path),
                        tool="artifact_validation",
                    )
                )

        return issues

    @staticmethod
    def _is_nwb_artifact(artifact: ProvenanceArtifact) -> bool:
        artifact_type = artifact.artifact_type.lower()
        return artifact_type == "nwb" or artifact.location.suffix.lower() == ".nwb"
