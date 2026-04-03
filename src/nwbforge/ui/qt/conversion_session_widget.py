"""Qt widget for one conversion-session workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from nwbforge.domain.enums import ReviewStatus
from nwbforge.domain.models import ConversionSession
from nwbforge.ui.conversion_session import ConversionSessionScreenModel
from nwbforge.ui.models import ConversionSessionScreenState
from nwbforge.ui.qt.bridge import StateBridge
from nwbforge.ui.qt.styling import build_metric_card


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
        self._output_path_edit.textChanged.connect(self._on_output_path_changed)
        self._choose_output_button = QPushButton("Choose Output...", self)
        self._choose_output_button.clicked.connect(self._choose_output_path)
        self._validation_summary_label = QLabel("Validation summary: not available.", self)
        self._review_outcome_label = QLabel("Review outcome: not available.", self)
        self._review_status_label = QLabel("Review status: not reviewed.", self)
        self._workflow_steps_label = QLabel(
            "Workflow: 1. Ingest in New Session  2. Review Metadata  3. Build Preview / Choose Output  4. Write NWB / Review Results",
            self,
        )
        self._workflow_steps_label.setWordWrap(True)
        self._session_context_label = QLabel(
            "Session focus: no session loaded. Open Session Details only when you need source inspection.",
            self,
        )
        self._session_context_label.setWordWrap(True)
        self._session_details_toggle = QCheckBox("Show Session Details", self)
        self._session_details_toggle.toggled.connect(self._set_session_summary_visible)
        self._advanced_toggle = QCheckBox("Show Advanced Tools", self)
        self._advanced_toggle.toggled.connect(self._set_advanced_ui_visible)
        self._readiness_summary_label = QLabel("Readiness: blocked until a session is loaded.", self)
        self._readiness_summary_label.setWordWrap(True)
        self._next_action_label = QLabel("Next action: start with New Session and add data sources.", self)
        self._next_action_label.setWordWrap(True)
        self._ready_to_write_label = QLabel(
            "Ready to write when: a session is loaded, preview is built, an output path is chosen, and remaining review blockers are understood.",
            self,
        )
        self._ready_to_write_label.setWordWrap(True)
        self._pre_write_checklist_label = QLabel(
            "Pre-write checklist:\n- Session loaded: pending\n- Preview built: pending\n- Metadata review: waiting for preview\n- Output path chosen: pending",
            self,
        )
        self._pre_write_checklist_label.setWordWrap(True)
        self._stage_value_label = QLabel("idle", self)
        self._output_value_label = QLabel("No output selected.", self)
        self._issue_count_value_label = QLabel("0 issues", self)
        self._artifact_count_value_label = QLabel("0 artifacts", self)
        self._disagreement_count_value_label = QLabel("0 metadata conflicts", self)
        self._issue_list = QListWidget(self)
        self._issue_list.itemChanged.connect(self._on_issue_item_changed)
        self._review_guidance_label = QLabel("Run preview or execution to unlock review guidance.", self)
        self._role_policy_label = QLabel(
            "Data source priority during conflict review: primary sources take precedence over metadata sources, which take precedence over supplemental sources.",
            self,
        )
        self._role_policy_label.setWordWrap(True)
        self._acknowledgement_summary_label = QLabel("Acknowledged 0 of 0 issues.", self)
        self._review_checklist_label = QLabel(
            "Review checklist:\n- Conversion results available: pending\n- Validation issues acknowledged: waiting for results\n- Reviewer recorded: pending\n- Decision recorded: pending",
            self,
        )
        self._review_checklist_label.setWordWrap(True)
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
        self._snapshot_history_list = QListWidget(self)
        self._snapshot_history_list.currentItemChanged.connect(self._sync_selected_snapshot_summary)
        self._snapshot_history_list.itemSelectionChanged.connect(self._refresh_snapshot_actions)
        self._progress_history_list = QListWidget(self)
        self._disagreement_list = QListWidget(self)
        self._disagreement_list.currentItemChanged.connect(self._sync_selected_disagreement)
        self._disagreement_filter_combo = QComboBox(self)
        self._disagreement_filter_combo.addItems(["Pending only", "Resolved only", "All conflicts"])
        self._disagreement_filter_combo.currentTextChanged.connect(self._sync_metadata_disagreements)
        self._selected_disagreement_value_label = QLabel("No metadata disagreement selected.", self)
        self._selected_disagreement_value_label.setWordWrap(True)
        self._selected_disagreement_source_list = QListWidget(self)
        self._selected_disagreement_source_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._selected_disagreement_source_list.currentItemChanged.connect(self._sync_selected_disagreement_source)
        self._selected_disagreement_notes_label = QLabel("No comparison notes.", self)
        self._selected_disagreement_notes_label.setWordWrap(True)
        self._recommended_resolution_label = QLabel(
            "Recommended action: select a metadata review item to see the default resolution path.",
            self,
        )
        self._recommended_resolution_label.setWordWrap(True)
        self._selected_session_override_status_label = QLabel(
            "Preferred session value: no session-wide override applied.",
            self,
        )
        self._selected_session_override_status_label.setWordWrap(True)
        self._selected_source_override_status_label = QLabel(
            "Source-specific overrides: none applied.",
            self,
        )
        self._selected_source_override_status_label.setWordWrap(True)
        self._selected_resolution_status_label = QLabel("Resolution status: not available.", self)
        self._selected_resolution_status_label.setWordWrap(True)
        self._metadata_resolution_summary_label = QLabel("No metadata conflicts loaded.", self)
        self._metadata_resolution_summary_label.setWordWrap(True)
        self._custom_session_override_toggle = QCheckBox("Use a custom preferred session value", self)
        self._custom_session_override_toggle.toggled.connect(self._set_custom_session_override_visible)
        self._manual_session_override_label = QLabel("Custom preferred session value", self)
        self._manual_session_override_edit = QLineEdit(self)
        self._manual_session_override_edit.setPlaceholderText("Manual session override value for selected field")
        self._manual_session_override_edit.textChanged.connect(self._refresh_metadata_resolution_actions)
        self._selected_source_override_edit = QLineEdit(self)
        self._selected_source_override_edit.setPlaceholderText("Override value for selected source")
        self._selected_source_override_edit.textChanged.connect(self._refresh_metadata_resolution_actions)
        self._use_source_value_button = QPushButton("Use Selected Source Value As Session Override", self)
        self._use_source_value_button.clicked.connect(self._apply_selected_source_as_session_override)
        self._apply_manual_session_override_button = QPushButton("Apply Manual Session Override", self)
        self._apply_manual_session_override_button.clicked.connect(self._apply_manual_session_override)
        self._clear_override_button = QPushButton("Clear Session Override", self)
        self._clear_override_button.clicked.connect(self._clear_selected_override)
        self._apply_source_override_button = QPushButton("Apply Source Override", self)
        self._apply_source_override_button.clicked.connect(self._apply_selected_source_override)
        self._use_source_value_as_source_override_button = QPushButton("Use Selected Source Value As Source Override", self)
        self._use_source_value_as_source_override_button.clicked.connect(self._apply_selected_source_as_source_override)
        self._clear_source_override_button = QPushButton("Clear Source Override", self)
        self._clear_source_override_button.clicked.connect(self._clear_selected_source_override)
        self._clear_all_field_overrides_button = QPushButton("Clear All Field Overrides", self)
        self._clear_all_field_overrides_button.clicked.connect(self._clear_all_field_overrides)
        self._open_artifact_button = QPushButton("Open Selected Artifact", self)
        self._open_artifact_button.clicked.connect(self._open_selected_artifact)
        self._reveal_artifact_button = QPushButton("Open Artifact Folder", self)
        self._reveal_artifact_button.clicked.connect(self._reveal_selected_artifact)
        self._open_validation_report_button = QPushButton("Open Validation Report", self)
        self._open_validation_report_button.clicked.connect(lambda: self._open_artifact_by_type("validation_report"))
        self._open_review_artifact_button = QPushButton("Open Review Decision", self)
        self._open_review_artifact_button.clicked.connect(lambda: self._open_artifact_by_type("review_decision"))
        self._restore_snapshot_button = QPushButton("Restore Selected Snapshot", self)
        self._restore_snapshot_button.clicked.connect(self._restore_selected_snapshot)
        self._selected_snapshot_summary_label = QLabel(
            "Select a saved snapshot to review its restore impact.",
            self,
        )
        self._selected_snapshot_summary_label.setWordWrap(True)

        self._session_summary_group = QGroupBox("Session Overview", self)
        self._execution_group = QGroupBox("Execution Status", self)
        self._review_group = QGroupBox("Quality Check and Review", self)
        self._artifact_group = QGroupBox("Generated Artifacts", self)
        self._history_group = QGroupBox("Saved Session History", self)
        self._diagnostics_group = QGroupBox("Runtime Diagnostics", self)
        self._workspace_tabs = QTabWidget(self)
        self._workspace_tabs.setDocumentMode(True)
        self._workspace_tabs.setUsesScrollButtons(True)
        self._session_tabs = QTabBar(self)
        self._session_tabs.setDocumentMode(True)
        self._session_tabs.setTabsClosable(True)
        self._session_tabs.setMovable(True)
        self._session_tabs.setUsesScrollButtons(True)
        self._session_tabs.hide()

        self._source_list.setAlternatingRowColors(True)
        self._issue_list.setAlternatingRowColors(True)
        self._artifact_list.setAlternatingRowColors(True)
        self._snapshot_history_list.setAlternatingRowColors(True)
        self._progress_history_list.setAlternatingRowColors(True)
        self._disagreement_list.setAlternatingRowColors(True)
        self._selected_disagreement_source_list.setAlternatingRowColors(True)
        self._source_list.setMinimumWidth(300)
        self._artifact_list.setMinimumHeight(180)
        self._issue_list.setMinimumHeight(170)

        self._choose_output_button.setProperty("secondary", True)
        self._open_artifact_button.setProperty("secondary", True)
        self._reveal_artifact_button.setProperty("secondary", True)
        self._open_validation_report_button.setProperty("secondary", True)
        self._open_review_artifact_button.setProperty("secondary", True)
        self._restore_snapshot_button.setProperty("secondary", True)
        self._clear_override_button.setProperty("secondary", True)
        self._clear_source_override_button.setProperty("secondary", True)
        self._clear_all_field_overrides_button.setProperty("danger", True)
        self._reject_button.setProperty("danger", True)

        self._pathway_metric_card, self._pathway_metric_value = build_metric_card("Workflow", "Not loaded", accent=True, parent=self)
        self._stage_metric_card, self._stage_metric_value = build_metric_card("Stage", "idle", parent=self)
        self._validation_metric_card, self._validation_metric_value = build_metric_card("Validation", "Not available", parent=self)
        self._artifact_metric_card, self._artifact_metric_value = build_metric_card("Artifacts", "0 artifacts", parent=self)
        self._readiness_metric_card, self._readiness_metric_value = build_metric_card("Readiness", "Blocked", parent=self)

        form_layout = QFormLayout()
        form_layout.addRow("Session", self._session_label)
        form_layout.addRow("Workflow", self._pathway_label)
        form_layout.addRow("Data sources", self._source_count_label)

        source_detail_layout = QFormLayout()
        source_detail_layout.addRow("Location", self._source_location_label)
        source_detail_layout.addRow("Data source role", self._source_role_label)
        source_detail_layout.addRow("Adapter", self._source_adapter_label)
        source_detail_layout.addRow("Media", self._source_media_type_label)
        self._source_detail_group = QGroupBox("Selected Data Source", self)
        self._source_detail_group.setLayout(source_detail_layout)

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
        session_summary_layout.addWidget(QLabel("Data sources", self))
        session_summary_layout.addWidget(self._source_list, stretch=1)
        session_summary_layout.addWidget(self._source_detail_group)
        self._session_summary_group.setLayout(session_summary_layout)

        run_overview_layout = QFormLayout()
        run_overview_layout.addRow("Stage", self._stage_value_label)
        run_overview_layout.addRow("Output target", self._output_value_label)
        run_overview_layout.addRow("Validation", self._issue_count_value_label)
        run_overview_layout.addRow("Metadata review", self._disagreement_count_value_label)
        run_overview_layout.addRow("Artifacts", self._artifact_count_value_label)

        output_form_layout = QFormLayout()
        output_form_layout.addRow("Output file", self._output_path_edit)
        output_button_row = QHBoxLayout()
        output_button_row.addWidget(self._choose_output_button)
        output_button_row.addWidget(self._preview_button)
        output_button_row.addWidget(self._execute_button)

        execution_layout = QVBoxLayout()
        execution_layout.addLayout(run_overview_layout)
        execution_layout.addWidget(self._workflow_steps_label)
        execution_layout.addWidget(self._session_context_label)
        execution_layout.addWidget(self._session_details_toggle)
        execution_layout.addWidget(self._advanced_toggle)
        execution_layout.addWidget(self._readiness_summary_label)
        execution_layout.addWidget(self._next_action_label)
        execution_layout.addWidget(self._ready_to_write_label)
        execution_layout.addWidget(self._pre_write_checklist_label)
        execution_layout.addLayout(output_form_layout)
        execution_layout.addLayout(output_button_row)
        execution_layout.addWidget(self._status_label)
        execution_layout.addWidget(self._result_label)
        execution_layout.addStretch(1)
        self._execution_group.setLayout(execution_layout)

        review_layout = QVBoxLayout()
        review_layout.addWidget(self._review_guidance_label)
        review_layout.addWidget(self._role_policy_label)
        review_layout.addWidget(self._acknowledgement_summary_label)
        review_layout.addWidget(self._review_checklist_label)
        review_layout.addWidget(self._validation_summary_label)
        review_layout.addWidget(self._review_outcome_label)
        review_layout.addWidget(self._review_status_label)
        reviewer_form_layout = QFormLayout()
        reviewer_form_layout.addRow("Reviewer", self._reviewer_edit)
        review_layout.addLayout(reviewer_form_layout)
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

        history_layout = QVBoxLayout()
        history_layout.addWidget(self._snapshot_history_list, stretch=1)
        history_layout.addWidget(self._selected_snapshot_summary_label)
        history_layout.addWidget(self._restore_snapshot_button)
        self._history_group.setLayout(history_layout)

        self._diagnostics_summary_label = QLabel("No runtime events captured yet.", self)
        self._diagnostics_summary_label.setWordWrap(True)
        diagnostics_layout = QVBoxLayout()
        diagnostics_layout.addWidget(self._diagnostics_summary_label)
        diagnostics_layout.addWidget(self._progress_history_list, stretch=1)
        self._diagnostics_group.setLayout(diagnostics_layout)

        metadata_review_page = QWidget(self)
        metadata_review_layout = QVBoxLayout(metadata_review_page)
        metadata_review_layout.addWidget(QLabel("Pending mixed-source metadata review", self))
        metadata_review_layout.addWidget(self._metadata_resolution_summary_label)
        metadata_review_layout.addWidget(self._disagreement_filter_combo)
        metadata_review_layout.addWidget(self._disagreement_list, stretch=1)
        metadata_detail_group = QGroupBox("Selected Metadata Review Item", self)
        metadata_detail_layout = QVBoxLayout(metadata_detail_group)
        metadata_detail_layout.addWidget(self._selected_disagreement_value_label)
        metadata_detail_layout.addWidget(self._recommended_resolution_label)
        metadata_detail_layout.addWidget(self._selected_resolution_status_label)
        metadata_detail_layout.addWidget(self._selected_session_override_status_label)
        metadata_detail_layout.addWidget(self._selected_source_override_status_label)
        metadata_detail_layout.addWidget(QLabel("Source comparison", self))
        metadata_detail_layout.addWidget(self._selected_disagreement_source_list, stretch=1)
        metadata_detail_layout.addWidget(QLabel("Resolution notes", self))
        metadata_detail_layout.addWidget(self._selected_disagreement_notes_label)
        metadata_resolution_row = QHBoxLayout()
        metadata_resolution_row.addWidget(self._use_source_value_button)
        metadata_resolution_row.addWidget(self._clear_override_button)
        metadata_detail_layout.addLayout(metadata_resolution_row)
        metadata_detail_layout.addWidget(self._custom_session_override_toggle)
        metadata_detail_layout.addWidget(self._manual_session_override_label)
        metadata_detail_layout.addWidget(self._manual_session_override_edit)
        metadata_detail_layout.addWidget(self._apply_manual_session_override_button)
        self._advanced_resolution_group = QGroupBox("Advanced Resolution Tools", self)
        advanced_resolution_layout = QVBoxLayout(self._advanced_resolution_group)
        advanced_resolution_layout.addWidget(QLabel("Preferred value for selected source", self))
        advanced_resolution_layout.addWidget(self._selected_source_override_edit)
        metadata_source_resolution_row = QHBoxLayout()
        metadata_source_resolution_row.addWidget(self._use_source_value_as_source_override_button)
        metadata_source_resolution_row.addWidget(self._apply_source_override_button)
        metadata_source_resolution_row.addWidget(self._clear_source_override_button)
        metadata_source_resolution_row.addWidget(self._clear_all_field_overrides_button)
        advanced_resolution_layout.addLayout(metadata_source_resolution_row)
        metadata_detail_layout.addWidget(self._advanced_resolution_group)
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

        history_page = QWidget(self)
        history_page_layout = QVBoxLayout(history_page)
        history_page_layout.addWidget(self._history_group)

        diagnostics_page = QWidget(self)
        diagnostics_page_layout = QVBoxLayout(diagnostics_page)
        diagnostics_page_layout.addWidget(self._diagnostics_group)

        self._workspace_tabs.addTab(run_overview_page, "1. Run Overview")
        self._workspace_tabs.addTab(metadata_review_page, "2. Metadata Review")
        self._workspace_tabs.addTab(review_page, "3. Quality Review")
        self._workspace_tabs.addTab(artifact_page, "4. Artifacts")
        self._workspace_tabs.addTab(history_page, "History")
        self._workspace_tabs.addTab(diagnostics_page, "Diagnostics")
        self._set_advanced_ui_visible(False)
        self._set_custom_session_override_visible(False)

        right_column = QWidget(self)
        right_column_layout = QVBoxLayout(right_column)
        right_column_layout.addWidget(self._workspace_tabs)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(self._session_summary_group)
        splitter.addWidget(right_column)
        splitter.setChildrenCollapsible(True)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        self._splitter = splitter
        self._set_session_summary_visible(False)

        metric_row = QHBoxLayout()
        metric_row.setSpacing(10)
        metric_row.addWidget(self._pathway_metric_card, 1)
        metric_row.addWidget(self._stage_metric_card, 1)
        metric_row.addWidget(self._validation_metric_card, 1)
        metric_row.addWidget(self._artifact_metric_card, 1)
        metric_row.addWidget(self._readiness_metric_card, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        content = QWidget(self)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)
        content_layout.addWidget(self._session_tabs)
        content_layout.addLayout(metric_row)
        content_layout.addWidget(splitter)

        self._scroll_area = QScrollArea(self)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setWidget(content)
        layout.addWidget(self._scroll_area)

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
        self._sync_snapshot_history(state)
        self._sync_progress_history(state)

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
        self._pathway_metric_value.setText(self._pathway_label.text())
        self._stage_metric_value.setText(self._stage_value_label.text().replace("_", " "))
        self._validation_metric_value.setText(self._issue_count_value_label.text())
        self._artifact_metric_value.setText(self._artifact_count_value_label.text())
        self._readiness_metric_value.setText(self._readiness_state_text(state))
        self._review_guidance_label.setText(self._review_guidance_text(state))
        self._readiness_summary_label.setText(self._readiness_summary_text(state))
        self._next_action_label.setText(self._next_action_text(state))
        self._ready_to_write_label.setText(self._ready_to_write_text(state))
        self._pre_write_checklist_label.setText(self._pre_write_checklist_text(state))
        self._review_checklist_label.setText(self._review_checklist_text(state))
        self._session_context_label.setText(self._session_context_text(state))
        self._acknowledgement_summary_label.setText(self._acknowledgement_summary_text(state))
        self._metadata_resolution_summary_label.setText(self._metadata_resolution_summary_text(state))
        self._diagnostics_summary_label.setText(self._diagnostics_summary_text(state))

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
        self._refresh_snapshot_actions()

    def _sync_sources(self, state: ConversionSessionScreenState) -> None:
        selected_item = self._source_list.currentItem()
        selected_source_id = selected_item.data(Qt.ItemDataRole.UserRole) if selected_item is not None else None
        self._source_list.clear()
        for source in state.sources:
            item = QListWidgetItem(f"{source.label} [{source.source_type}]")
            item.setToolTip(str(source.location))
            item.setData(Qt.ItemDataRole.UserRole, source.source_id)
            self._source_list.addItem(item)
        if self._source_list.count() > 0:
            restored_row = 0
            if selected_source_id is not None:
                for row in range(self._source_list.count()):
                    if self._source_list.item(row).data(Qt.ItemDataRole.UserRole) == selected_source_id:
                        restored_row = row
                        break
            self._source_list.setCurrentRow(restored_row)
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

    def _sync_snapshot_history(self, state: ConversionSessionScreenState) -> None:
        selected_item = self._snapshot_history_list.currentItem()
        selected_snapshot_id = selected_item.data(Qt.ItemDataRole.UserRole) if selected_item is not None else None
        self._snapshot_history_list.clear()
        for snapshot in state.snapshot_history:
            snapshot_kind = "preview state" if snapshot.artifact_count == 0 else "results state"
            review_state = "reviewed" if snapshot.has_review_record else "pending review record"
            label = (
                f"{snapshot.saved_at_text} | {snapshot.status}"
                f" | {snapshot_kind}"
                f" | {snapshot.artifact_count} artifacts"
                f" | {snapshot.issue_count} issues"
            )
            label += f" | {review_state}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, snapshot.snapshot_id)
            item.setToolTip(snapshot.snapshot_id)
            self._snapshot_history_list.addItem(item)
        if self._snapshot_history_list.count() == 0:
            self._selected_snapshot_summary_label.setText(
                "Select a saved snapshot to review its restore impact."
            )
            self._refresh_snapshot_actions()
            return
        restored_row = 0
        if selected_snapshot_id is not None:
            for row in range(self._snapshot_history_list.count()):
                if self._snapshot_history_list.item(row).data(Qt.ItemDataRole.UserRole) == selected_snapshot_id:
                    restored_row = row
                    break
        self._snapshot_history_list.setCurrentRow(restored_row)
        self._refresh_snapshot_actions()

    def _sync_selected_snapshot_summary(self, *_args) -> None:
        snapshot = self._selected_snapshot_history_item()
        if snapshot is None:
            self._selected_snapshot_summary_label.setText(
                "Select a saved snapshot to review its restore impact."
            )
            return
        review_text = "reviewed" if snapshot.has_review_record else "not reviewed"
        self._selected_snapshot_summary_label.setText(
            "Selected snapshot: "
            f"{snapshot.saved_at_text} | {snapshot.status} | "
            f"{snapshot.artifact_count} artifacts | {snapshot.issue_count} issues | {review_text}. "
            "Restoring replaces the current session view with this saved state."
        )

    def _sync_progress_history(self, state: ConversionSessionScreenState) -> None:
        self._progress_history_list.clear()
        for event in state.progress_history:
            source_suffix = f" | {event.source_id}" if event.source_id is not None else ""
            stage_prefix = self._progress_stage_prefix(event.stage)
            item = QListWidgetItem(
                f"[{stage_prefix}] {event.created_at_text} | {event.stage} | {event.percent_complete}% | "
                f"{event.message}{source_suffix}"
            )
            item.setToolTip(event.message)
            self._progress_history_list.addItem(item)

    def _sync_metadata_disagreements(self, state: ConversionSessionScreenState | None = None, *_args) -> None:
        if state is None or not isinstance(state, ConversionSessionScreenState):
            state = self._screen_model.state
        selected_item = self._disagreement_list.currentItem()
        selected_key = selected_item.data(Qt.ItemDataRole.UserRole) if selected_item is not None else None
        self._disagreement_list.clear()
        disagreements = tuple(
            sorted(
                self._filtered_metadata_disagreements(state),
                key=lambda item: (not item.pending_resolution, item.canonical_key),
            )
        )
        for disagreement in disagreements:
            status_label = "Pending Review" if disagreement.pending_resolution else "Resolved"
            resolution_suffix = ""
            if disagreement.resolution_status == "session_override":
                resolution_suffix = " | session override"
            elif disagreement.resolution_status == "source_override":
                resolution_suffix = " | source override"
            item = QListWidgetItem(
                f"[{status_label}] {disagreement.canonical_key} -> {disagreement.resolved_value}{resolution_suffix}"
            )
            item.setData(Qt.ItemDataRole.UserRole, disagreement.canonical_key)
            tooltip_lines = [
                f"Resolution state: {disagreement.resolution_status.replace('_', ' ')}",
                f"Resolved from {disagreement.resolved_origin} value using source(s): "
                f"{', '.join(disagreement.source_ids) or 'session merge'}",
            ]
            if disagreement.resolution_history:
                tooltip_lines.append(disagreement.resolution_history[-1])
            item.setToolTip("\n".join(tooltip_lines))
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
            self._recommended_resolution_label.setText(
                "Recommended action: select a metadata review item to see the default resolution path."
            )
            self._selected_session_override_status_label.setText(
                "Preferred session value: no session-wide override applied."
            )
            self._selected_source_override_status_label.setText("Source-specific overrides: none applied.")
            self._selected_resolution_status_label.setText("Resolution status: not available.")
            with QSignalBlocker(self._custom_session_override_toggle):
                self._custom_session_override_toggle.setChecked(False)
            with QSignalBlocker(self._manual_session_override_edit):
                self._manual_session_override_edit.setText("")
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
            self._recommended_resolution_label.setText(
                "Recommended action: select a metadata review item to see the default resolution path."
            )
            self._selected_session_override_status_label.setText(
                "Preferred session value: no session-wide override applied."
            )
            self._selected_source_override_status_label.setText("Source-specific overrides: none applied.")
            self._selected_resolution_status_label.setText("Resolution status: not available.")
            with QSignalBlocker(self._custom_session_override_toggle):
                self._custom_session_override_toggle.setChecked(False)
            with QSignalBlocker(self._manual_session_override_edit):
                self._manual_session_override_edit.setText("")
            with QSignalBlocker(self._selected_source_override_edit):
                self._selected_source_override_edit.setText("")
            self._refresh_metadata_resolution_actions()
            return
        self._selected_disagreement_value_label.setText(
            f"{disagreement.canonical_key}\nResolved value: {disagreement.resolved_value}\n"
            f"Origin: {disagreement.resolved_origin}"
        )
        self._selected_resolution_status_label.setText(
            "Resolution status: " + disagreement.resolution_status.replace("_", " ")
        )
        selected_source_item = self._selected_disagreement_source_list.currentItem()
        selected_source_id = (
            selected_source_item.data(Qt.ItemDataRole.UserRole) if selected_source_item is not None else None
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
            restored_row = 0
            if selected_source_id is not None:
                for row in range(self._selected_disagreement_source_list.count()):
                    if self._selected_disagreement_source_list.item(row).data(Qt.ItemDataRole.UserRole) == selected_source_id:
                        restored_row = row
                        break
            self._selected_disagreement_source_list.setCurrentRow(restored_row)
        note_lines = list(disagreement.notes)
        note_lines.extend(disagreement.resolution_notes)
        note_lines.extend(disagreement.resolution_history)
        if note_lines:
            self._selected_disagreement_notes_label.setText("\n".join(note_lines))
        else:
            self._selected_disagreement_notes_label.setText("No comparison notes.")
        source_override_lines = [
            f"{source_value.source_label}: {source_value.override_value}"
            for source_value in disagreement.source_values
            if source_value.override_value is not None
        ]
        self._selected_session_override_status_label.setText(
            (
                f"Preferred session value: {disagreement.session_override_value}"
                if disagreement.session_override_value is not None
                else "Preferred session value: no session-wide override applied."
            )
        )
        self._selected_source_override_status_label.setText(
            (
                "Source-specific overrides: " + "; ".join(source_override_lines)
                if source_override_lines
                else "Source-specific overrides: none applied."
            )
        )
        should_show_custom_override = disagreement.session_override_value is not None
        with QSignalBlocker(self._custom_session_override_toggle):
            self._custom_session_override_toggle.setChecked(should_show_custom_override)
        with QSignalBlocker(self._manual_session_override_edit):
            self._manual_session_override_edit.setText(disagreement.session_override_value or "")
        self._set_custom_session_override_visible(should_show_custom_override)
        self._sync_selected_disagreement_source()
        self._refresh_metadata_resolution_actions()

    def _sync_selected_disagreement_source(self, *_args) -> None:
        selected_source = self._selected_disagreement_source()
        with QSignalBlocker(self._selected_source_override_edit):
            self._selected_source_override_edit.setText(
                selected_source.override_value if selected_source is not None and selected_source.override_value is not None else ""
            )
        disagreement = self._selected_disagreement()
        self._recommended_resolution_label.setText(
            self._recommended_resolution_text(disagreement, selected_source)
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

    def _output_text(self, state: ConversionSessionScreenState) -> str:
        if state.output_path is not None:
            return str(state.output_path)
        if self._output_path_edit.text().strip():
            return self._output_path_edit.text().strip()
        return "No output selected."

    def _has_output_target(self, state: ConversionSessionScreenState) -> bool:
        return state.output_path is not None or bool(self._output_path_edit.text().strip())

    def _write_blockers(self, state: ConversionSessionScreenState) -> list[str]:
        blockers: list[str] = []
        if state.session is None:
            blockers.append("load or create a session")
        if state.preview is None:
            blockers.append("build preview")
        if any(item.pending_resolution for item in state.metadata_disagreements):
            blockers.append("review metadata conflicts")
        if not self._has_output_target(state):
            blockers.append("choose output path")
        return blockers

    def _pre_write_checklist_text(self, state: ConversionSessionScreenState) -> str:
        session_status = "done" if state.session is not None else "pending"
        if state.is_preview_running:
            preview_status = "in progress"
        elif state.preview is not None or state.execution is not None:
            preview_status = "done"
        else:
            preview_status = "pending"
        if state.preview is None and state.execution is None and not state.is_preview_running:
            metadata_status = "waiting for preview"
        elif any(item.pending_resolution for item in state.metadata_disagreements):
            metadata_status = "pending"
        else:
            metadata_status = "done"
        output_status = "done" if self._has_output_target(state) else "pending"
        return (
            "Pre-write checklist:\n"
            f"- Session loaded: {session_status}\n"
            f"- Preview built: {preview_status}\n"
            f"- Metadata review: {metadata_status}\n"
            f"- Output path chosen: {output_status}"
        )

    def _next_action_text(self, state: ConversionSessionScreenState) -> str:
        if state.session is None:
            return "Next action: start with New Session and add supported or custom data sources."
        if state.is_preview_running:
            return "Current step: Build Preview. Wait for preview results so the app can surface metadata conflicts and readiness."
        if state.preview is None:
            return "Current step: Build Preview. Next action: review the session summary, then select Build Preview."
        pending_conflicts = [item for item in state.metadata_disagreements if item.pending_resolution]
        if pending_conflicts:
            return "Current step: Review Metadata. Next action: inspect pending mixed-source conflicts before writing NWB."
        if not self._has_output_target(state):
            return "Current step: Choose Output. Next action: choose an NWB output path before writing."
        if state.is_execution_running:
            return "Current step: Write NWB. Wait for conversion to finish, then review validation results and artifacts."
        if state.execution is None:
            return "Current step: Write NWB. Next action: run Write NWB when you are satisfied with the current preview."
        return "Current step: Review Results. Next action: inspect validation issues and artifacts, then complete review if required."

    def _ready_to_write_text(self, state: ConversionSessionScreenState) -> str:
        blockers = self._write_blockers(state)
        if blockers:
            return "Ready to write when: " + ", ".join(blockers) + "."
        return "Ready to write when: the current preview looks correct and you want to generate NWB plus validation artifacts."

    def _readiness_state_text(self, state: ConversionSessionScreenState) -> str:
        if state.session is None:
            return "Blocked"
        if state.is_preview_running:
            return "Building Preview"
        if state.is_execution_running:
            return "Writing NWB"
        if state.execution is not None:
            outcome = state.execution.review_outcome
            if outcome.blocks_completion:
                return "Blocked by Review"
            if outcome.requires_manual_review or state.validation_issues:
                return "Needs Review"
            return "Completed"
        blockers = self._write_blockers(state)
        if not blockers:
            return "Ready to Write"
        if state.preview is not None and any(item.pending_resolution for item in state.metadata_disagreements):
            return "Needs Review"
        return "Blocked"

    def _readiness_summary_text(self, state: ConversionSessionScreenState) -> str:
        if state.session is None:
            return "Readiness: blocked until a session is loaded."
        if state.is_preview_running:
            return "Readiness: building preview so the app can check grouping, metadata, and conversion readiness."
        if state.is_execution_running:
            return "Readiness: writing NWB now. Review results after conversion finishes."
        if state.execution is not None:
            outcome = state.execution.review_outcome
            if outcome.blocks_completion:
                return "Readiness: blocked by review findings. Add rationale and override only if the result is acceptable."
            if outcome.requires_manual_review or state.validation_issues:
                return (
                    "Readiness: needs review. Inspect validation findings and artifacts before treating the result as complete."
                )
            return "Readiness: complete. Output and generated artifacts are ready for inspection or archival."
        blockers = self._write_blockers(state)
        if blockers:
            return "Readiness: blocked by " + ", ".join(blockers) + "."
        return "Readiness: ready to write. Preview is built, main conflicts are cleared, and output is selected."

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

    @staticmethod
    def _review_checklist_text(state: ConversionSessionScreenState) -> str:
        if state.execution is None:
            return (
                "Review checklist:\n"
                "- Conversion results available: pending\n"
                "- Validation issues acknowledged: waiting for results\n"
                "- Reviewer recorded: pending\n"
                "- Decision recorded: pending"
            )
        acknowledgement_status = (
            "done"
            if not state.validation_issues or len(state.acknowledged_issue_refs) == len(state.validation_issues)
            else "pending"
        )
        reviewer_status = "done" if state.reviewer_name.strip() else "pending"
        outcome = state.execution.review_outcome
        if not outcome.requires_manual_review and not outcome.blocks_completion and not state.validation_issues:
            decision_status = "not required"
        else:
            decision_status = "done" if state.last_review_submission is not None else "pending"
        return (
            "Review checklist:\n"
            "- Conversion results available: done\n"
            f"- Validation issues acknowledged: {acknowledgement_status}\n"
            f"- Reviewer recorded: {reviewer_status}\n"
            f"- Decision recorded: {decision_status}"
        )

    @staticmethod
    def _session_context_text(state: ConversionSessionScreenState) -> str:
        if state.session is None:
            return "Session focus: no session loaded. Open Session Details only when you need source inspection."
        source_count = len(state.sources)
        source_suffix = "data source" if source_count == 1 else "data sources"
        return (
            f"Session focus: {state.session.session_id} | {state.session.pathway.value} workflow | "
            f"{source_count} {source_suffix}. Open Session Details for per-source inspection and output setup."
        )

    def _refresh_execute_enabled(self) -> None:
        state = self._screen_model.state
        self._execute_button.setEnabled(state.can_run_execution and bool(self._output_path_edit.text().strip()))

    def _on_output_path_changed(self, *_args) -> None:
        self._refresh_execute_enabled()
        self._refresh_local_stage_guidance()

    def _refresh_local_stage_guidance(self) -> None:
        state = self._screen_model.state
        self._output_value_label.setText(self._output_text(state))
        self._readiness_metric_value.setText(self._readiness_state_text(state))
        self._readiness_summary_label.setText(self._readiness_summary_text(state))
        self._next_action_label.setText(self._next_action_text(state))
        self._ready_to_write_label.setText(self._ready_to_write_text(state))
        self._pre_write_checklist_label.setText(self._pre_write_checklist_text(state))
        self._review_checklist_label.setText(self._review_checklist_text(state))

    def _set_session_summary_visible(self, visible: bool) -> None:
        self._session_summary_group.setVisible(visible)
        if visible:
            self._splitter.setSizes([1, 2])
        else:
            self._splitter.setSizes([0, 1])

    def _set_advanced_ui_visible(self, visible: bool) -> None:
        self._advanced_resolution_group.setVisible(visible)
        self._workspace_tabs.setTabVisible(4, visible)
        self._workspace_tabs.setTabVisible(5, visible)
        if not visible and self._workspace_tabs.currentIndex() in {4, 5}:
            self._workspace_tabs.setCurrentIndex(0)

    def _set_custom_session_override_visible(self, visible: bool) -> None:
        self._manual_session_override_label.setVisible(visible)
        self._manual_session_override_edit.setVisible(visible)
        self._apply_manual_session_override_button.setVisible(visible)

    def _refresh_metadata_resolution_actions(self, *_args) -> None:
        disagreement = self._selected_disagreement()
        selected_source_item = self._selected_disagreement_source_list.currentItem()
        selected_source = self._selected_disagreement_source()
        self._use_source_value_button.setEnabled(disagreement is not None and selected_source_item is not None)
        custom_override_enabled = disagreement is not None and self._custom_session_override_toggle.isChecked()
        self._manual_session_override_edit.setEnabled(custom_override_enabled)
        self._apply_manual_session_override_button.setEnabled(
            custom_override_enabled and bool(self._manual_session_override_edit.text().strip())
        )
        self._clear_override_button.setEnabled(
            disagreement is not None and disagreement.session_override_value is not None
        )
        self._selected_source_override_edit.setEnabled(disagreement is not None and selected_source_item is not None)
        self._use_source_value_as_source_override_button.setEnabled(
            disagreement is not None and selected_source_item is not None
        )
        self._apply_source_override_button.setEnabled(
            disagreement is not None
            and selected_source_item is not None
            and bool(self._selected_source_override_edit.text().strip())
        )
        self._clear_source_override_button.setEnabled(
            selected_source is not None and selected_source.override_value is not None
        )
        self._clear_all_field_overrides_button.setEnabled(disagreement is not None)

    @staticmethod
    def _recommended_resolution_text(disagreement, selected_source) -> str:
        if disagreement is None:
            return "Recommended action: select a metadata review item to see the default resolution path."
        if disagreement.session_override_value is not None:
            return (
                "Recommended action: keep the current preferred session value unless you need a different session-wide "
                f"override. Current preferred session value: {disagreement.session_override_value}."
            )
        selected_source_match = (
            selected_source is not None and selected_source.value == disagreement.resolved_value
        )
        if selected_source_match:
            return (
                "Recommended action: use the selected source value as the preferred session value. "
                f"It matches the current resolved value from {disagreement.resolved_origin}."
            )
        matching_source = next(
            (
                source_value
                for source_value in disagreement.source_values
                if source_value.value == disagreement.resolved_value
            ),
            None,
        )
        if matching_source is not None:
            return (
                "Recommended action: select "
                f"{matching_source.source_label} and use its value as the preferred session value. "
                f"The current resolved value comes from that {matching_source.role} source."
            )
        if disagreement.resolution_status == "source_override":
            return (
                "Recommended action: verify whether the current source-specific override should stay scoped to that "
                "source or be promoted to the preferred session value."
            )
        if disagreement.pending_resolution:
            return (
                "Recommended action: compare the source values and set a preferred session value before writing NWB. "
                "No source currently matches the resolved value exactly."
            )
        return (
            "Recommended action: verify the current resolved value, then continue if the field reflects the intended "
            "session-level metadata."
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

    def _apply_manual_session_override(self) -> None:
        disagreement = self._selected_disagreement()
        value = self._manual_session_override_edit.text().strip()
        if disagreement is None or not value:
            return
        self._screen_model.apply_session_override(disagreement.canonical_key, value)

    def _apply_selected_source_as_source_override(self) -> None:
        disagreement = self._selected_disagreement()
        selected_source = self._selected_disagreement_source()
        if disagreement is None or selected_source is None:
            return
        self._screen_model.apply_source_override(
            selected_source.source_id,
            disagreement.canonical_key,
            selected_source.value,
        )

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

    def _clear_all_field_overrides(self) -> None:
        disagreement = self._selected_disagreement()
        if disagreement is None:
            return
        self._screen_model.clear_all_field_overrides(disagreement.canonical_key)

    @staticmethod
    def _metadata_resolution_summary_text(state: ConversionSessionScreenState) -> str:
        conflict_count = len(state.metadata_disagreements)
        session_override_count = len(
            [item for item in state.metadata_disagreements if item.session_override_value is not None]
        )
        source_override_count = sum(
            1
            for item in state.metadata_disagreements
            for source_value in item.source_values
            if source_value.override_value is not None
        )
        unresolved_count = len(
            [item for item in state.metadata_disagreements if item.pending_resolution]
        )
        if conflict_count == 0:
            return "No metadata conflicts loaded."
        return (
            f"{conflict_count} conflicts | "
            f"{unresolved_count} pending review | "
            f"{conflict_count - unresolved_count} resolved | "
            f"{session_override_count} session overrides | "
            f"{source_override_count} source overrides"
        )

    @staticmethod
    def _diagnostics_summary_text(state: ConversionSessionScreenState) -> str:
        event_count = len(state.progress_history)
        snapshot_count = len(state.snapshot_history)
        if state.error_message:
            return (
                f"{event_count} runtime events | "
                f"{snapshot_count} saved snapshots | "
                f"Latest state: error | {state.error_message}"
            )
        if state.recovery_message:
            return (
                f"{event_count} runtime events | "
                f"{snapshot_count} saved snapshots | "
                f"Latest state: recovery | {state.recovery_message}"
            )
        if state.review_message and state.review_message.startswith("Recovered "):
            return (
                f"{event_count} runtime events | "
                f"{snapshot_count} saved snapshots | "
                f"Latest state: recovered review | {state.review_message}"
            )
        if event_count == 0:
            return "No runtime events captured yet."
        latest_event = state.progress_history[-1]
        return (
            f"{event_count} runtime events | "
            f"{snapshot_count} saved snapshots | "
            f"Latest stage: {latest_event.stage} ({latest_event.percent_complete}%)"
        )

    def _filtered_metadata_disagreements(
        self,
        state: ConversionSessionScreenState,
    ):
        filter_value = self._disagreement_filter_combo.currentText()
        if filter_value == "Pending only":
            return tuple(item for item in state.metadata_disagreements if item.pending_resolution)
        if filter_value == "Resolved only":
            return tuple(item for item in state.metadata_disagreements if not item.pending_resolution)
        return state.metadata_disagreements

    @staticmethod
    def _progress_stage_prefix(stage: str) -> str:
        if stage == "failed":
            return "Error"
        if stage == "completed":
            return "Complete"
        if stage == "ready_to_write":
            return "Ready"
        return "Progress"

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

    def _refresh_snapshot_actions(self) -> None:
        self._restore_snapshot_button.setEnabled(self._selected_snapshot_id() is not None)

    def _selected_snapshot_id(self) -> str | None:
        item = self._snapshot_history_list.currentItem()
        if item is None:
            return None
        snapshot_id = item.data(Qt.ItemDataRole.UserRole)
        return str(snapshot_id) if snapshot_id else None

    def _selected_snapshot_history_item(self):
        snapshot_id = self._selected_snapshot_id()
        if snapshot_id is None:
            return None
        for snapshot in self._screen_model.state.snapshot_history:
            if snapshot.snapshot_id == snapshot_id:
                return snapshot
        return None

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

    def _restore_selected_snapshot(self) -> None:
        snapshot_id = self._selected_snapshot_id()
        if snapshot_id is None:
            return
        self._screen_model.restore_snapshot(snapshot_id)

    def _open_artifact_by_type(self, artifact_type: str) -> None:
        path = self._artifact_path_for_type(artifact_type)
        if path is None:
            return
        if self._artifact_opener is not None:
            self._artifact_opener(path)
            return
