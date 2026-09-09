"""Qt dialog for direct file/folder session assembly."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from nwbforge.domain.models import ConversionSession
from nwbforge.ui.models import SessionAssemblySourceTypeOption, SessionAssemblyState
from nwbforge.ui.qt.bridge import StateBridge
from nwbforge.ui.qt.file_preview_pane import FilePreviewPane
from nwbforge.ui.session_assembly import SessionAssemblyScreenModel
from nwbforge.ui.qt.styling import apply_window_chrome, build_page_header


class SessionAssemblyDialog(QWidget):
    """Embedded panel bound to `SessionAssemblyScreenModel` for direct source ingestion."""

    dismissed = Signal()

    _METADATA_OVERRIDE_FIELDS = (
        ("session.start_time", "Session Start Time"),
        ("session.experimenter", "Experimenter"),
        ("session.session_description", "Session Description"),
        ("subject.subject_id", "Subject ID"),
        ("subject.species", "Species"),
    )

    def __init__(
        self,
        screen_model: SessionAssemblyScreenModel,
        parent=None,
        *,
        session_created: Callable[[ConversionSession], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.resize(1120, 820)
        apply_window_chrome(self)

        self._screen_model = screen_model
        self._session_created = session_created

        self._input_list = QListWidget(self)
        self._group_list = QListWidget(self)
        self._source_list = QListWidget(self)
        self._input_list.setAlternatingRowColors(True)
        self._group_list.setAlternatingRowColors(True)
        self._source_list.setAlternatingRowColors(True)
        self._source_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._source_list.currentItemChanged.connect(self._sync_selected_source)
        self._group_list.currentItemChanged.connect(self._sync_selected_group)
        self._issue_list = QListWidget(self)
        self._issue_list.setAlternatingRowColors(True)
        self._session_id_edit = QLineEdit(self)
        self._session_id_edit.textChanged.connect(self._screen_model.set_session_id)
        self._title_edit = QLineEdit(self)
        self._title_edit.textChanged.connect(self._screen_model.set_title)
        self._role_combo = QComboBox(self)
        self._role_combo.addItems(["primary", "supplemental", "metadata"])
        self._role_combo.currentTextChanged.connect(self._apply_selected_role)
        self._group_edit = QLineEdit(self)
        self._group_edit.setPlaceholderText("Group label")
        self._group_edit.editingFinished.connect(self._apply_selected_group)
        self._pathway_label = QLabel("custom", self)
        self._project_label = QLabel("Unsaved project", self)
        self._project_label.setWordWrap(True)
        self._grouping_label = QLabel("No grouping suggestions yet.", self)
        self._grouping_label.setWordWrap(True)
        self._summary_label = QLabel("Add files or folders to build a conversion session.", self)
        self._error_label = QLabel("", self)
        self._error_label.setWordWrap(True)
        self._selected_source_label = QLabel("No source selected.", self)
        self._selected_source_label.setWordWrap(True)
        self._selected_entry_label = QLabel("Not available.", self)
        self._selected_entry_label.setWordWrap(True)
        self._selected_bundle_label = QLabel("Not available.", self)
        self._selected_bundle_label.setWordWrap(True)
        self._selected_adapter_label = QLabel("No adapter match", self)
        self._selected_adapter_label.setWordWrap(True)
        self._selected_sidecar_label = QLabel("None", self)
        self._selected_sidecar_label.setWordWrap(True)
        self._selected_group_label = QLabel("No group selected.", self)
        self._selected_group_pathway_label = QLabel("Not available.", self)
        self._selected_group_kind_label = QLabel("Not available.", self)
        self._selected_group_workflow_label = QLabel("Not available.", self)
        self._selected_group_workflow_label.setWordWrap(True)
        self._selected_group_anchor_label = QLabel("Not available.", self)
        self._selected_group_anchor_label.setWordWrap(True)
        self._selected_group_canonical_label = QLabel("Not available.", self)
        self._selected_group_canonical_label.setWordWrap(True)
        self._selected_group_reason_label = QLabel("Not available.", self)
        self._selected_group_reason_label.setWordWrap(True)
        self._selected_group_members_label = QLabel("No group selected.", self)
        self._selected_group_members_label.setWordWrap(True)
        self._selected_group_counts_label = QLabel("No group selected.", self)
        self._selected_group_counts_label.setWordWrap(True)
        self._selected_group_edit = QLineEdit(self)
        self._selected_group_edit.setPlaceholderText("Selected group label")
        self._selected_group_edit.editingFinished.connect(self._rename_selected_group)
        self._rename_group_button = QPushButton("Rename Group", self)
        self._rename_group_button.clicked.connect(self._rename_selected_group)
        self._confirm_group_button = QPushButton("Confirm Group", self)
        self._confirm_group_button.clicked.connect(self._toggle_selected_group_confirmation)
        self._confirm_all_groups_button = QPushButton("Confirm All Groups", self)
        self._confirm_all_groups_button.clicked.connect(self._screen_model.confirm_all_groups)
        self._move_selected_sources_button = QPushButton("Move Selected Sources To Group", self)
        self._move_selected_sources_button.clicked.connect(self._move_selected_sources_to_group)
        self._create_group_from_selection_button = QPushButton("Create Group From Selection", self)
        self._create_group_from_selection_button.clicked.connect(self._create_group_from_selection)
        self._split_selection_button = QPushButton("Split Selected Sources", self)
        self._split_selection_button.clicked.connect(self._split_selected_sources)
        self._split_group_button = QPushButton("Split Group", self)
        self._split_group_button.clicked.connect(self._split_selected_group)
        self._group_action_hint_label = QLabel(
            "Select one or more sources, then confirm, split, move, or create groups before preview.",
            self,
        )
        self._group_action_hint_label.setWordWrap(True)
        self._metadata_override_edits: dict[str, QLineEdit] = {}
        self._source_metadata_override_edits: dict[str, QLineEdit] = {}
        self._source_type_combo = QComboBox(self)
        self._source_type_combo.currentIndexChanged.connect(self._update_add_controls)
        self._source_type_description_label = QLabel("", self)
        self._source_type_description_label.setWordWrap(True)
        self._source_preview_pane = FilePreviewPane(
            self,
            empty_message="Select a data source to preview its contents here.",
        )

        self._add_files_button = QPushButton("Add Files...", self)
        self._add_files_button.clicked.connect(self._add_files)
        self._add_folder_button = QPushButton("Add Folder...", self)
        self._add_folder_button.clicked.connect(self._add_folder)
        self._remove_selected_button = QPushButton("Remove Selected", self)
        self._remove_selected_button.clicked.connect(self._remove_selected_inputs)
        self._create_button = QPushButton("Create Session", self)
        self._create_button.clicked.connect(self._create_session)
        self._cancel_button = QPushButton("Cancel", self)
        self._cancel_button.clicked.connect(self.reject)
        self._remove_selected_button.setProperty("secondary", True)
        self._rename_group_button.setProperty("secondary", True)
        self._confirm_group_button.setProperty("secondary", True)
        self._confirm_all_groups_button.setProperty("secondary", True)
        self._move_selected_sources_button.setProperty("secondary", True)
        self._create_group_from_selection_button.setProperty("secondary", True)
        self._split_selection_button.setProperty("secondary", True)
        self._split_group_button.setProperty("secondary", True)
        self._cancel_button.setProperty("secondary", True)

        (
            self._header_frame,
            self._header_title_label,
            self._header_subtitle_label,
            self._header_badge_label,
        ) = build_page_header(
            "New Conversion Session",
            "Add files or folders, review detected dataset bundles, set metadata, and create a draft session before preview or write.",
            badge_text="Direct Ingest",
            parent=self,
        )

        summary_group = QGroupBox("Session Draft", self)
        summary_layout = QFormLayout(summary_group)
        summary_layout.addRow("Session ID", self._session_id_edit)
        summary_layout.addRow("Title", self._title_edit)
        summary_layout.addRow("Project", self._project_label)
        summary_layout.addRow("Workflow", self._pathway_label)
        summary_layout.addRow("Grouping", self._grouping_label)
        summary_layout.addRow("Status", self._summary_label)

        input_group = QGroupBox("Selected Inputs", self)
        input_layout = QVBoxLayout(input_group)
        source_type_row = QFormLayout()
        source_type_row.addRow("Source Type", self._source_type_combo)
        input_layout.addLayout(source_type_row)
        input_layout.addWidget(self._source_type_description_label)
        input_buttons = QHBoxLayout()
        input_buttons.addWidget(self._add_files_button)
        input_buttons.addWidget(self._add_folder_button)
        input_buttons.addWidget(self._remove_selected_button)
        input_layout.addLayout(input_buttons)
        input_layout.addWidget(self._input_list)

        source_group = QGroupBox("Data Source Preview", self)
        source_layout = QVBoxLayout(source_group)
        source_layout.addWidget(self._source_list)
        source_details = QFormLayout()
        source_details.addRow("Selected data source", self._selected_source_label)
        source_details.addRow("Structured Entry", self._selected_entry_label)
        source_details.addRow("Resolved Bundle", self._selected_bundle_label)
        source_details.addRow("Data source role", self._role_combo)
        source_details.addRow("Group", self._group_edit)
        source_details.addRow("Sidecar Association", self._selected_sidecar_label)
        source_details.addRow("Adapter Match", self._selected_adapter_label)
        source_layout.addLayout(source_details)

        group_group = QGroupBox("Detected Dataset Groups", self)
        group_layout = QVBoxLayout(group_group)
        group_layout.addWidget(self._group_list)
        group_details = QFormLayout()
        group_details.addRow("Group", self._selected_group_label)
        group_details.addRow("Workflow", self._selected_group_pathway_label)
        group_details.addRow("Kind", self._selected_group_kind_label)
        group_details.addRow("Workflow", self._selected_group_workflow_label)
        group_details.addRow("Anchor", self._selected_group_anchor_label)
        group_details.addRow("Canonical Entry", self._selected_group_canonical_label)
        group_details.addRow("Reason", self._selected_group_reason_label)
        group_details.addRow("Members", self._selected_group_members_label)
        group_details.addRow("Composition", self._selected_group_counts_label)
        group_details.addRow("Group Label", self._selected_group_edit)
        group_layout.addLayout(group_details)
        group_action_row = QHBoxLayout()
        group_action_row.addWidget(self._rename_group_button)
        group_action_row.addWidget(self._confirm_group_button)
        group_action_row.addWidget(self._confirm_all_groups_button)
        group_action_row.addWidget(self._move_selected_sources_button)
        group_action_row.addWidget(self._create_group_from_selection_button)
        group_action_row.addWidget(self._split_selection_button)
        group_action_row.addWidget(self._split_group_button)
        group_layout.addLayout(group_action_row)
        group_layout.addWidget(self._group_action_hint_label)

        metadata_group = QGroupBox("Session Metadata Overrides", self)
        metadata_layout = QFormLayout(metadata_group)
        for key, label in self._METADATA_OVERRIDE_FIELDS:
            edit = QLineEdit(self)
            edit.setPlaceholderText(label)
            edit.textChanged.connect(lambda value, field_key=key: self._screen_model.set_metadata_override(field_key, value))
            metadata_layout.addRow(label, edit)
            self._metadata_override_edits[key] = edit

        source_metadata_group = QGroupBox("Selected Data Source Metadata Overrides", self)
        source_metadata_layout = QFormLayout(source_metadata_group)
        for key, label in self._METADATA_OVERRIDE_FIELDS:
            edit = QLineEdit(self)
            edit.setPlaceholderText(f"{label} for selected source")
            edit.textChanged.connect(
                lambda value, field_key=key: self._apply_selected_source_metadata_override(field_key, value)
            )
            source_metadata_layout.addRow(label, edit)
            self._source_metadata_override_edits[key] = edit

        issue_group = QGroupBox("Assembly Issues", self)
        issue_layout = QVBoxLayout(issue_group)
        issue_layout.addWidget(self._issue_list)
        issue_layout.addWidget(self._error_label)

        left_column = QVBoxLayout()
        left_column.setContentsMargins(0, 0, 0, 0)
        left_column.setSpacing(12)
        left_column.addWidget(input_group, stretch=1)
        left_column.addWidget(source_group, stretch=1)

        grouping_page = QWidget(self)
        grouping_layout = QVBoxLayout(grouping_page)
        grouping_layout.setContentsMargins(0, 0, 0, 0)
        grouping_layout.setSpacing(12)
        grouping_layout.addWidget(group_group, stretch=2)
        grouping_layout.addWidget(issue_group, stretch=1)

        session_metadata_page = QWidget(self)
        session_metadata_layout = QVBoxLayout(session_metadata_page)
        session_metadata_layout.setContentsMargins(0, 0, 0, 0)
        session_metadata_layout.addWidget(metadata_group)
        session_metadata_layout.addStretch(1)

        source_metadata_page = QWidget(self)
        source_metadata_layout = QVBoxLayout(source_metadata_page)
        source_metadata_layout.setContentsMargins(0, 0, 0, 0)
        source_metadata_layout.addWidget(source_metadata_group)
        source_metadata_layout.addStretch(1)

        source_preview_page = QWidget(self)
        source_preview_layout = QVBoxLayout(source_preview_page)
        source_preview_layout.setContentsMargins(0, 0, 0, 0)
        source_preview_group = QGroupBox("Selected Data Source Preview", self)
        source_preview_group_layout = QVBoxLayout(source_preview_group)
        source_preview_group_layout.addWidget(self._source_preview_pane)
        source_preview_layout.addWidget(source_preview_group)
        source_preview_layout.addStretch(1)

        self._workspace_tabs = QTabWidget(self)
        self._workspace_tabs.setDocumentMode(True)
        self._workspace_tabs.setUsesScrollButtons(True)
        self._workspace_tabs.addTab(grouping_page, "Grouping")
        self._workspace_tabs.addTab(session_metadata_page, "Session Metadata")
        self._workspace_tabs.addTab(source_metadata_page, "Selected Data Source Metadata")
        self._workspace_tabs.addTab(source_preview_page, "Selected Data Source Preview")

        left_column_widget = QWidget(self)
        left_column_widget.setLayout(left_column)

        right_column = QVBoxLayout()
        right_column.setContentsMargins(0, 0, 0, 0)
        right_column.setSpacing(12)
        right_column.addWidget(self._workspace_tabs, stretch=1)

        right_column_widget = QWidget(self)
        right_column_widget.setLayout(right_column)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(left_column_widget)
        splitter.addWidget(right_column_widget)
        splitter.setChildrenCollapsible(True)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        self._workspace_splitter = splitter

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        action_row.addWidget(self._cancel_button)
        action_row.addWidget(self._create_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        content = QWidget(self)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(14)
        content_layout.addWidget(self._header_frame)
        content_layout.addWidget(summary_group)
        content_layout.addWidget(splitter, stretch=1)
        content_layout.addLayout(action_row)

        self._scroll_area = QScrollArea(self)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setWidget(content)
        layout.addWidget(self._scroll_area)

        self._bridge = StateBridge(self)
        self._bridge.state_changed.connect(self._apply_state)
        self._screen_model.subscribe(self._bridge.publish)

    def reject(self) -> None:
        self.dismissed.emit()

    def _add_files(self) -> None:
        selected_option = self._selected_source_type_option()
        if selected_option is None:
            return
        if selected_option.ingest_kind == "supported":
            selected_path, _ = QFileDialog.getOpenFileName(
                self,
                f"Add {selected_option.label} Main File",
                str(Path.cwd()),
                "All supported inputs (*.*)",
            )
            if not selected_path:
                return
            self._screen_model.add_supported_paths(
                (Path(selected_path),),
                route_name=str(selected_option.route_name or ""),
                route_display_name=selected_option.label,
            )
            return

        selected_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Add Custom Source Files",
            str(Path.cwd()),
            "All supported inputs (*.*)",
        )
        if not selected_paths:
            return
        self._screen_model.add_custom_paths(tuple(Path(path) for path in selected_paths))

    def _add_folder(self) -> None:
        selected_option = self._selected_source_type_option()
        if selected_option is None:
            return
        selected_path = QFileDialog.getExistingDirectory(
            self,
            (
                f"Add {selected_option.label} Root Folder"
                if selected_option.ingest_kind == "supported"
                else "Add Custom Source Folder"
            ),
            str(Path.cwd()),
        )
        if not selected_path:
            return
        if selected_option.ingest_kind == "supported":
            self._screen_model.add_supported_paths(
                (Path(selected_path),),
                route_name=str(selected_option.route_name or ""),
                route_display_name=selected_option.label,
            )
            return
        self._screen_model.add_custom_paths((Path(selected_path),))

    def _remove_selected_inputs(self) -> None:
        selected_paths = []
        for item in self._input_list.selectedItems():
            path_text = item.data(Qt.ItemDataRole.UserRole)
            if path_text:
                selected_paths.append(Path(path_text))
        if not selected_paths:
            return
        self._screen_model.remove_paths(tuple(selected_paths))

    def _create_session(self) -> None:
        session = self._screen_model.create_session()
        if self._session_created is not None:
            self._session_created(session)
        self.dismissed.emit()

    def _apply_state(self, state: SessionAssemblyState) -> None:
        selected_source_id = None
        selected_item = self._source_list.currentItem()
        if selected_item is not None:
            selected_source_id = selected_item.data(Qt.ItemDataRole.UserRole)

        with QSignalBlocker(self._session_id_edit):
            if self._session_id_edit.text() != state.session_id:
                self._session_id_edit.setText(state.session_id)
        with QSignalBlocker(self._title_edit):
            if self._title_edit.text() != state.title:
                self._title_edit.setText(state.title)

        self._pathway_label.setText(state.suggested_pathway)
        self._sync_source_type_options(state)
        if self._header_badge_label is not None:
            badge_text = state.suggested_pathway.title() if state.selected_paths else "Direct Ingest"
            if state.has_unsaved_changes and state.selected_paths:
                badge_text += " Draft"
            self._header_badge_label.setText(badge_text)
        project_text = "Unsaved project"
        if state.project_path is not None:
            project_text = str(state.project_path)
            if state.has_unsaved_changes:
                project_text += " (modified)"
        elif state.has_unsaved_changes and state.selected_paths:
            project_text = "Unsaved project (modified)"
        self._project_label.setText(project_text)
        unique_groups = sorted({source.group_label for source in state.sources})
        self._grouping_label.setText(", ".join(unique_groups) if unique_groups else "No grouping suggestions yet.")
        absorbed_input_paths = self._absorbed_input_paths(state)
        self._summary_label.setText(
            self._build_summary_text(state, absorbed_input_paths)
            if state.selected_paths
            else "Add files or folders to build a conversion session."
        )
        self._error_label.setText(state.error_message or "")

        self._input_list.clear()
        for path in state.selected_paths:
            source_item = next((item for item in state.sources if item.location == path), None)
            selection_prefix = f"[{source_item.selection_label}] " if source_item is not None else ""
            absorbed_suffix = " (inside structured bundle)" if path in absorbed_input_paths else ""
            item = QListWidgetItem(f"{selection_prefix}{path.name}{absorbed_suffix}")
            tooltip = str(path)
            if path in absorbed_input_paths:
                tooltip += "\nAlready represented by a selected structured source bundle."
            item.setToolTip(tooltip)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            self._input_list.addItem(item)

        self._source_list.clear()
        for source in state.sources:
            adapter_summary = ", ".join(source.matching_adapter_ids) if source.matching_adapter_ids else "no adapter match"
            item = QListWidgetItem(
                f"[{source.selection_label}] [{source.group_label}] [{source.suggested_pathway}] "
                f"{source.label} ({source.role}) -> {adapter_summary}"
            )
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
            self._sync_selected_source()

        selected_group_key = None
        selected_group_item = self._group_list.currentItem()
        if selected_group_item is not None:
            selected_group_key = selected_group_item.data(Qt.ItemDataRole.UserRole)
        self._group_list.clear()
        for group in state.groups:
            item = QListWidgetItem(
                f"[{group.suggested_pathway}] "
                f"{'[confirmed] ' if group.is_confirmed else ''}"
                f"{group.group_label} ({group.source_count} sources)"
            )
            item.setData(Qt.ItemDataRole.UserRole, group.group_key)
            self._group_list.addItem(item)
        if self._group_list.count() > 0:
            restored_group_row = 0
            if selected_group_key is not None:
                for row in range(self._group_list.count()):
                    if self._group_list.item(row).data(Qt.ItemDataRole.UserRole) == selected_group_key:
                        restored_group_row = row
                        break
            self._group_list.setCurrentRow(restored_group_row)
        else:
            self._sync_selected_group()

        self._issue_list.clear()
        for issue in state.issues:
            item = QListWidgetItem(f"[{issue.severity}] {issue.message}")
            if issue.location is not None:
                item.setToolTip(str(issue.location))
            self._issue_list.addItem(item)

        for key, edit in self._metadata_override_edits.items():
            with QSignalBlocker(edit):
                next_value = state.metadata_overrides.get(key, "")
                if edit.text() != next_value:
                    edit.setText(next_value)

        self._remove_selected_button.setEnabled(self._input_list.count() > 0)
        self._create_button.setEnabled(state.can_create_session)
        self._move_selected_sources_button.setEnabled(
            bool(self._selected_source_ids()) and self._group_list.currentItem() is not None
        )
        self._create_group_from_selection_button.setEnabled(bool(self._selected_source_ids()))
        self._split_selection_button.setEnabled(bool(self._selected_source_ids()))
        self._confirm_all_groups_button.setEnabled(bool(state.groups))
        self._header_title_label.setText(
            "New Conversion Session"
            if state.project_path is None and not state.has_unsaved_changes
            else "Conversion Project"
        )
        self._update_add_controls()

    @staticmethod
    def _absorbed_input_paths(state: SessionAssemblyState) -> set[Path]:
        return {
            issue.location.resolve()
            for issue in state.issues
            if issue.code == "session-assembly-structured-member-absorbed" and issue.location is not None
        }

    @staticmethod
    def _build_summary_text(state: SessionAssemblyState, absorbed_input_paths: set[Path]) -> str:
        summary = (
            f"{len(state.sources)} sources in {len(state.groups)} groups, "
            f"{len(state.selected_paths)} selected inputs, {len(state.issues)} issues."
        )
        if absorbed_input_paths:
            summary += f" {len(absorbed_input_paths)} input{'s' if len(absorbed_input_paths) != 1 else ''} absorbed into structured bundles."
        return summary

    def _sync_selected_source(self, *_args) -> None:
        selected_item = self._source_list.currentItem()
        if selected_item is None:
            self._selected_source_label.setText("No source selected.")
            self._selected_entry_label.setText("Not available.")
            self._selected_bundle_label.setText("Not available.")
            self._selected_adapter_label.setText("No adapter match")
            self._selected_sidecar_label.setText("None")
            self._source_preview_pane.set_preview_path(None)
            with QSignalBlocker(self._role_combo):
                self._role_combo.setCurrentText("primary")
            with QSignalBlocker(self._group_edit):
                self._group_edit.setText("")
            for edit in self._source_metadata_override_edits.values():
                with QSignalBlocker(edit):
                    edit.setText("")
            self._role_combo.setEnabled(False)
            self._group_edit.setEnabled(False)
            for edit in self._source_metadata_override_edits.values():
                edit.setEnabled(False)
            self._move_selected_sources_button.setEnabled(False)
            self._create_group_from_selection_button.setEnabled(False)
            return

        source_id = selected_item.data(Qt.ItemDataRole.UserRole)
        source = next((item for item in self._screen_model.state.sources if item.source_id == source_id), None)
        if source is None:
            self._selected_source_label.setText("No source selected.")
            self._selected_entry_label.setText("Not available.")
            self._selected_bundle_label.setText("Not available.")
            self._selected_adapter_label.setText("No adapter match")
            self._selected_sidecar_label.setText("None")
            self._source_preview_pane.set_preview_path(None)
            with QSignalBlocker(self._role_combo):
                self._role_combo.setCurrentText("primary")
            with QSignalBlocker(self._group_edit):
                self._group_edit.setText("")
            for edit in self._source_metadata_override_edits.values():
                with QSignalBlocker(edit):
                    edit.setText("")
            self._role_combo.setEnabled(False)
            self._group_edit.setEnabled(False)
            for edit in self._source_metadata_override_edits.values():
                edit.setEnabled(False)
            self._move_selected_sources_button.setEnabled(False)
            self._create_group_from_selection_button.setEnabled(False)
            return

        self._selected_source_label.setText(f"{source.label}\nGroup: {source.group_label}\n{source.location}")
        self._source_preview_pane.set_preview_path(source.location)
        entry_text = "Custom or unstructured input."
        bundle_text = "Custom or unstructured input."
        if source.ingest_kind == "supported":
            entry_role_label = source.entry_role_label or (
                "root directory" if source.entry_path_kind == "directory" else "main file"
            )
            validation_status = source.entry_validation_status or "review"
            entry_text = (
                f"{source.selection_label} {entry_role_label}\n"
                f"Entry type: {source.entry_path_kind or source.source_type.lower()}\n"
                f"Validation: {validation_status}"
            )
            if source.structured_bundle_member_count:
                bundle_examples = ", ".join(source.structured_bundle_member_labels)
                bundle_text = (
                    f"{source.structured_bundle_member_count} resolved member"
                    f"{'' if source.structured_bundle_member_count == 1 else 's'}\n"
                    f"{bundle_examples}"
                )
            else:
                bundle_text = "No additional bundle members detected."
        self._selected_entry_label.setText(entry_text)
        self._selected_bundle_label.setText(bundle_text)
        adapter_summary = ", ".join(source.matching_adapter_ids) if source.matching_adapter_ids else "No adapter match"
        self._selected_adapter_label.setText(adapter_summary)
        self._selected_sidecar_label.setText(source.sidecar_for_label or "None")
        with QSignalBlocker(self._role_combo):
            self._role_combo.setCurrentText(source.role)
        with QSignalBlocker(self._group_edit):
            self._group_edit.setText(source.group_label)
        for key, edit in self._source_metadata_override_edits.items():
            with QSignalBlocker(edit):
                edit.setText(source.metadata_overrides.get(key, ""))
        self._role_combo.setEnabled(True)
        self._group_edit.setEnabled(True)
        for edit in self._source_metadata_override_edits.values():
            edit.setEnabled(True)
        self._move_selected_sources_button.setEnabled(
            bool(self._selected_source_ids()) and self._group_list.currentItem() is not None
        )
        self._create_group_from_selection_button.setEnabled(bool(self._selected_source_ids()))
        group_row = next(
            (
                row
                for row in range(self._group_list.count())
                if self._group_list.item(row).data(Qt.ItemDataRole.UserRole) == source.group_key
            ),
            None,
        )
        if group_row is not None:
            with QSignalBlocker(self._group_list):
                self._group_list.setCurrentRow(group_row)

    def _sync_selected_group(self, *_args) -> None:
        selected_item = self._group_list.currentItem()
        if selected_item is None:
            self._selected_group_label.setText("No group selected.")
            self._selected_group_pathway_label.setText("Not available.")
            self._selected_group_kind_label.setText("Not available.")
            self._selected_group_workflow_label.setText("Not available.")
            self._selected_group_anchor_label.setText("Not available.")
            self._selected_group_canonical_label.setText("Not available.")
            self._selected_group_reason_label.setText("Not available.")
            self._selected_group_members_label.setText("No group selected.")
            self._selected_group_counts_label.setText("No group selected.")
            with QSignalBlocker(self._selected_group_edit):
                self._selected_group_edit.setText("")
            self._rename_group_button.setEnabled(False)
            self._confirm_group_button.setEnabled(False)
            self._confirm_group_button.setText("Confirm Group")
            self._move_selected_sources_button.setEnabled(False)
            self._create_group_from_selection_button.setEnabled(bool(self._selected_source_ids()))
            self._split_selection_button.setEnabled(bool(self._selected_source_ids()))
            self._split_group_button.setEnabled(False)
            return

        group_key = selected_item.data(Qt.ItemDataRole.UserRole)
        group = next((item for item in self._screen_model.state.groups if item.group_key == group_key), None)
        if group is None:
            self._selected_group_label.setText("No group selected.")
            self._selected_group_pathway_label.setText("Not available.")
            self._selected_group_kind_label.setText("Not available.")
            self._selected_group_workflow_label.setText("Not available.")
            self._selected_group_anchor_label.setText("Not available.")
            self._selected_group_canonical_label.setText("Not available.")
            self._selected_group_reason_label.setText("Not available.")
            self._selected_group_members_label.setText("No group selected.")
            self._selected_group_counts_label.setText("No group selected.")
            with QSignalBlocker(self._selected_group_edit):
                self._selected_group_edit.setText("")
            self._rename_group_button.setEnabled(False)
            self._confirm_group_button.setEnabled(False)
            self._confirm_group_button.setText("Confirm Group")
            self._move_selected_sources_button.setEnabled(False)
            self._create_group_from_selection_button.setEnabled(bool(self._selected_source_ids()))
            self._split_selection_button.setEnabled(bool(self._selected_source_ids()))
            self._split_group_button.setEnabled(False)
            return

        self._selected_group_label.setText(group.group_label)
        self._selected_group_pathway_label.setText(group.suggested_pathway)
        self._selected_group_kind_label.setText(group.group_kind.replace("_", " "))
        self._selected_group_workflow_label.setText(group.workflow_display_name or "Not available.")
        self._selected_group_anchor_label.setText(str(group.anchor_path) if group.anchor_path is not None else "Not available.")
        canonical_text = "Not available."
        if group.canonical_source_label is not None:
            bundle_summary = ""
            if group.canonical_bundle_member_count:
                bundle_examples = ", ".join(group.canonical_bundle_member_labels)
                bundle_summary = (
                    f"\nResolved bundle members: {group.canonical_bundle_member_count}"
                    f"\n{bundle_examples}"
                )
            canonical_text = (
                f"{group.canonical_source_label}\n"
                f"{group.canonical_selection_label or 'Structured source'} "
                f"{group.canonical_entry_role_label or 'entry'}\n"
                f"{group.canonical_source_path}"
                f"{bundle_summary}"
            )
        self._selected_group_canonical_label.setText(canonical_text)
        self._selected_group_reason_label.setText(group.grouping_reason or "No grouping reason available.")
        self._selected_group_members_label.setText(", ".join(group.member_labels) if group.member_labels else "No members listed.")
        self._selected_group_counts_label.setText(
            f"{group.primary_count} primary, {group.supplemental_count} supplemental, "
            f"{group.metadata_count} metadata"
            + (f" | {group.review_issue_count} review flags" if group.review_issue_count else "")
            + (" | confirmation required" if group.requires_confirmation else "")
            + (" | review needed" if group.needs_review else "")
            + (" | confirmed" if group.is_confirmed else "")
        )
        with QSignalBlocker(self._selected_group_edit):
            self._selected_group_edit.setText(group.group_label)
        self._rename_group_button.setEnabled(True)
        self._confirm_group_button.setEnabled(True)
        self._confirm_group_button.setText("Unconfirm Group" if group.is_confirmed else "Confirm Group")
        self._confirm_all_groups_button.setEnabled(bool(self._screen_model.state.groups))
        self._move_selected_sources_button.setEnabled(bool(self._selected_source_ids()))
        self._create_group_from_selection_button.setEnabled(bool(self._selected_source_ids()))
        self._split_selection_button.setEnabled(bool(self._selected_source_ids()))
        self._split_group_button.setEnabled(group.source_count > 1)

    def _apply_selected_role(self, role: str) -> None:
        selected_item = self._source_list.currentItem()
        if selected_item is None:
            return
        source_id = selected_item.data(Qt.ItemDataRole.UserRole)
        if source_id is None:
            return
        self._screen_model.set_source_role(str(source_id), role)

    def _apply_selected_group(self) -> None:
        selected_item = self._source_list.currentItem()
        if selected_item is None:
            return
        source_id = selected_item.data(Qt.ItemDataRole.UserRole)
        if source_id is None:
            return
        self._screen_model.set_source_group_label(str(source_id), self._group_edit.text())

    def _selected_source_type_option(self) -> SessionAssemblySourceTypeOption | None:
        selected_index = self._source_type_combo.currentIndex()
        if selected_index < 0:
            return None
        option = self._source_type_combo.itemData(selected_index, Qt.ItemDataRole.UserRole)
        if isinstance(option, SessionAssemblySourceTypeOption):
            return option
        return None

    def _sync_source_type_options(self, state: SessionAssemblyState) -> None:
        current_key = self._source_type_combo.currentData(Qt.ItemDataRole.UserRole)
        current_label = None
        if isinstance(current_key, SessionAssemblySourceTypeOption):
            current_label = (current_key.ingest_kind, current_key.route_name or "")

        with QSignalBlocker(self._source_type_combo):
            self._source_type_combo.clear()
            for option in state.source_type_options:
                self._source_type_combo.addItem(option.label, option)

            restored_index = 0
            if current_label is not None:
                for index, option in enumerate(state.source_type_options):
                    if (option.ingest_kind, option.route_name or "") == current_label:
                        restored_index = index
                        break
            if state.source_type_options:
                self._source_type_combo.setCurrentIndex(restored_index)

    def _update_add_controls(self) -> None:
        selected_option = self._selected_source_type_option()
        if selected_option is None:
            self._source_type_description_label.setText("")
            self._add_files_button.setText("Add Files...")
            self._add_folder_button.setText("Add Folder...")
            return
        self._source_type_description_label.setText(selected_option.description)
        if selected_option.ingest_kind == "supported":
            self._add_files_button.setText(f"Add {selected_option.label} File...")
            self._add_folder_button.setText(f"Add {selected_option.label} Folder...")
            return
        self._add_files_button.setText("Add Custom Files...")
        self._add_folder_button.setText("Add Custom Folder...")

    def _selected_source_ids(self) -> tuple[str, ...]:
        source_ids: list[str] = []
        for item in self._source_list.selectedItems():
            source_id = item.data(Qt.ItemDataRole.UserRole)
            if source_id is not None:
                source_ids.append(str(source_id))
        return tuple(source_ids)

    def _rename_selected_group(self) -> None:
        selected_item = self._group_list.currentItem()
        if selected_item is None:
            return
        group_key = selected_item.data(Qt.ItemDataRole.UserRole)
        if group_key is None:
            return
        self._screen_model.rename_group(str(group_key), self._selected_group_edit.text())

    def _move_selected_sources_to_group(self) -> None:
        source_ids = self._selected_source_ids()
        if not source_ids:
            return
        target_label = self._selected_group_edit.text().strip() or self._selected_group_label.text().strip()
        if not target_label:
            return
        self._screen_model.set_group_label_for_sources(source_ids, target_label)

    def _create_group_from_selection(self) -> None:
        source_ids = self._selected_source_ids()
        if not source_ids:
            return
        group_label = self._selected_group_edit.text().strip()
        if not group_label:
            return
        self._screen_model.set_group_label_for_sources(source_ids, group_label)

    def _split_selected_sources(self) -> None:
        source_ids = self._selected_source_ids()
        if not source_ids:
            return
        self._screen_model.split_sources_into_individual_groups(source_ids)

    def _split_selected_group(self) -> None:
        selected_item = self._group_list.currentItem()
        if selected_item is None:
            return
        group_key = selected_item.data(Qt.ItemDataRole.UserRole)
        if group_key is None:
            return
        self._screen_model.split_group(str(group_key))

    def _toggle_selected_group_confirmation(self) -> None:
        selected_item = self._group_list.currentItem()
        if selected_item is None:
            return
        group_key = selected_item.data(Qt.ItemDataRole.UserRole)
        if group_key is None:
            return
        group = next(
            (item for item in self._screen_model.state.groups if item.group_key == str(group_key)),
            None,
        )
        if group is None:
            return
        if group.is_confirmed:
            self._screen_model.unconfirm_group(str(group_key))
            return
        self._screen_model.confirm_group(str(group_key))

    def _apply_selected_source_metadata_override(self, key: str, value: str) -> None:
        selected_item = self._source_list.currentItem()
        if selected_item is None:
            return
        source_id = selected_item.data(Qt.ItemDataRole.UserRole)
        if source_id is None:
            return
        self._screen_model.set_source_metadata_override(str(source_id), key, value)
