"""Shared value objects for the canonical domain layer."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Generic, TypeVar

from nwbforge.domain.enums import IssueSeverity, ReviewStatus, ValueOrigin

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ReviewIssue:
    """A human-review item that should remain visible across layers."""

    code: str
    message: str
    severity: IssueSeverity = IssueSeverity.WARNING
    field: str | None = None
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class NormalizedValue(Generic[T]):
    """A canonical metadata value plus traceability and review state."""

    value: T
    origin: ValueOrigin
    source_ids: tuple[str, ...] = ()
    confidence: float | None = None
    unit: str | None = None
    review_status: ReviewStatus = ReviewStatus.NOT_REVIEWED
    notes: tuple[str, ...] = ()

    @property
    def needs_review(self) -> bool:
        return self.review_status == ReviewStatus.NEEDS_REVIEW

    def with_review_status(self, review_status: ReviewStatus) -> "NormalizedValue[T]":
        return replace(self, review_status=review_status)
