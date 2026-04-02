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
from nwbforge.domain.models import ConversionSession, NormalizedMetadataBundle, SessionSnapshot
from nwbforge.normalization.rules import DEFAULT_FIELD_ALIASES, NormalizationRuleSet
from nwbforge.ui.errors import DefaultUiErrorPresenter, UiErrorPresenter
from nwbforge.ui.models import (
    ConversionSessionScreenState,
    ConversionSessionStateListener,
    GeneratedArtifactItem,
    MetadataDisagreementItem,
    MetadataDisagreementSourceItem,
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

    def apply_session_override(self, canonical_key: str, value: str) -> ConversionSessionScreenState:
        session = self._require_session()
        next_overrides = dict(session.metadata_overrides)
        next_overrides[canonical_key] = value
        updated_session = replace(session, metadata_overrides=next_overrides)
        return self._set_state(
            replace(
                self._state,
                session=updated_session,
                sources=conversion_source_items(updated_session.sources),
                preview=None,
                execution=None,
                generated_artifacts=(),
                validation_issues=(),
                metadata_disagreements=(),
                progress_event=None,
                last_review_submission=None,
                review_message=f"Applied session override for {canonical_key}. Rebuild preview to refresh results.",
                recovery_message=None,
                error_message=None,
                user_error=None,
                persisted_validation_summary=None,
                persisted_review_outcome=None,
            )
        )

    def clear_session_override(self, canonical_key: str) -> ConversionSessionScreenState:
        session = self._require_session()
        if canonical_key not in session.metadata_overrides:
            return self._state
        next_overrides = dict(session.metadata_overrides)
        next_overrides.pop(canonical_key, None)
        updated_session = replace(session, metadata_overrides=next_overrides)
        return self._set_state(
            replace(
                self._state,
                session=updated_session,
                sources=conversion_source_items(updated_session.sources),
                preview=None,
                execution=None,
                generated_artifacts=(),
                validation_issues=(),
                metadata_disagreements=(),
                progress_event=None,
                last_review_submission=None,
                review_message=f"Cleared session override for {canonical_key}. Rebuild preview to refresh results.",
                recovery_message=None,
                error_message=None,
                user_error=None,
                persisted_validation_summary=None,
                persisted_review_outcome=None,
            )
        )

    def apply_source_override(
        self,
        source_id: str,
        canonical_key: str,
        value: str,
    ) -> ConversionSessionScreenState:
        session = self._require_session()
        next_source_overrides = {
            str(existing_source_id): dict(overrides)
            for existing_source_id, overrides in session.source_metadata_overrides.items()
        }
        source_overrides = dict(next_source_overrides.get(source_id, {}))
        source_overrides[canonical_key] = value
        next_source_overrides[source_id] = source_overrides
        updated_session = replace(session, source_metadata_overrides=next_source_overrides)
        return self._set_state(
            replace(
                self._state,
                session=updated_session,
                sources=conversion_source_items(updated_session.sources),
                preview=None,
                execution=None,
                generated_artifacts=(),
                validation_issues=(),
                metadata_disagreements=(),
                progress_event=None,
                last_review_submission=None,
                review_message=(
                    f"Applied source override for {canonical_key} on {source_id}. "
                    "Rebuild preview to refresh results."
                ),
                recovery_message=None,
                error_message=None,
                user_error=None,
                persisted_validation_summary=None,
                persisted_review_outcome=None,
            )
        )

    def clear_source_override(
        self,
        source_id: str,
        canonical_key: str,
    ) -> ConversionSessionScreenState:
        session = self._require_session()
        next_source_overrides = {
            str(existing_source_id): dict(overrides)
            for existing_source_id, overrides in session.source_metadata_overrides.items()
        }
        source_overrides = dict(next_source_overrides.get(source_id, {}))
        if canonical_key not in source_overrides:
            return self._state
        source_overrides.pop(canonical_key, None)
        if source_overrides:
            next_source_overrides[source_id] = source_overrides
        else:
            next_source_overrides.pop(source_id, None)
        updated_session = replace(session, source_metadata_overrides=next_source_overrides)
        return self._set_state(
            replace(
                self._state,
                session=updated_session,
                sources=conversion_source_items(updated_session.sources),
                preview=None,
                execution=None,
                generated_artifacts=(),
                validation_issues=(),
                metadata_disagreements=(),
                progress_event=None,
                last_review_submission=None,
                review_message=(
                    f"Cleared source override for {canonical_key} on {source_id}. "
                    "Rebuild preview to refresh results."
                ),
                recovery_message=None,
                error_message=None,
                user_error=None,
                persisted_validation_summary=None,
                persisted_review_outcome=None,
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
                metadata_disagreements=metadata_disagreement_items(preview),
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
                metadata_disagreements=metadata_disagreement_items(execution.preview),
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
            metadata_disagreements=(),
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


def metadata_disagreement_items(preview: ConversionPreview) -> tuple[MetadataDisagreementItem, ...]:
    """Project pending normalized metadata conflicts into a reviewable UI workspace."""

    rules = NormalizationRuleSet(DEFAULT_FIELD_ALIASES)
    source_index = {source.source_id: source for source in preview.session.sources}
    extracted_by_canonical: dict[str, list[MetadataDisagreementSourceItem]] = {}
    for result in preview.extraction_results:
        source = source_index.get(result.source_id)
        source_label = source.label if source is not None else result.source_id
        source_role = source.role if source is not None else "unknown"
        for field in result.fields.values():
            canonical_key = rules.canonical_key_for(field.key) or field.key.strip().lower().replace("-", "_")
            override_value = preview.session.source_metadata_overrides.get(result.source_id, {}).get(canonical_key)
            extracted_by_canonical.setdefault(canonical_key, []).append(
                MetadataDisagreementSourceItem(
                    source_id=result.source_id,
                    source_label=source_label,
                    role=source_role,
                    extracted_key=field.key,
                    value=str(field.value),
                    override_value=override_value,
                )
            )

    items: list[MetadataDisagreementItem] = []
    for canonical_key, normalized_value in _pending_review_entries(preview.normalized_metadata):
        source_values = tuple(extracted_by_canonical.get(canonical_key, ()))
        items.append(
            MetadataDisagreementItem(
                canonical_key=canonical_key,
                resolved_value=str(normalized_value.value),
                resolved_origin=normalized_value.origin.value,
                source_ids=normalized_value.source_ids,
                notes=normalized_value.notes,
                source_values=source_values,
                session_override_value=preview.session.metadata_overrides.get(canonical_key),
                resolution_notes=_resolution_notes(
                    canonical_key=canonical_key,
                    source_values=source_values,
                    session_override_value=preview.session.metadata_overrides.get(canonical_key),
                ),
                pending_resolution=normalized_value.review_status is ReviewStatus.NEEDS_REVIEW,
            )
        )
    return tuple(items)


def _resolution_notes(
    *,
    canonical_key: str,
    source_values: tuple[MetadataDisagreementSourceItem, ...],
    session_override_value: str | None,
) -> tuple[str, ...]:
    notes: list[str] = []
    if session_override_value is not None:
        notes.append(f"Session override active for {canonical_key}: {session_override_value}")
    for source_value in source_values:
        if source_value.override_value is not None:
            notes.append(
                f"Source override active for {source_value.source_label} ({source_value.source_id}): "
                f"{source_value.override_value}"
            )
    return tuple(notes)


def _pending_review_entries(bundle: NormalizedMetadataBundle) -> tuple[tuple[str, object], ...]:
    entries: list[tuple[str, object]] = []

    def add_entry(key: str, value) -> None:
        if value is not None and getattr(value, "needs_review", False):
            entries.append((key, value))

    for field_name in ("subject_id", "species", "sex", "age", "date_of_birth", "description", "genotype", "strain"):
        add_entry(f"subject.{field_name}", getattr(bundle.subject, field_name))
    for field_name in (
        "session_id",
        "session_description",
        "experiment_description",
        "start_time",
        "experimenter",
        "institution",
        "lab",
    ):
        add_entry(f"session.{field_name}", getattr(bundle.session, field_name))
    for index, keyword in enumerate(bundle.session.keywords):
        add_entry(f"session.keywords.{index}", keyword)
    for key, value in bundle.additional_metadata.items():
        add_entry(key, value)
    for device in bundle.devices:
        add_entry(f"devices.{device.device_id}.name", device.name)
        add_entry(f"devices.{device.device_id}.description", device.description)
        add_entry(f"devices.{device.device_id}.manufacturer", device.manufacturer)
        for key, value in device.additional_fields.items():
            add_entry(f"devices.{device.device_id}.{key}", value)
    for stream in bundle.acquisition_streams:
        add_entry(f"acquisition_streams.{stream.stream_id}.name", stream.name)
        add_entry(f"acquisition_streams.{stream.stream_id}.description", stream.description)
        add_entry(f"acquisition_streams.{stream.stream_id}.start_time", stream.start_time)
        add_entry(f"acquisition_streams.{stream.stream_id}.end_time", stream.end_time)
        for key, value in stream.metadata.items():
            add_entry(f"acquisition_streams.{stream.stream_id}.{key}", value)
    for table in bundle.time_interval_tables:
        add_entry(f"time_intervals.{table.table_id}.table_name", table.table_name)
        add_entry(f"time_intervals.{table.table_id}.table_description", table.table_description)
        for row in table.rows:
            add_entry(f"time_intervals.{table.table_id}.rows.{row.row_id}.start_time", row.start_time)
            add_entry(f"time_intervals.{table.table_id}.rows.{row.row_id}.stop_time", row.stop_time)
            for key, value in row.metadata.items():
                add_entry(f"time_intervals.{table.table_id}.rows.{row.row_id}.{key}", value)

    return tuple(entries)


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
