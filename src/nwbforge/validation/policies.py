"""Validation policies for generated conversion artifacts."""

from __future__ import annotations

from dataclasses import dataclass

from nwbforge.domain.contracts import ValidationPolicyService
from nwbforge.domain.enums import ValidationReviewStatus
from nwbforge.domain.models import ConversionSession, ValidationReviewOutcome, ValidationSummary


@dataclass(frozen=True, slots=True)
class ValidationPolicy:
    require_nwb_output: bool = True
    allowed_nwb_suffixes: tuple[str, ...] = (".nwb",)
    require_existing_files: bool = True
    reject_empty_files: bool = True


class DefaultValidationReviewPolicyService(ValidationPolicyService):
    """Map raw validation issues into explicit workflow-facing review outcomes."""

    def assess(
        self,
        session: ConversionSession,
        validation_summary: ValidationSummary,
    ) -> ValidationReviewOutcome:
        del session
        error_count = len(validation_summary.errors())
        warning_count = len(validation_summary.warnings())

        if error_count:
            return ValidationReviewOutcome(
                status=ValidationReviewStatus.BLOCKED,
                blocks_completion=True,
                requires_manual_review=True,
                error_count=error_count,
                warning_count=warning_count,
            )

        if warning_count:
            return ValidationReviewOutcome(
                status=ValidationReviewStatus.REVIEW,
                blocks_completion=False,
                requires_manual_review=True,
                error_count=0,
                warning_count=warning_count,
            )

        return ValidationReviewOutcome(
            status=ValidationReviewStatus.PASS,
            blocks_completion=False,
            requires_manual_review=False,
            error_count=0,
            warning_count=0,
        )
