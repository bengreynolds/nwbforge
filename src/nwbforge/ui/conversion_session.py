"""Toolkit-agnostic conversion-session screen model."""

from __future__ import annotations

from concurrent.futures import Future
from dataclasses import replace
from pathlib import Path
from threading import Lock

from nwbforge.app.services import ExecutionReviewService
from nwbforge.app.services.models import ConversionExecution, ConversionPreview, ReviewSubmission
from nwbforge.app.runtime import ConversionExecutor
from nwbforge.domain.enums import ReviewStatus
from nwbforge.domain.models import ConversionSession
from nwbforge.ui.errors import DefaultUiErrorPresenter, UiErrorPresenter
from nwbforge.ui.models import (
    ConversionSessionScreenState,
    ConversionSessionStateListener,
    GeneratedArtifactItem,
    ValidationIssueItem,
    conversion_source_items,
)


class ConversionSessionScreenModel:
    """Drive preview/execution state for a future conversion-session screen."""

    def __init__(
        self,
        executor: ConversionExecutor,
        *,
        review_service: ExecutionReviewService | None = None,
        error_presenter: UiErrorPresenter | None = None,
    ) -> None:
        self._executor = executor
        self._review_service = review_service
        self._state = ConversionSessionScreenState()
        self._listeners: list[ConversionSessionStateListener] = []
        self._lock = Lock()
        self._error_presenter = error_presenter or DefaultUiErrorPresenter()

    @property
    def state(self) -> ConversionSessionScreenState:
        return self._state

    def subscribe(self, listener: ConversionSessionStateListener, *, emit_initial: bool = True) -> None:
        with self._lock:
            self._listeners.append(listener)
            state = self._state
        if emit_initial:
            listener(state)

    def load_session(self, session: ConversionSession) -> ConversionSessionScreenState:
        return self._set_state(
            ConversionSessionScreenState(
                session=session,
                sources=conversion_source_items(session.sources),
                generated_artifacts=(),
                error_message=None,
                review_message=None,
                user_error=None,
            )
        )

    def start_preview(self) -> Future[ConversionPreview]:
        session = self._require_session()
        self._set_state(
            replace(
                self._state,
                is_preview_running=True,
                error_message=None,
                preview=None,
                execution=None,
                generated_artifacts=(),
                validation_issues=(),
                last_review_submission=None,
                review_message=None,
                progress_event=None,
                user_error=None,
            )
        )
        future = self._executor.submit_preview(session, progress_callback=self._handle_progress)
        future.add_done_callback(self._handle_preview_complete)
        return future

    def start_execution(self, output_path: Path) -> Future[ConversionExecution]:
        preview = self._require_preview()
        self._set_state(
            replace(
                self._state,
                is_execution_running=True,
                output_path=output_path,
                error_message=None,
                execution=None,
                generated_artifacts=(),
                last_review_submission=None,
                review_message=None,
                progress_event=None,
                user_error=None,
            )
        )
        future = self._executor.submit_execute(
            preview,
            output_path,
            progress_callback=self._handle_progress,
        )
        future.add_done_callback(self._handle_execution_complete)
        return future

    def shutdown(self, wait: bool = True) -> None:
        shutdown = getattr(self._executor, "shutdown", None)
        if shutdown is not None:
            shutdown(wait=wait)

    def set_reviewer_name(self, reviewer_name: str) -> ConversionSessionScreenState:
        return self._set_state(
            replace(
                self._state,
                reviewer_name=reviewer_name,
                error_message=None,
                user_error=None,
            )
        )

    def set_review_rationale(self, rationale: str) -> ConversionSessionScreenState:
        return self._set_state(
            replace(
                self._state,
                review_rationale=rationale,
                error_message=None,
                user_error=None,
            )
        )

    def set_override_blocks_completion(self, enabled: bool) -> ConversionSessionScreenState:
        return self._set_state(
            replace(
                self._state,
                override_blocks_completion=enabled,
                error_message=None,
                user_error=None,
            )
        )

    def set_issue_acknowledged(self, issue_ref: str, acknowledged: bool) -> ConversionSessionScreenState:
        issues = tuple(
            replace(issue, is_acknowledged=acknowledged) if issue.issue_ref == issue_ref else issue
            for issue in self._state.validation_issues
        )
        return self._set_state(
            replace(
                self._state,
                validation_issues=issues,
                error_message=None,
                user_error=None,
            )
        )

    def submit_review(self, decision: ReviewStatus) -> ReviewSubmission:
        if self._review_service is None:
            raise ValueError("Review submission is not configured for this conversion session.")

        execution = self._require_execution()
        try:
            submission = self._review_service.submit_review(
                execution,
                reviewer=self._state.reviewer_name.strip(),
                decision=decision,
                acknowledged_issue_refs=self._state.acknowledged_issue_refs,
                override_blocks_completion=self._state.override_blocks_completion,
                rationale=self._state.review_rationale.strip() or None,
            )
        except Exception as exc:
            user_error = self._error_presenter.present(exc)
            self._set_state(
                replace(
                    self._state,
                    error_message=user_error.message,
                    review_message=user_error.message,
                    user_error=user_error,
                )
            )
            raise

        self._set_state(
            replace(
                self._state,
                last_review_submission=submission,
                generated_artifacts=generated_artifact_items(submission.provenance_record.generated_artifacts),
                review_message=f"Review {submission.review_record.decision.value} by {submission.review_record.reviewer}.",
                error_message=None,
                user_error=None,
            )
        )
        return submission

    def _handle_progress(self, event) -> None:
        self._set_state(replace(self._state, progress_event=event, error_message=None, user_error=None))

    def _handle_preview_complete(self, future: Future[ConversionPreview]) -> None:
        try:
            preview = future.result()
        except Exception as exc:
            user_error = self._error_presenter.present(exc)
            self._set_state(
                replace(
                    self._state,
                    is_preview_running=False,
                    error_message=user_error.message,
                    review_message=None,
                    user_error=user_error,
                )
            )
            return

        self._set_state(
            replace(
                self._state,
                session=preview.session,
                sources=conversion_source_items(preview.session.sources),
                preview=preview,
                execution=None,
                generated_artifacts=(),
                validation_issues=(),
                last_review_submission=None,
                review_message=None,
                is_preview_running=False,
                error_message=None,
                user_error=None,
            )
        )

    def _handle_execution_complete(self, future: Future[ConversionExecution]) -> None:
        try:
            execution = future.result()
        except Exception as exc:
            user_error = self._error_presenter.present(exc)
            self._set_state(
                replace(
                    self._state,
                    is_execution_running=False,
                    error_message=user_error.message,
                    review_message=None,
                    user_error=user_error,
                )
            )
            return

        self._set_state(
            replace(
                self._state,
                session=execution.session,
                sources=conversion_source_items(execution.session.sources),
                execution=execution,
                preview=execution.preview,
                generated_artifacts=generated_artifact_items(execution.provenance_record.generated_artifacts),
                validation_issues=validation_issue_items(execution),
                last_review_submission=None,
                review_message=None,
                is_execution_running=False,
                error_message=None,
                user_error=None,
            )
        )

    def _require_session(self) -> ConversionSession:
        if self._state.session is None:
            raise ValueError("Conversion session screen requires a loaded session before preview can start.")
        return self._state.session

    def _require_preview(self) -> ConversionPreview:
        if self._state.preview is None:
            raise ValueError("Conversion preview must be available before execution can start.")
        return self._state.preview

    def _require_execution(self) -> ConversionExecution:
        if self._state.execution is None:
            raise ValueError("Conversion execution must be available before review can start.")
        return self._state.execution

    def _set_state(self, new_state: ConversionSessionScreenState) -> ConversionSessionScreenState:
        with self._lock:
            self._state = new_state
            listeners = tuple(self._listeners)
            state = self._state
        for listener in listeners:
            listener(state)
        return state


def validation_issue_items(execution: ConversionExecution) -> tuple[ValidationIssueItem, ...]:
    """Project validation issues into UI-facing issue items."""

    return tuple(
        ValidationIssueItem(
            issue_ref=execution.validation_summary.issue_ref(issue),
            code=issue.code,
            message=issue.message,
            severity=issue.severity.value,
            location=issue.location,
            tool=issue.tool,
            is_acknowledged=False,
        )
        for issue in execution.validation_summary.issues
    )


def generated_artifact_items(artifacts) -> tuple[GeneratedArtifactItem, ...]:
    """Project generated provenance artifacts into UI-facing summaries."""

    return tuple(
        GeneratedArtifactItem(
            artifact_type=artifact.artifact_type,
            location=artifact.location,
            description=artifact.description,
        )
        for artifact in artifacts
    )
