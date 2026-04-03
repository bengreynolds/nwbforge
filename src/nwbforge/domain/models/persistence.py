"""Persistable session snapshot models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from nwbforge.domain.models.provenance import ProvenanceRecord
from nwbforge.domain.models.review import ExecutionReviewRecord
from nwbforge.domain.models.session import ConversionSession
from nwbforge.domain.models.validation import ValidationReviewOutcome, ValidationSummary


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    session: ConversionSession
    snapshot_id: str | None = None
    saved_at: datetime | None = None
    provenance_record: ProvenanceRecord | None = None
    validation_summary: ValidationSummary | None = None
    review_outcome: ValidationReviewOutcome | None = None
    review_record: ExecutionReviewRecord | None = None


@dataclass(frozen=True, slots=True)
class SessionSnapshotHistoryEntry:
    snapshot_id: str
    session_id: str
    saved_at: datetime
    location: Path
    status: str
    artifact_count: int = 0
    issue_count: int = 0
    has_review_record: bool = False
