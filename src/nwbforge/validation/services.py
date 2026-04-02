"""Concrete validation services."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from nwbinspector import Importance, inspect_nwbfile
from pynwb import validate as pynwb_validate

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


class PyNWBSchemaValidationService(ValidationService):
    """Validate NWB artifacts against the NWB schema with PyNWB."""

    def validate(
        self,
        session: ConversionSession,
        output_artifacts: tuple[ProvenanceArtifact, ...],
    ) -> ValidationSummary:
        del session
        issues: list[ValidationIssue] = []

        for artifact in output_artifacts:
            if not ArtifactValidationService._is_nwb_artifact(artifact):
                continue
            if not artifact.location.exists() or not artifact.location.is_file():
                continue
            if artifact.location.stat().st_size == 0:
                continue

            issues.extend(self._validate_artifact(artifact))

        return ValidationSummary(issues=tuple(issues))

    def _validate_artifact(self, artifact: ProvenanceArtifact) -> list[ValidationIssue]:
        try:
            schema_errors = pynwb_validate(path=artifact.location)
        except Exception as exc:  # pragma: no cover - third-party error types vary
            return [
                ValidationIssue(
                    code="pynwb-schema-exception",
                    message=f"PyNWB validation could not inspect '{artifact.location.name}': {exc}",
                    severity=IssueSeverity.ERROR,
                    location=str(artifact.location),
                    tool="pynwb",
                )
            ]

        return [
            ValidationIssue(
                code="pynwb-schema-error",
                message=str(error),
                severity=IssueSeverity.ERROR,
                location=str(artifact.location),
                tool="pynwb",
            )
            for error in schema_errors
        ]


class NWBInspectorValidationService(ValidationService):
    """Validate NWB artifacts against NWB best-practice checks."""

    def __init__(
        self,
        *,
        importance_threshold: str | Importance = Importance.BEST_PRACTICE_SUGGESTION,
        ignore: list[str] | None = None,
        select: list[str] | None = None,
    ) -> None:
        self._importance_threshold = importance_threshold
        self._ignore = ignore
        self._select = select

    def validate(
        self,
        session: ConversionSession,
        output_artifacts: tuple[ProvenanceArtifact, ...],
    ) -> ValidationSummary:
        del session
        issues: list[ValidationIssue] = []

        for artifact in output_artifacts:
            if not ArtifactValidationService._is_nwb_artifact(artifact):
                continue
            if not artifact.location.exists() or not artifact.location.is_file():
                continue
            if artifact.location.stat().st_size == 0:
                continue

            issues.extend(self._validate_artifact(artifact))

        return ValidationSummary(issues=tuple(issues))

    def _validate_artifact(self, artifact: ProvenanceArtifact) -> list[ValidationIssue]:
        try:
            messages = list(
                inspect_nwbfile(
                    artifact.location,
                    skip_validate=True,
                    ignore=self._ignore,
                    select=self._select,
                    importance_threshold=self._importance_threshold,
                )
            )
        except Exception as exc:  # pragma: no cover - third-party error types vary
            return [
                ValidationIssue(
                    code="nwbinspector-exception",
                    message=f"NWB Inspector could not inspect '{artifact.location.name}': {exc}",
                    severity=IssueSeverity.ERROR,
                    location=str(artifact.location),
                    tool="nwbinspector",
                )
            ]

        issues: list[ValidationIssue] = []
        for message in messages:
            if message is None:
                continue
            issues.append(
                ValidationIssue(
                    code=self._message_code(message.check_function_name),
                    message=message.message,
                    severity=self._map_importance(message.importance),
                    location=self._message_location(artifact.location, message.location),
                    tool="nwbinspector",
                )
            )
        return issues

    @staticmethod
    def _message_code(check_function_name: str | None) -> str:
        if check_function_name:
            return f"nwbinspector-{check_function_name}"
        return "nwbinspector-message"

    @staticmethod
    def _message_location(artifact_path: Path, object_location: str | None) -> str:
        if object_location:
            return f"{artifact_path}::{object_location}"
        return str(artifact_path)

    @staticmethod
    def _map_importance(importance: Importance) -> IssueSeverity:
        if importance in {Importance.ERROR, Importance.PYNWB_VALIDATION, Importance.CRITICAL}:
            return IssueSeverity.ERROR
        return IssueSeverity.WARNING


class CompositeValidationService(ValidationService):
    """Aggregate multiple validation services into one validation pass."""

    def __init__(self, services: Iterable[ValidationService]) -> None:
        self._services = tuple(services)

    def validate(
        self,
        session: ConversionSession,
        output_artifacts: tuple[ProvenanceArtifact, ...],
    ) -> ValidationSummary:
        issues: list[ValidationIssue] = []
        for service in self._services:
            issues.extend(service.validate(session, output_artifacts).issues)
        return ValidationSummary(issues=tuple(issues))
