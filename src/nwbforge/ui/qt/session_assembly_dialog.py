"""Qt dialog for direct file/folder session assembly."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from nwbforge.domain.models import ConversionSession
from nwbforge.ui.models import SessionAssemblyState
from nwbforge.ui.qt.bridge import StateBridge
from nwbforge.ui.session_assembly import SessionAssemblyScreenModel


class SessionAssemblyDialog(QDialog):
    """Dialog bound to `SessionAssemblyScreenModel` for direct source ingestion."""

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
        self.setWindowTitle("New Conversion Session")
        self.resize(760, 620)

        self._screen_model = screen_model
        self._session_created = session_created

        self._input_list = QListWidget(self)
        self._group_list = QListWidget(self)
        self._source_list = QListWidget(self)
        self._source_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._source_list.currentItemChanged.connect(self._sync_selected_source)
        self._group_list.currentItemChanged.connect(self._sync_selected_group)
        self._issue_list = QListWidget(self)
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
        self._selected_adapter_label = QLabel("No adapter match", self)
        self._selected_adapter_label.setWordWrap(True)
        self._selected_sidecar_label = QLabel("None", self)
        self._selected_sidecar_label.setWordWrap(True)
        self._selected_group_label = QLabel("No group selected.", self)
        self._selected_group_pathway_label = QLabel("Not available.", self)
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
        self._group_action_hint_label = QLabel(
            "Select one or more sources, then confirm, split, move, or create groups before preview.",
            self,
        )
        self._group_action_hint_label.setWordWrap(True)
        self._metadata_override_edits: dict[str, QLineEdit] = {}
        self._source_metadata_override_edits: dict[str, QLineEdit] = {}

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

        summary_group = QGroupBox("Session Draft", self)
        summary_layout = QFormLayout(summary_group)
        summary_layout.addRow("Session ID", self._session_id_edit)
        summary_layout.addRow("Title", self._title_edit)
        summary_layout.addRow("Project", self._project_label)
        summary_layout.addRow("Pathway", self._pathway_label)
        summary_layout.addRow("Grouping", self._grouping_label)
        summary_layout.addRow("Status", self._summary_label)

        input_group = QGroupBox("Selected Inputs", self)
        input_layout = QVBoxLayout(input_group)
        input_buttons = QHBoxLayout()
        input_buttons.addWidget(self._add_files_button)
        input_buttons.addWidget(self._add_folder_button)
        input_buttons.addWidget(self._remove_selected_button)
        input_layout.addLayout(input_buttons)
        input_layout.addWidget(self._input_list)

        source_group = QGroupBox("Source Assembly Preview", self)
        source_layout = QVBoxLayout(source_group)
        source_layout.addWidget(self._source_list)
        source_details = QFormLayout()
        source_details.addRow("Selected Source", self._selected_source_label)
        source_details.addRow("Role", self._role_combo)
        source_details.addRow("Group", self._group_edit)
        source_details.addRow("Sidecar Association", self._selected_sidecar_label)
        source_details.addRow("Adapter Match", self._selected_adapter_label)
        source_layout.addLayout(source_details)

        group_group = QGroupBox("Detected Dataset Groups", self)
        group_layout = QVBoxLayout(group_group)
        group_layout.addWidget(self._group_list)
        group_details = QFormLayout()
        group_details.addRow("Group", self._selected_group_label)
        group_details.addRow("Pathway", self._selected_group_pathway_label)
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
        group_layout.addLayout(group_action_row)
        group_layout.addWidget(self._group_action_hint_label)

        metadata_group = QGroupBox("Metadata Overrides", self)
        metadata_layout = QFormLayout(metadata_group)
        for key, label in self._METADATA_OVERRIDE_FIELDS:
            edit = QLineEdit(self)
            edit.setPlaceholderText(label)
            edit.textChanged.connect(lambda value, field_key=key: self._screen_model.set_metadata_override(field_key, value))
            metadata_layout.addRow(label, edit)
            self._metadata_override_edits[key] = edit

        source_metadata_group = QGroupBox("Selected Source Metadata Overrides", self)
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

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        action_row.addWidget(self._cancel_button)
        action_row.addWidget(self._create_button)

        layout = QVBoxLayout(self)
        layout.addWidget(summary_group)
        layout.addWidget(input_group, stretch=1)
        layout.addWidget(group_group, stretch=1)
        layout.addWidget(source_group, stretch=1)
        layout.addWidget(metadata_group)
        layout.addWidget(source_metadata_group)
        layout.addWidget(issue_group, stretch=1)
        layout.addLayout(action_row)

        self._bridge = StateBridge(self)
        self._bridge.state_changed.connect(self._apply_state)
        self._screen_model.subscribe(self._bridge.publish)

    def _add_files(self) -> None:
        selected_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Add Source Files",
            str(Path.cwd()),
            "All supported inputs (*.*)",
        )
        if not selected_paths:
            return
        self._screen_model.add_paths(tuple(Path(path) for path in selected_paths))

    def _add_folder(self) -> None:
        selected_path = QFileDialog.getExistingDirectory(
            self,
            "Add Source Folder",
            str(Path.cwd()),
        )
        if not selected_path:
            return
        self._screen_model.add_paths((Path(selected_path),))

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
        self.accept()

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
        self._summary_label.setText(
            f"{len(state.sources)} sources in {len(state.groups)} groups, {len(state.issues)} issues."
            if state.selected_paths
            else "Add files or folders to build a conversion session."
        )
        self._error_label.setText(state.error_message or "")

        self._input_list.clear()
        for path in state.selected_paths:
            item = QListWidgetItem(path.name)
            item.setToolTip(str(path))
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            self._input_list.addItem(item)

        self._source_list.clear()
        for source in state.sources:
            adapter_summary = ", ".join(source.matching_adapter_ids) if source.matching_adapter_ids else "no adapter match"
            item = QListWidgetItem(
                f"[{source.group_label}] [{source.suggested_pathway}] {source.label} ({source.role}) -> {adapter_summary}"
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
        self.setWindowTitle(
            "New Conversion Session"
            if state.project_path is None and not state.has_unsaved_changes
            else "Conversion Project"
            + (" *" if state.has_unsaved_changes else "")
        )

    def _sync_selected_source(self, *_args) -> None:
        selected_item = self._source_list.currentItem()
        if selected_item is None:
            self._selected_source_label.setText("No source selected.")
            self._selected_adapter_label.setText("No adapter match")
            self._selected_sidecar_label.setText("None")
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
            self._selected_adapter_label.setText("No adapter match")
            self._selected_sidecar_label.setText("None")
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
            self._selected_group_counts_label.setText("No group selected.")
            with QSignalBlocker(self._selected_group_edit):
                self._selected_group_edit.setText("")
            self._rename_group_button.setEnabled(False)
            self._confirm_group_button.setEnabled(False)
            self._confirm_group_button.setText("Confirm Group")
            self._move_selected_sources_button.setEnabled(False)
            self._create_group_from_selection_button.setEnabled(bool(self._selected_source_ids()))
            self._split_selection_button.setEnabled(bool(self._selected_source_ids()))
            return

        group_key = selected_item.data(Qt.ItemDataRole.UserRole)
        group = next((item for item in self._screen_model.state.groups if item.group_key == group_key), None)
        if group is None:
            self._selected_group_label.setText("No group selected.")
            self._selected_group_pathway_label.setText("Not available.")
            self._selected_group_counts_label.setText("No group selected.")
            with QSignalBlocker(self._selected_group_edit):
                self._selected_group_edit.setText("")
            self._rename_group_button.setEnabled(False)
            self._confirm_group_button.setEnabled(False)
            self._confirm_group_button.setText("Confirm Group")
            self._move_selected_sources_button.setEnabled(False)
            self._create_group_from_selection_button.setEnabled(bool(self._selected_source_ids()))
            self._split_selection_button.setEnabled(bool(self._selected_source_ids()))
            return

        self._selected_group_label.setText(group.group_label)
        self._selected_group_pathway_label.setText(group.suggested_pathway)
        self._selected_group_counts_label.setText(
            f"{group.primary_count} primary, {group.supplemental_count} supplemental, "
            f"{group.metadata_count} metadata"
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
