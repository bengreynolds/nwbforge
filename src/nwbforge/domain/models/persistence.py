"""Persistable session snapshot models."""

from __future__ import annotations

from dataclasses import dataclass

from nwbforge.domain.models.provenance import ProvenanceRecord
from nwbforge.domain.models.review import ExecutionReviewRecord
from nwbforge.domain.models.session import ConversionSession
from nwbforge.domain.models.validation import ValidationReviewOutcome, ValidationSummary


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    session: ConversionSession
    provenance_record: ProvenanceRecord | None = None
    validation_summary: ValidationSummary | None = None
    review_outcome: ValidationReviewOutcome | None = None
    review_record: ExecutionReviewRecord | None = None
