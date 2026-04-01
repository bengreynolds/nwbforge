"""Qt widget for one conversion-session workflow."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
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

    def __init__(self, screen_model: ConversionSessionScreenModel, parent=None) -> None:
        super().__init__(parent)
        self._screen_model = screen_model

        self._session_label = QLabel("No session loaded.", self)
        self._source_list = QListWidget(self)
        self._preview_button = QPushButton("Build Preview", self)
        self._preview_button.clicked.connect(self._screen_model.start_preview)
        self._execute_button = QPushButton("Write NWB", self)
        self._execute_button.clicked.connect(self._on_execute_clicked)
        self._output_path_edit = QLineEdit(self)
        self._output_path_edit.setPlaceholderText("Output NWB path")
        self._output_path_edit.textChanged.connect(self._refresh_execute_enabled)
        self._validation_summary_label = QLabel("Validation summary: not available.", self)
        self._review_outcome_label = QLabel("Review outcome: not available.", self)
        self._review_status_label = QLabel("Review status: not reviewed.", self)
        self._issue_list = QListWidget(self)
        self._issue_list.itemChanged.connect(self._on_issue_item_changed)
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

        form_layout = QFormLayout()
        form_layout.addRow("Session", self._session_label)
        form_layout.addRow("Output", self._output_path_edit)
        form_layout.addRow("Reviewer", self._reviewer_edit)

        button_row = QHBoxLayout()
        button_row.addWidget(self._preview_button)
        button_row.addWidget(self._execute_button)

        review_button_row = QHBoxLayout()
        review_button_row.addWidget(self._approve_button)
        review_button_row.addWidget(self._reject_button)

        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addWidget(QLabel("Sources", self))
        layout.addWidget(self._source_list, stretch=1)
        layout.addLayout(button_row)
        layout.addWidget(self._validation_summary_label)
        layout.addWidget(self._review_outcome_label)
        layout.addWidget(self._review_status_label)
        layout.addWidget(QLabel("Validation issues", self))
        layout.addWidget(self._issue_list, stretch=1)
        layout.addWidget(self._override_checkbox)
        layout.addWidget(QLabel("Review rationale", self))
        layout.addWidget(self._rationale_edit)
        layout.addLayout(review_button_row)
        layout.addWidget(self._result_label)
        layout.addWidget(self._status_label)

        self._bridge = StateBridge(self)
        self._bridge.state_changed.connect(self._apply_state)
        self._screen_model.subscribe(self._bridge.publish)

    def load_session(self, session: ConversionSession) -> None:
        self._screen_model.load_session(session)

    def _apply_state(self, state: ConversionSessionScreenState) -> None:
        if state.session is None:
            self._session_label.setText("No session loaded.")
        else:
            self._session_label.setText(f"{state.session.session_id} ({state.session.status.value})")

        self._sync_sources(state)
        self._sync_validation_issues(state)

        if state.user_error is not None:
            self._status_label.setText(state.user_error.message)
        elif state.progress_event is not None:
            self._status_label.setText(state.progress_event.message)
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
        else:
            self._result_label.setText("No preview or execution yet.")

        self._validation_summary_label.setText(self._validation_summary_text(state))
        self._review_outcome_label.setText(self._review_outcome_text(state))
        self._review_status_label.setText(self._review_status_text(state))

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
        self._refresh_execute_enabled()
        self._approve_button.setEnabled(state.can_submit_review)
        self._reject_button.setEnabled(state.can_submit_review)
        self._override_checkbox.setEnabled(state.execution is not None)
        self._issue_list.setEnabled(state.execution is not None)
        self._rationale_edit.setEnabled(state.execution is not None)
        self._reviewer_edit.setEnabled(state.execution is not None)

    def _sync_sources(self, state: ConversionSessionScreenState) -> None:
        self._source_list.clear()
        for source in state.sources:
            item = QListWidgetItem(f"{source.label} [{source.source_type}]")
            item.setToolTip(str(source.location))
            self._source_list.addItem(item)

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

    @staticmethod
    def _validation_summary_text(state: ConversionSessionScreenState) -> str:
        if state.execution is None:
            return "Validation summary: not available."
        summary = state.execution.validation_summary
        return (
            "Validation summary: "
            f"{len(summary.errors())} errors, {len(summary.warnings())} warnings"
        )

    @staticmethod
    def _review_outcome_text(state: ConversionSessionScreenState) -> str:
        if state.execution is None:
            return "Review outcome: not available."
        outcome = state.execution.review_outcome
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

    def _refresh_execute_enabled(self) -> None:
        state = self._screen_model.state
        self._execute_button.setEnabled(state.can_run_execution and bool(self._output_path_edit.text().strip()))

    def _on_execute_clicked(self) -> None:
        output_text = self._output_path_edit.text().strip()
        if not output_text:
            self._status_label.setText("Output path is required before writing NWB.")
            return
        self._screen_model.start_execution(Path(output_text))

    def _on_rationale_changed(self) -> None:
        self._screen_model.set_review_rationale(self._rationale_edit.toPlainText())

    def _on_issue_item_changed(self, *_args) -> None:
        for index in range(self._issue_list.count()):
            item = self._issue_list.item(index)
            self._screen_model.set_issue_acknowledged(
                item.data(Qt.ItemDataRole.UserRole),
                item.checkState() == Qt.CheckState.Checked,
            )
