"""Qt widget for one conversion-session workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from nwbforge.domain.enums import ReviewStatus
from nwbforge.domain.models import ConversionSession
from nwbforge.ui.conversion_session import ConversionSessionScreenModel
from nwbforge.ui.models import ConversionSessionScreenState
from nwbforge.ui.qt.bridge import StateBridge


class ConversionSessionWidget(QWidget):
    """Widget bound to `ConversionSessionScreenModel`."""

    def __init__(
        self,
        screen_model: ConversionSessionScreenModel,
        parent=None,
        *,
        output_path_selector: Callable[[Path | None], Path | None] | None = None,
        artifact_opener: Callable[[Path], bool] | None = None,
        artifact_revealer: Callable[[Path], bool] | None = None,
    ) -> None:
        super().__init__(parent)
        self._screen_model = screen_model
        self._output_path_selector = output_path_selector
        self._artifact_opener = artifact_opener
        self._artifact_revealer = artifact_revealer

        self._session_label = QLabel("No session loaded.", self)
        self._pathway_label = QLabel("Not available.", self)
        self._source_count_label = QLabel("0", self)
        self._source_list = QListWidget(self)
        self._source_list.currentItemChanged.connect(self._sync_selected_source_details)
        self._source_location_label = QLabel("No source selected.", self)
        self._source_location_label.setWordWrap(True)
        self._source_role_label = QLabel("Not available.", self)
        self._source_adapter_label = QLabel("Auto-detect", self)
        self._source_media_type_label = QLabel("Not available.", self)
        self._preview_button = QPushButton("Build Preview", self)
        self._preview_button.clicked.connect(self._screen_model.start_preview)
        self._execute_button = QPushButton("Write NWB", self)
        self._execute_button.clicked.connect(self._on_execute_clicked)
        self._output_path_edit = QLineEdit(self)
        self._output_path_edit.setPlaceholderText("Output NWB path")
        self._output_path_edit.textChanged.connect(self._refresh_execute_enabled)
        self._choose_output_button = QPushButton("Choose Output...", self)
        self._choose_output_button.clicked.connect(self._choose_output_path)
        self._validation_summary_label = QLabel("Validation summary: not available.", self)
        self._review_outcome_label = QLabel("Review outcome: not available.", self)
        self._review_status_label = QLabel("Review status: not reviewed.", self)
        self._stage_value_label = QLabel("idle", self)
        self._output_value_label = QLabel("No output selected.", self)
        self._issue_count_value_label = QLabel("0 issues", self)
        self._artifact_count_value_label = QLabel("0 artifacts", self)
        self._disagreement_count_value_label = QLabel("0 metadata conflicts", self)
        self._issue_list = QListWidget(self)
        self._issue_list.itemChanged.connect(self._on_issue_item_changed)
        self._review_guidance_label = QLabel("Run preview or execution to unlock review guidance.", self)
        self._role_policy_label = QLabel(
            "Conflict precedence: primary sources override metadata sources, which override supplemental sources.",
            self,
        )
        self._role_policy_label.setWordWrap(True)
        self._acknowledgement_summary_label = QLabel("Acknowledged 0 of 0 issues.", self)
        self._reviewer_edit = QLineEdit(self)
        self._reviewer_edit.setPlaceholderText("Reviewer name")
        self._reviewer_edit.textChanged.connect(self._screen_model.set_reviewer_name)
        self._override_checkbox = QCheckBox("Override blocked completion", self)
        self._override_checkbox.toggled.connect(self._screen_model.set_override_blocks_completion)
        self._rationale_edit = QPlainTextEdit(self)
        self._rationale_edit.setPlaceholderText("Review rationale or notes")
        self._rationale_edit.textChanged.connect(self._on_rationale_changed)
        self._approve_button = QPushButton("Approve", self)
        self._approve_button.clicked.connect(lambda: self._screen_model.submit_review(ReviewStatus.APPROVED))
        self._reject_button = QPushButton("Reject", self)
        self._reject_button.clicked.connect(lambda: self._screen_model.submit_review(ReviewStatus.REJECTED))
        self._status_label = QLabel("Ready.", self)
        self._result_label = QLabel("No preview or execution yet.", self)
        self._artifact_list = QListWidget(self)
        self._artifact_list.itemSelectionChanged.connect(self._refresh_artifact_actions)
        self._disagreement_list = QListWidget(self)
        self._disagreement_list.currentItemChanged.connect(self._sync_selected_disagreement)
        self._selected_disagreement_value_label = QLabel("No metadata disagreement selected.", self)
        self._selected_disagreement_value_label.setWordWrap(True)
        self._selected_disagreement_source_list = QListWidget(self)
        self._selected_disagreement_source_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._selected_disagreement_source_list.currentItemChanged.connect(self._sync_selected_disagreement_source)
        self._selected_disagreement_notes_label = QLabel("No comparison notes.", self)
        self._selected_disagreement_notes_label.setWordWrap(True)
        self._selected_override_status_label = QLabel("No session override applied.", self)
        self._selected_override_status_label.setWordWrap(True)
        self._selected_source_override_edit = QLineEdit(self)
        self._selected_source_override_edit.setPlaceholderText("Override value for selected source")
        self._selected_source_override_edit.textChanged.connect(self._refresh_metadata_resolution_actions)
        self._use_source_value_button = QPushButton("Use Selected Source Value As Session Override", self)
        self._use_source_value_button.clicked.connect(self._apply_selected_source_as_session_override)
        self._clear_override_button = QPushButton("Clear Session Override", self)
        self._clear_override_button.clicked.connect(self._clear_selected_override)
        self._apply_source_override_button = QPushButton("Apply Source Override", self)
        self._apply_source_override_button.clicked.connect(self._apply_selected_source_override)
        self._clear_source_override_button = QPushButton("Clear Source Override", self)
        self._clear_source_override_button.clicked.connect(self._clear_selected_source_override)
        self._open_artifact_button = QPushButton("Open Selected Artifact", self)
        self._open_artifact_button.clicked.connect(self._open_selected_artifact)
        self._reveal_artifact_button = QPushButton("Open Artifact Folder", self)
        self._reveal_artifact_button.clicked.connect(self._reveal_selected_artifact)
        self._open_validation_report_button = QPushButton("Open Validation Report", self)
        self._open_validation_report_button.clicked.connect(lambda: self._open_artifact_by_type("validation_report"))
        self._open_review_artifact_button = QPushButton("Open Review Decision", self)
        self._open_review_artifact_button.clicked.connect(lambda: self._open_artifact_by_type("review_decision"))

        self._session_summary_group = QGroupBox("Session Summary", self)
        self._execution_group = QGroupBox("Execution Status", self)
        self._review_group = QGroupBox("Validation and Review", self)
        self._artifact_group = QGroupBox("Generated Artifacts", self)
        self._workspace_tabs = QTabWidget(self)

        form_layout = QFormLayout()
        form_layout.addRow("Session", self._session_label)
        form_layout.addRow("Pathway", self._pathway_label)
        form_layout.addRow("Sources", self._source_count_label)
        form_layout.addRow("Output", self._output_path_edit)
        form_layout.addRow("Reviewer", self._reviewer_edit)

        source_detail_layout = QFormLayout()
        source_detail_layout.addRow("Location", self._source_location_label)
        source_detail_layout.addRow("Role", self._source_role_label)
        source_detail_layout.addRow("Adapter", self._source_adapter_label)
        source_detail_layout.addRow("Media", self._source_media_type_label)
        self._source_detail_group = QGroupBox("Source Details", self)
        self._source_detail_group.setLayout(source_detail_layout)

        button_row = QHBoxLayout()
        button_row.addWidget(self._preview_button)
        button_row.addWidget(self._execute_button)
        button_row.addWidget(self._choose_output_button)

        review_button_row = QHBoxLayout()
        review_button_row.addWidget(self._approve_button)
        review_button_row.addWidget(self._reject_button)

        artifact_button_row = QHBoxLayout()
        artifact_button_row.addWidget(self._open_artifact_button)
        artifact_button_row.addWidget(self._reveal_artifact_button)
        artifact_button_row.addWidget(self._open_validation_report_button)
        artifact_button_row.addWidget(self._open_review_artifact_button)

        session_summary_layout = QVBoxLayout()
        session_summary_layout.addLayout(form_layout)
        session_summary_layout.addWidget(QLabel("Sources", self))
        session_summary_layout.addWidget(self._source_list, stretch=1)
        session_summary_layout.addWidget(self._source_detail_group)
        session_summary_layout.addLayout(button_row)
        self._session_summary_group.setLayout(session_summary_layout)

        run_overview_layout = QFormLayout()
        run_overview_layout.addRow("Stage", self._stage_value_label)
        run_overview_layout.addRow("Output target", self._output_value_label)
        run_overview_layout.addRow("Validation", self._issue_count_value_label)
        run_overview_layout.addRow("Metadata review", self._disagreement_count_value_label)
        run_overview_layout.addRow("Artifacts", self._artifact_count_value_label)

        execution_layout = QVBoxLayout()
        execution_layout.addLayout(run_overview_layout)
        execution_layout.addWidget(self._status_label)
        execution_layout.addWidget(self._result_label)
        execution_layout.addWidget(self._validation_summary_label)
        execution_layout.addWidget(self._review_outcome_label)
        execution_layout.addWidget(self._review_status_label)
        execution_layout.addStretch(1)
        self._execution_group.setLayout(execution_layout)

        review_layout = QVBoxLayout()
        review_layout.addWidget(self._review_guidance_label)
        review_layout.addWidget(self._role_policy_label)
        review_layout.addWidget(self._acknowledgement_summary_label)
        review_layout.addWidget(QLabel("Validation issues", self))
        review_layout.addWidget(self._issue_list, stretch=1)
        review_layout.addWidget(self._override_checkbox)
        review_layout.addWidget(QLabel("Review rationale", self))
        review_layout.addWidget(self._rationale_edit)
        review_layout.addLayout(review_button_row)
        self._review_group.setLayout(review_layout)

        artifact_layout = QVBoxLayout()
        artifact_layout.addWidget(self._artifact_list, stretch=1)
        artifact_layout.addLayout(artifact_button_row)
        self._artifact_group.setLayout(artifact_layout)

        metadata_review_page = QWidget(self)
        metadata_review_layout = QVBoxLayout(metadata_review_page)
        metadata_review_layout.addWidget(QLabel("Pending mixed-source metadata review", self))
        metadata_review_layout.addWidget(self._disagreement_list, stretch=1)
        metadata_detail_group = QGroupBox("Selected Metadata Conflict", self)
        metadata_detail_layout = QVBoxLayout(metadata_detail_group)
        metadata_detail_layout.addWidget(self._selected_disagreement_value_label)
        metadata_detail_layout.addWidget(self._selected_override_status_label)
        metadata_detail_layout.addWidget(QLabel("Source comparison", self))
        metadata_detail_layout.addWidget(self._selected_disagreement_source_list, stretch=1)
        metadata_detail_layout.addWidget(QLabel("Selected source override", self))
        metadata_detail_layout.addWidget(self._selected_source_override_edit)
        metadata_detail_layout.addWidget(QLabel("Resolution notes", self))
        metadata_detail_layout.addWidget(self._selected_disagreement_notes_label)
        metadata_resolution_row = QHBoxLayout()
        metadata_resolution_row.addWidget(self._use_source_value_button)
        metadata_resolution_row.addWidget(self._clear_override_button)
        metadata_detail_layout.addLayout(metadata_resolution_row)
        metadata_source_resolution_row = QHBoxLayout()
        metadata_source_resolution_row.addWidget(self._apply_source_override_button)
        metadata_source_resolution_row.addWidget(self._clear_source_override_button)
        metadata_detail_layout.addLayout(metadata_source_resolution_row)
        metadata_review_layout.addWidget(metadata_detail_group, stretch=1)

        run_overview_page = QWidget(self)
        run_overview_layout = QVBoxLayout(run_overview_page)
        run_overview_layout.addWidget(self._execution_group)
        run_overview_layout.addStretch(1)

        review_page = QWidget(self)
        review_page_layout = QVBoxLayout(review_page)
        review_page_layout.addWidget(self._review_group)

        artifact_page = QWidget(self)
        artifact_page_layout = QVBoxLayout(artifact_page)
        artifact_page_layout.addWidget(self._artifact_group)

        self._workspace_tabs.addTab(run_overview_page, "Run Overview")
        self._workspace_tabs.addTab(review_page, "Review Workspace")
        self._workspace_tabs.addTab(metadata_review_page, "Metadata Review")
        self._workspace_tabs.addTab(artifact_page, "Artifacts")

        right_column = QWidget(self)
        right_column_layout = QVBoxLayout(right_column)
        right_column_layout.addWidget(self._workspace_tabs)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(self._session_summary_group)
        splitter.addWidget(right_column)
        splitter.setChildrenCollapsible(False)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        self._splitter = splitter

        layout = QVBoxLayout(self)
        layout.addWidget(splitter)

        self._bridge = StateBridge(self)
        self._bridge.state_changed.connect(self._apply_state)
        self._screen_model.subscribe(self._bridge.publish)

    def load_session(self, session: ConversionSession) -> None:
        self._screen_model.load_session(session)

    def _apply_state(self, state: ConversionSessionScreenState) -> None:
        if state.session is None:
            self._session_label.setText("No session loaded.")
            self._pathway_label.setText("Not available.")
            self._source_count_label.setText("0")
        else:
            self._session_label.setText(f"{state.session.session_id} ({state.session.status.value})")
            self._pathway_label.setText(state.session.pathway.value)
            self._source_count_label.setText(str(len(state.sources)))

        self._sync_sources(state)
        self._sync_validation_issues(state)
        self._sync_metadata_disagreements(state)
        self._sync_generated_artifacts(state)

        if state.user_error is not None:
            self._status_label.setText(state.user_error.message)
        elif state.progress_event is not None:
            self._status_label.setText(state.progress_event.message)
        elif state.recovery_message is not None:
            self._status_label.setText(state.recovery_message)
        elif state.review_message is not None:
            self._status_label.setText(state.review_message)
        elif state.execution is not None:
            self._status_label.setText("Execution finished.")
        elif state.preview is not None:
            self._status_label.setText("Preview ready.")
        else:
            self._status_label.setText("Ready.")

        if state.execution is not None:
            self._result_label.setText(f"Execution status: {state.execution.session.status.value}")
        elif state.preview is not None:
            self._result_label.setText(f"Preview status: {state.preview.session.status.value}")
        elif state.recovery_message is not None and state.session is not None:
            self._result_label.setText(
                f"Recovered session status: {state.session.status.value}"
            )
        else:
            self._result_label.setText("No preview or execution yet.")

        self._validation_summary_label.setText(self._validation_summary_text(state))
        self._review_outcome_label.setText(self._review_outcome_text(state))
        self._review_status_label.setText(self._review_status_text(state))
        self._stage_value_label.setText(self._stage_text(state))
        self._output_value_label.setText(self._output_text(state))
        self._issue_count_value_label.setText(self._issue_count_text(state))
        self._artifact_count_value_label.setText(self._artifact_count_text(state))
        self._disagreement_count_value_label.setText(self._disagreement_count_text(state))
        self._review_guidance_label.setText(self._review_guidance_text(state))
        self._acknowledgement_summary_label.setText(self._acknowledgement_summary_text(state))

        if state.output_path is not None and self._output_path_edit.text() != str(state.output_path):
            self._output_path_edit.setText(str(state.output_path))

        with QSignalBlocker(self._reviewer_edit):
            if self._reviewer_edit.text() != state.reviewer_name:
                self._reviewer_edit.setText(state.reviewer_name)

        with QSignalBlocker(self._override_checkbox):
            self._override_checkbox.setChecked(state.override_blocks_completion)

        with QSignalBlocker(self._rationale_edit):
            if self._rationale_edit.toPlainText() != state.review_rationale:
                self._rationale_edit.setPlainText(state.review_rationale)

        self._preview_button.setEnabled(state.can_run_preview)
        self._choose_output_button.setEnabled(state.session is not None and not state.is_execution_running)
        self._refresh_execute_enabled()
        self._approve_button.setEnabled(state.can_submit_review)
        self._reject_button.setEnabled(state.can_submit_review)
        self._override_checkbox.setEnabled(state.execution is not None)
        self._issue_list.setEnabled(state.execution is not None)
        self._rationale_edit.setEnabled(state.execution is not None)
        self._reviewer_edit.setEnabled(state.execution is not None)
        self._refresh_metadata_resolution_actions()
        self._refresh_artifact_actions()
        self._sync_workspace_tab(state)

    def _sync_sources(self, state: ConversionSessionScreenState) -> None:
        self._source_list.clear()
        for source in state.sources:
            item = QListWidgetItem(f"{source.label} [{source.source_type}]")
            item.setToolTip(str(source.location))
            item.setData(Qt.ItemDataRole.UserRole, source.source_id)
            self._source_list.addItem(item)
        if self._source_list.count() > 0:
            self._source_list.setCurrentRow(0)
        else:
            self._sync_selected_source_details()

    def _sync_selected_source_details(self, *_args) -> None:
        selected_item = self._source_list.currentItem()
        if selected_item is None:
            self._source_location_label.setText("No source selected.")
            self._source_role_label.setText("Not available.")
            self._source_adapter_label.setText("Auto-detect")
            self._source_media_type_label.setText("Not available.")
            return

        source_id = selected_item.data(Qt.ItemDataRole.UserRole)
        selected_source = next(
            (source for source in self._screen_model.state.sources if source.source_id == source_id),
            None,
        )
        if selected_source is None:
            self._source_location_label.setText("No source selected.")
            self._source_role_label.setText("Not available.")
            self._source_adapter_label.setText("Auto-detect")
            self._source_media_type_label.setText("Not available.")
            return

        self._source_location_label.setText(str(selected_source.location))
        self._source_role_label.setText(selected_source.role)
        self._source_adapter_label.setText(selected_source.adapter_hint or "Auto-detect")
        self._source_media_type_label.setText(selected_source.media_type or "Not available.")

    def _sync_validation_issues(self, state: ConversionSessionScreenState) -> None:
        existing = {
            self._issue_list.item(i).data(Qt.ItemDataRole.UserRole): self._issue_list.item(i)
            for i in range(self._issue_list.count())
        }
        seen_refs = set()
        for issue in state.validation_issues:
            seen_refs.add(issue.issue_ref)
            item = existing.get(issue.issue_ref)
            label = f"[{issue.severity}] {issue.message}"
            if item is None:
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, issue.issue_ref)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                self._issue_list.addItem(item)
            item.setText(label)
            tooltip_parts = [issue.code]
            if issue.location:
                tooltip_parts.append(issue.location)
            if issue.tool:
                tooltip_parts.append(issue.tool)
            item.setToolTip(" | ".join(tooltip_parts))
            with QSignalBlocker(self._issue_list):
                item.setCheckState(Qt.CheckState.Checked if issue.is_acknowledged else Qt.CheckState.Unchecked)

        for index in reversed(range(self._issue_list.count())):
            item = self._issue_list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) not in seen_refs:
                self._issue_list.takeItem(index)

    def _sync_generated_artifacts(self, state: ConversionSessionScreenState) -> None:
        self._artifact_list.clear()
        for artifact in state.generated_artifacts:
            label = f"[{artifact.artifact_type}] {artifact.location.name}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, str(artifact.location))
            tooltip = str(artifact.location)
            if artifact.description:
                tooltip = f"{artifact.description}\n{tooltip}"
            item.setToolTip(tooltip)
            self._artifact_list.addItem(item)
        self._refresh_artifact_actions()

    def _sync_metadata_disagreements(self, state: ConversionSessionScreenState) -> None:
        selected_item = self._disagreement_list.currentItem()
        selected_key = selected_item.data(Qt.ItemDataRole.UserRole) if selected_item is not None else None
        self._disagreement_list.clear()
        for disagreement in state.metadata_disagreements:
            item = QListWidgetItem(f"{disagreement.canonical_key} -> {disagreement.resolved_value}")
            item.setData(Qt.ItemDataRole.UserRole, disagreement.canonical_key)
            item.setToolTip(
                f"Resolved from {disagreement.resolved_origin} value using source(s): "
                f"{', '.join(disagreement.source_ids) or 'session merge'}"
            )
            self._disagreement_list.addItem(item)
        if self._disagreement_list.count() == 0:
            self._sync_selected_disagreement()
            return
        restored_row = 0
        if selected_key is not None:
            for row in range(self._disagreement_list.count()):
                if self._disagreement_list.item(row).data(Qt.ItemDataRole.UserRole) == selected_key:
                    restored_row = row
                    break
        self._disagreement_list.setCurrentRow(restored_row)

    def _sync_selected_disagreement(self, *_args) -> None:
        selected_item = self._disagreement_list.currentItem()
        if selected_item is None:
            self._selected_disagreement_value_label.setText("No metadata disagreement selected.")
            self._selected_disagreement_source_list.clear()
            self._selected_disagreement_notes_label.setText("No comparison notes.")
            self._selected_override_status_label.setText("No session override applied.")
            with QSignalBlocker(self._selected_source_override_edit):
                self._selected_source_override_edit.setText("")
            self._refresh_metadata_resolution_actions()
            return
        canonical_key = selected_item.data(Qt.ItemDataRole.UserRole)
        disagreement = next(
            (
                item
                for item in self._screen_model.state.metadata_disagreements
                if item.canonical_key == canonical_key
            ),
            None,
        )
        if disagreement is None:
            self._selected_disagreement_value_label.setText("No metadata disagreement selected.")
            self._selected_disagreement_source_list.clear()
            self._selected_disagreement_notes_label.setText("No comparison notes.")
            self._selected_override_status_label.setText("No session override applied.")
            with QSignalBlocker(self._selected_source_override_edit):
                self._selected_source_override_edit.setText("")
            self._refresh_metadata_resolution_actions()
            return
        self._selected_disagreement_value_label.setText(
            f"{disagreement.canonical_key}\nResolved value: {disagreement.resolved_value}\n"
            f"Origin: {disagreement.resolved_origin}"
        )
        self._selected_disagreement_source_list.clear()
        for source_value in disagreement.source_values:
            item = QListWidgetItem(
                f"[{source_value.role}] {source_value.source_label}: {source_value.value}"
                + (
                    f" | source override: {source_value.override_value}"
                    if source_value.override_value is not None
                    else ""
                )
            )
            item.setToolTip(f"{source_value.extracted_key} ({source_value.source_id})")
            item.setData(Qt.ItemDataRole.UserRole, source_value.source_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, source_value.value)
            self._selected_disagreement_source_list.addItem(item)
        if self._selected_disagreement_source_list.count() > 0:
            self._selected_disagreement_source_list.setCurrentRow(0)
        note_lines = list(disagreement.notes)
        note_lines.extend(disagreement.resolution_notes)
        if note_lines:
            self._selected_disagreement_notes_label.setText("\n".join(note_lines))
        else:
            self._selected_disagreement_notes_label.setText("No comparison notes.")
        override_lines = []
        if disagreement.session_override_value is not None:
            override_lines.append(f"Session override: {disagreement.session_override_value}")
        source_override_lines = [
            f"{source_value.source_label}: {source_value.override_value}"
            for source_value in disagreement.source_values
            if source_value.override_value is not None
        ]
        if source_override_lines:
            override_lines.append("Source overrides: " + "; ".join(source_override_lines))
        self._selected_override_status_label.setText(
            "\n".join(override_lines) if override_lines else "No session or source overrides applied."
        )
        self._sync_selected_disagreement_source()
        self._refresh_metadata_resolution_actions()

    def _sync_selected_disagreement_source(self, *_args) -> None:
        selected_source = self._selected_disagreement_source()
        with QSignalBlocker(self._selected_source_override_edit):
            self._selected_source_override_edit.setText(
                selected_source.override_value if selected_source is not None and selected_source.override_value is not None else ""
            )
        self._refresh_metadata_resolution_actions()

    @staticmethod
    def _validation_summary_text(state: ConversionSessionScreenState) -> str:
        summary = state.execution.validation_summary if state.execution is not None else state.persisted_validation_summary
        if summary is None:
            return "Validation summary: not available."
        return (
            "Validation summary: "
            f"{len(summary.errors())} errors, {len(summary.warnings())} warnings"
        )

    @staticmethod
    def _review_outcome_text(state: ConversionSessionScreenState) -> str:
        outcome = state.execution.review_outcome if state.execution is not None else state.persisted_review_outcome
        if outcome is None:
            return "Review outcome: not available."
        return (
            "Review outcome: "
            f"{outcome.status.value}"
            f" | manual review={outcome.requires_manual_review}"
            f" | blocks completion={outcome.blocks_completion}"
        )

    @staticmethod
    def _review_status_text(state: ConversionSessionScreenState) -> str:
        if state.last_review_submission is not None:
            record = state.last_review_submission.review_record
            return f"Review status: {record.decision.value} by {record.reviewer}"
        if state.review_message:
            return f"Review status: {state.review_message}"
        return "Review status: not reviewed."

    @staticmethod
    def _stage_text(state: ConversionSessionScreenState) -> str:
        if state.progress_event is not None:
            return state.progress_event.stage.value
        if state.execution is not None:
            return state.execution.session.status.value
        if state.preview is not None:
            return state.preview.session.status.value
        if state.session is not None:
            return state.session.status.value
        return "idle"

    @staticmethod
    def _output_text(state: ConversionSessionScreenState) -> str:
        if state.output_path is None:
            return "No output selected."
        return str(state.output_path)

    @staticmethod
    def _issue_count_text(state: ConversionSessionScreenState) -> str:
        if state.execution is None:
            return "Not available."
        issue_count = len(state.validation_issues)
        warning_count = len([issue for issue in state.validation_issues if issue.severity == "warning"])
        error_count = len([issue for issue in state.validation_issues if issue.severity == "error"])
        return f"{issue_count} issues ({error_count} errors, {warning_count} warnings)"

    @staticmethod
    def _artifact_count_text(state: ConversionSessionScreenState) -> str:
        count = len(state.generated_artifacts)
        return f"{count} artifacts"

    @staticmethod
    def _disagreement_count_text(state: ConversionSessionScreenState) -> str:
        count = len(state.metadata_disagreements)
        return f"{count} metadata conflicts"

    @staticmethod
    def _review_guidance_text(state: ConversionSessionScreenState) -> str:
        if state.execution is None:
            return "Run preview or execution to unlock review guidance."
        outcome = state.execution.review_outcome
        if outcome.blocks_completion:
            return (
                "Completion is blocked. Provide rationale and enable override only if the result is acceptable."
            )
        if outcome.requires_manual_review:
            return (
                "Manual review is required. Conflicting fields retain primary-source values first, then metadata, "
                "then supplemental values. Acknowledge issues, add rationale if needed, then approve or reject."
            )
        return "No blocking review actions are currently required."

    @staticmethod
    def _acknowledgement_summary_text(state: ConversionSessionScreenState) -> str:
        total_issues = len(state.validation_issues)
        acknowledged = len(state.acknowledged_issue_refs)
        return f"Acknowledged {acknowledged} of {total_issues} issues."

    def _refresh_execute_enabled(self) -> None:
        state = self._screen_model.state
        self._execute_button.setEnabled(state.can_run_execution and bool(self._output_path_edit.text().strip()))

    def _refresh_metadata_resolution_actions(self, *_args) -> None:
        disagreement = self._selected_disagreement()
        selected_source_item = self._selected_disagreement_source_list.currentItem()
        selected_source = self._selected_disagreement_source()
        self._use_source_value_button.setEnabled(disagreement is not None and selected_source_item is not None)
        self._clear_override_button.setEnabled(
            disagreement is not None and disagreement.session_override_value is not None
        )
        self._selected_source_override_edit.setEnabled(disagreement is not None and selected_source_item is not None)
        self._apply_source_override_button.setEnabled(
            disagreement is not None
            and selected_source_item is not None
            and bool(self._selected_source_override_edit.text().strip())
        )
        self._clear_source_override_button.setEnabled(
            selected_source is not None and selected_source.override_value is not None
        )

    def _selected_disagreement(self):
        selected_item = self._disagreement_list.currentItem()
        if selected_item is None:
            return None
        canonical_key = selected_item.data(Qt.ItemDataRole.UserRole)
        for disagreement in self._screen_model.state.metadata_disagreements:
            if disagreement.canonical_key == canonical_key:
                return disagreement
        return None

    def _selected_disagreement_source(self):
        disagreement = self._selected_disagreement()
        source_item = self._selected_disagreement_source_list.currentItem()
        if disagreement is None or source_item is None:
            return None
        source_id = source_item.data(Qt.ItemDataRole.UserRole)
        if source_id is None:
            return None
        for source_value in disagreement.source_values:
            if source_value.source_id == source_id:
                return source_value
        return None

    def _apply_selected_source_as_session_override(self) -> None:
        disagreement = self._selected_disagreement()
        source_item = self._selected_disagreement_source_list.currentItem()
        if disagreement is None or source_item is None:
            return
        selected_value = source_item.data(Qt.ItemDataRole.UserRole + 1)
        if selected_value is None:
            return
        self._screen_model.apply_session_override(disagreement.canonical_key, str(selected_value))

    def _apply_selected_source_override(self) -> None:
        disagreement = self._selected_disagreement()
        selected_source = self._selected_disagreement_source()
        value = self._selected_source_override_edit.text().strip()
        if disagreement is None or selected_source is None or not value:
            return
        self._screen_model.apply_source_override(selected_source.source_id, disagreement.canonical_key, value)

    def _clear_selected_source_override(self) -> None:
        disagreement = self._selected_disagreement()
        selected_source = self._selected_disagreement_source()
        if disagreement is None or selected_source is None:
            return
        self._screen_model.clear_source_override(selected_source.source_id, disagreement.canonical_key)

    def _clear_selected_override(self) -> None:
        disagreement = self._selected_disagreement()
        if disagreement is None:
            return
        self._screen_model.clear_session_override(disagreement.canonical_key)

    def _on_execute_clicked(self) -> None:
        output_text = self._output_path_edit.text().strip()
        if not output_text:
            self._status_label.setText("Output path is required before writing NWB.")
            return
        self._screen_model.start_execution(Path(output_text))

    def _choose_output_path(self) -> None:
        if self._output_path_selector is None:
            return
        current_text = self._output_path_edit.text().strip()
        selected = self._output_path_selector(Path(current_text) if current_text else None)
        if selected is None:
            return
        self._output_path_edit.setText(str(selected))

    def _on_rationale_changed(self) -> None:
        self._screen_model.set_review_rationale(self._rationale_edit.toPlainText())

    def _on_issue_item_changed(self, *_args) -> None:
        for index in range(self._issue_list.count()):
            item = self._issue_list.item(index)
            self._screen_model.set_issue_acknowledged(
                item.data(Qt.ItemDataRole.UserRole),
                item.checkState() == Qt.CheckState.Checked,
            )

    def _refresh_artifact_actions(self) -> None:
        has_selection = self._selected_artifact_path() is not None
        self._open_artifact_button.setEnabled(has_selection)
        self._reveal_artifact_button.setEnabled(has_selection)
        self._open_validation_report_button.setEnabled(self._artifact_path_for_type("validation_report") is not None)
        self._open_review_artifact_button.setEnabled(self._artifact_path_for_type("review_decision") is not None)

    def _sync_workspace_tab(self, state: ConversionSessionScreenState) -> None:
        if state.execution is None:
            if state.metadata_disagreements:
                self._workspace_tabs.setCurrentIndex(2)
                return
            self._workspace_tabs.setCurrentIndex(0)
            return
        if state.validation_issues:
            self._workspace_tabs.setCurrentIndex(1)
            return
        if state.metadata_disagreements:
            self._workspace_tabs.setCurrentIndex(2)
            return
        if state.generated_artifacts:
            self._workspace_tabs.setCurrentIndex(3)
            return
        self._workspace_tabs.setCurrentIndex(0)

    def _selected_artifact_path(self) -> Path | None:
        item = self._artifact_list.currentItem()
        if item is None:
            return None
        path_text = item.data(Qt.ItemDataRole.UserRole)
        return Path(path_text) if path_text else None

    def _open_selected_artifact(self) -> None:
        path = self._selected_artifact_path()
        if path is None:
            return
        if self._artifact_opener is not None:
            self._artifact_opener(path)
            return

    def _reveal_selected_artifact(self) -> None:
        path = self._selected_artifact_path()
        if path is None:
            return
        if self._artifact_revealer is not None:
            self._artifact_revealer(path)
            return

    def _artifact_path_for_type(self, artifact_type: str) -> Path | None:
        for index in range(self._artifact_list.count()):
            item = self._artifact_list.item(index)
            path_text = item.data(Qt.ItemDataRole.UserRole)
            if item.text().startswith(f"[{artifact_type}]") and path_text:
                return Path(path_text)
        return None

    def _open_artifact_by_type(self, artifact_type: str) -> None:
        path = self._artifact_path_for_type(artifact_type)
        if path is None:
            return
        if self._artifact_opener is not None:
            self._artifact_opener(path)
            return
