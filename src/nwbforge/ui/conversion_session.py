"""Toolkit-agnostic conversion-session screen model."""

from __future__ import annotations

from concurrent.futures import Future
from dataclasses import replace
from pathlib import Path
from threading import Lock

from nwbforge.app.services import ExecutionReviewService
from nwbforge.app.services.persistence import SessionPersistenceService
from nwbforge.app.services.models import ConversionExecution, ConversionPreview, ReviewSubmission
from nwbforge.app.runtime import ConversionExecutor
from nwbforge.domain.enums import ReviewStatus
from nwbforge.domain.models import ConversionSession, SessionSnapshot
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
        persistence_service: SessionPersistenceService | None = None,
        error_presenter: UiErrorPresenter | None = None,
    ) -> None:
        self._executor = executor
        self._review_service = review_service
        self._persistence_service = persistence_service
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
        base_state = ConversionSessionScreenState(
            session=session,
            sources=conversion_source_items(session.sources),
            generated_artifacts=(),
            error_message=None,
            review_message=None,
            recovery_message=None,
            user_error=None,
        )
        return self._set_state(self._recover_state(base_state))

    def clear_session(self) -> ConversionSessionScreenState:
        return self._set_state(ConversionSessionScreenState())

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
                recovery_message=None,
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
                recovery_message=None,
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

    def set_output_path(self, output_path: Path | None) -> ConversionSessionScreenState:
        return self._set_state(
            replace(
                self._state,
                output_path=output_path,
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
                recovery_message=None,
                error_message=None,
                user_error=None,
                persisted_validation_summary=submission.execution.validation_summary,
                persisted_review_outcome=submission.execution.review_outcome,
            )
        )
        self._persist_review_submission(submission)
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
                recovery_message=None,
                is_preview_running=False,
                error_message=None,
                user_error=None,
                persisted_validation_summary=None,
                persisted_review_outcome=None,
            )
        )
        self._persist_preview(preview)

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
                recovery_message=None,
                is_execution_running=False,
                error_message=None,
                user_error=None,
                persisted_validation_summary=execution.validation_summary,
                persisted_review_outcome=execution.review_outcome,
            )
        )
        self._persist_execution(execution)

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

    def _persist_preview(self, preview: ConversionPreview) -> None:
        if self._persistence_service is None:
            return
        try:
            self._persistence_service.persist_preview(preview)
        except Exception as exc:
            user_error = self._error_presenter.present(exc)
            self._set_state(
                replace(
                    self._state,
                    error_message=f"Preview completed, but state persistence failed: {user_error.message}",
                    user_error=user_error,
                )
            )

    def _persist_execution(self, execution: ConversionExecution) -> None:
        if self._persistence_service is None:
            return
        try:
            self._persistence_service.persist_execution(execution)
        except Exception as exc:
            user_error = self._error_presenter.present(exc)
            self._set_state(
                replace(
                    self._state,
                    error_message=f"Execution completed, but state persistence failed: {user_error.message}",
                    user_error=user_error,
                )
            )

    def _persist_review_submission(self, submission: ReviewSubmission) -> None:
        if self._persistence_service is None:
            return
        try:
            self._persistence_service.persist_review_submission(submission)
        except Exception as exc:
            user_error = self._error_presenter.present(exc)
            self._set_state(
                replace(
                    self._state,
                    error_message=f"Review completed, but state persistence failed: {user_error.message}",
                    user_error=user_error,
                )
            )

    def _recover_state(self, base_state: ConversionSessionScreenState) -> ConversionSessionScreenState:
        if self._persistence_service is None or base_state.session is None:
            return base_state
        try:
            snapshot = self._persistence_service.load(base_state.session.session_id)
        except Exception as exc:
            user_error = self._error_presenter.present(exc)
            return replace(
                base_state,
                error_message=f"Session loaded, but saved state recovery failed: {user_error.message}",
                user_error=user_error,
            )
        if snapshot is None:
            return base_state
        return replace(
            base_state,
            session=snapshot.session,
            sources=conversion_source_items(snapshot.session.sources),
            output_path=recovered_output_path(snapshot),
            generated_artifacts=generated_artifact_items(
                snapshot.provenance_record.generated_artifacts if snapshot.provenance_record is not None else ()
            ),
            validation_issues=validation_issue_items_from_snapshot(snapshot),
            reviewer_name=snapshot.review_record.reviewer if snapshot.review_record is not None else "",
            review_rationale=snapshot.review_record.rationale or "" if snapshot.review_record is not None else "",
            override_blocks_completion=(
                snapshot.review_record.override_blocks_completion if snapshot.review_record is not None else False
            ),
            review_message=recovered_review_message(snapshot),
            recovery_message="Recovered latest saved session state.",
            persisted_validation_summary=snapshot.validation_summary,
            persisted_review_outcome=snapshot.review_outcome,
        )


def validation_issue_items(execution: ConversionExecution) -> tuple[ValidationIssueItem, ...]:
    """Project validation issues into UI-facing issue items."""

    return validation_issue_items_from_snapshot(
        SessionSnapshot(
            session=execution.session,
            validation_summary=execution.validation_summary,
        )
    )


def validation_issue_items_from_snapshot(snapshot: SessionSnapshot) -> tuple[ValidationIssueItem, ...]:
    """Project snapshot validation issues into UI-facing acknowledgement items."""

    summary = snapshot.validation_summary
    if summary is None:
        return ()
    acknowledged_issue_refs = (
        snapshot.review_record.acknowledged_issue_refs if snapshot.review_record is not None else ()
    )
    return tuple(
        ValidationIssueItem(
            issue_ref=summary.issue_ref(issue),
            code=issue.code,
            message=issue.message,
            severity=issue.severity.value,
            location=issue.location,
            tool=issue.tool,
            is_acknowledged=summary.issue_ref(issue) in acknowledged_issue_refs,
        )
        for issue in summary.issues
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


def recovered_review_message(snapshot: SessionSnapshot) -> str | None:
    """Summarize recovered review state for UI display."""

    if snapshot.review_record is not None:
        return (
            f"Recovered review {snapshot.review_record.decision.value} "
            f"by {snapshot.review_record.reviewer}."
        )
    if snapshot.validation_summary is not None or snapshot.provenance_record is not None:
        return "Recovered saved validation and artifact state."
    return "Recovered saved preview state."


def recovered_output_path(snapshot: SessionSnapshot) -> Path | None:
    """Best-effort NWB output path recovered from snapshot provenance."""

    if snapshot.provenance_record is None:
        return None
    for artifact in snapshot.provenance_record.generated_artifacts:
        if artifact.artifact_type == "nwb":
            return artifact.location
    return None
