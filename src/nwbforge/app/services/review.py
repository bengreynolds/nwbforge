"""Application services for post-execution review and approval steps."""

from __future__ import annotations

from dataclasses import replace
import logging

from nwbforge.app.logging import get_logger, log_event
from nwbforge.app.services.errors import ReviewDecisionError
from nwbforge.app.services.models import ConversionExecution, ReviewSubmission
from nwbforge.domain.contracts import ReviewArtifactService
from nwbforge.domain.enums import ReviewStatus
from nwbforge.domain.models import ExecutionReviewRecord


class ExecutionReviewService:
    """Persist review acknowledgements and approval decisions for execution results."""

    _logger = get_logger(__name__)

    def __init__(self, review_artifact_service: ReviewArtifactService) -> None:
        self._review_artifact_service = review_artifact_service

    def submit_review(
        self,
        execution: ConversionExecution,
        *,
        reviewer: str,
        decision: ReviewStatus,
        acknowledged_issue_refs: tuple[str, ...] = (),
        override_blocks_completion: bool = False,
        rationale: str | None = None,
    ) -> ReviewSubmission:
        log_event(
            self._logger,
            logging.INFO,
            "Submitting execution review.",
            session_id=execution.session.session_id,
            decision=decision.value,
            acknowledged_issue_count=len(acknowledged_issue_refs),
            override_blocks_completion=override_blocks_completion,
        )
        self._validate_submission(
            execution,
            decision=decision,
            acknowledged_issue_refs=acknowledged_issue_refs,
            override_blocks_completion=override_blocks_completion,
            rationale=rationale,
        )

        review_record = ExecutionReviewRecord(
            session_id=execution.session.session_id,
            reviewer=reviewer,
            decision=decision,
            validation_status=execution.review_outcome.status,
            acknowledged_issue_refs=acknowledged_issue_refs,
            override_blocks_completion=override_blocks_completion,
            rationale=rationale,
        )
        review_artifact = self._review_artifact_service.write_review(
            execution.session,
            execution.provenance_record,
            execution.validation_summary,
            execution.review_outcome,
            review_record,
        )
        provenance_record = replace(
            execution.provenance_record,
            generated_artifacts=execution.provenance_record.generated_artifacts + (review_artifact,),
        )
        log_event(
            self._logger,
            logging.INFO,
            "Submitted execution review.",
            session_id=execution.session.session_id,
            decision=decision.value,
            review_artifact=str(review_artifact.location),
        )
        return ReviewSubmission(
            execution=execution,
            review_record=review_record,
            review_artifact=review_artifact,
            provenance_record=provenance_record,
        )

    @staticmethod
    def _validate_submission(
        execution: ConversionExecution,
        *,
        decision: ReviewStatus,
        acknowledged_issue_refs: tuple[str, ...],
        override_blocks_completion: bool,
        rationale: str | None,
    ) -> None:
        if decision not in {ReviewStatus.APPROVED, ReviewStatus.REJECTED}:
            raise ReviewDecisionError("Review submissions must be approved or rejected explicitly.")

        available_issue_refs = execution.validation_summary.issue_refs()
        unknown_issue_refs = tuple(
            issue_ref for issue_ref in acknowledged_issue_refs if issue_ref not in available_issue_refs
        )
        if unknown_issue_refs:
            raise ReviewDecisionError(
                f"Review submission acknowledged unknown issue refs: {', '.join(unknown_issue_refs)}"
            )

        if decision != ReviewStatus.APPROVED:
            return

        if execution.review_outcome.requires_manual_review:
            missing_issue_refs = tuple(
                issue_ref for issue_ref in available_issue_refs if issue_ref not in acknowledged_issue_refs
            )
            if missing_issue_refs:
                raise ReviewDecisionError(
                    "Approving a review-required execution requires acknowledging all current validation issues."
                )

        if execution.review_outcome.blocks_completion:
            if not override_blocks_completion:
                raise ReviewDecisionError(
                    "Blocked executions cannot be approved without an explicit override."
                )
            if not rationale:
                raise ReviewDecisionError(
                    "Blocked execution overrides require a rationale."
                )
