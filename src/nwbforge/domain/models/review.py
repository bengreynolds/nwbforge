"""Review and approval records for conversion outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from nwbforge.domain.enums import ReviewStatus, ValidationReviewStatus
from nwbforge.domain.models.session import utc_now


@dataclass(frozen=True, slots=True)
class ExecutionReviewRecord:
    session_id: str
    reviewer: str
    decision: ReviewStatus
    validation_status: ValidationReviewStatus
    acknowledged_issue_refs: tuple[str, ...] = ()
    override_blocks_completion: bool = False
    rationale: str | None = None
    reviewed_at: datetime = field(default_factory=utc_now)
