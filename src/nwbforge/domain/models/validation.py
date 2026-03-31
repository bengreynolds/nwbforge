"""Validation models shared across schema and best-practice checks."""

from __future__ import annotations

from dataclasses import dataclass

from nwbforge.domain.enums import IssueSeverity, ValidationReviewStatus


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    message: str
    severity: IssueSeverity
    location: str | None = None
    tool: str | None = None


@dataclass(frozen=True, slots=True)
class ValidationSummary:
    issues: tuple[ValidationIssue, ...] = ()

    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == IssueSeverity.ERROR)

    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == IssueSeverity.WARNING)

    def is_passing(self) -> bool:
        return not self.errors()


@dataclass(frozen=True, slots=True)
class ValidationReviewOutcome:
    status: ValidationReviewStatus
    blocks_completion: bool
    requires_manual_review: bool
    error_count: int
    warning_count: int
