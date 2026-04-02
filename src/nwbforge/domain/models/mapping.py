"""Mapping-plan models between normalized metadata and NWB targets."""

from __future__ import annotations

from dataclasses import dataclass, field

from nwbforge.domain.enums import ConversionPathway, MappingAction, ReviewStatus
from nwbforge.domain.models.common import ReviewIssue


@dataclass(frozen=True, slots=True)
class MappingDecision:
    source_key: str
    target_path: str | None
    action: MappingAction
    rationale: str
    review_status: ReviewStatus = ReviewStatus.NOT_REVIEWED
    source_ids: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    @property
    def requires_manual_attention(self) -> bool:
        return self.review_status == ReviewStatus.NEEDS_REVIEW


@dataclass(frozen=True, slots=True)
class MappingPlan:
    pathway: ConversionPathway
    decisions: tuple[MappingDecision, ...] = ()
    issues: tuple[ReviewIssue, ...] = ()
    summary_notes: tuple[str, ...] = ()
    extension_recommendations: tuple[str, ...] = ()

    def blocking_issues(self) -> tuple[ReviewIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity.value == "error")

    def requires_manual_review(self) -> bool:
        return any(decision.requires_manual_attention for decision in self.decisions)

    def target_paths(self) -> tuple[str, ...]:
        return tuple(
            decision.target_path
            for decision in self.decisions
            if decision.target_path is not None
        )
