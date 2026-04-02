"""Qt dialog for direct file/folder session assembly."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import (
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
        self._source_list = QListWidget(self)
        self._source_list.currentItemChanged.connect(self._sync_selected_source)
        self._issue_list = QListWidget(self)
        self._session_id_edit = QLineEdit(self)
        self._session_id_edit.textChanged.connect(self._screen_model.set_session_id)
        self._title_edit = QLineEdit(self)
        self._title_edit.textChanged.connect(self._screen_model.set_title)
        self._role_combo = QComboBox(self)
        self._role_combo.addItems(["primary", "supplemental", "metadata"])
        self._role_combo.currentTextChanged.connect(self._apply_selected_role)
        self._pathway_label = QLabel("custom", self)
        self._summary_label = QLabel("Add files or folders to build a conversion session.", self)
        self._error_label = QLabel("", self)
        self._error_label.setWordWrap(True)
        self._selected_source_label = QLabel("No source selected.", self)
        self._selected_source_label.setWordWrap(True)
        self._selected_adapter_label = QLabel("No adapter match", self)
        self._selected_adapter_label.setWordWrap(True)
        self._metadata_override_edits: dict[str, QLineEdit] = {}

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
        summary_layout.addRow("Pathway", self._pathway_label)
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
        source_details.addRow("Adapter Match", self._selected_adapter_label)
        source_layout.addLayout(source_details)

        metadata_group = QGroupBox("Metadata Overrides", self)
        metadata_layout = QFormLayout(metadata_group)
        for key, label in self._METADATA_OVERRIDE_FIELDS:
            edit = QLineEdit(self)
            edit.setPlaceholderText(label)
            edit.textChanged.connect(lambda value, field_key=key: self._screen_model.set_metadata_override(field_key, value))
            metadata_layout.addRow(label, edit)
            self._metadata_override_edits[key] = edit

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
        layout.addWidget(source_group, stretch=1)
        layout.addWidget(metadata_group)
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
        with QSignalBlocker(self._session_id_edit):
            if self._session_id_edit.text() != state.session_id:
                self._session_id_edit.setText(state.session_id)
        with QSignalBlocker(self._title_edit):
            if self._title_edit.text() != state.title:
                self._title_edit.setText(state.title)

        self._pathway_label.setText(state.suggested_pathway)
        self._summary_label.setText(
            f"{len(state.sources)} sources, {len(state.issues)} issues."
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
                f"[{source.suggested_pathway}] {source.label} ({source.role}) -> {adapter_summary}"
            )
            item.setToolTip(str(source.location))
            item.setData(Qt.ItemDataRole.UserRole, source.source_id)
            self._source_list.addItem(item)
        if self._source_list.count() > 0:
            self._source_list.setCurrentRow(0)
        else:
            self._sync_selected_source()

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

    def _sync_selected_source(self, *_args) -> None:
        selected_item = self._source_list.currentItem()
        if selected_item is None:
            self._selected_source_label.setText("No source selected.")
            self._selected_adapter_label.setText("No adapter match")
            with QSignalBlocker(self._role_combo):
                self._role_combo.setCurrentText("primary")
            self._role_combo.setEnabled(False)
            return

        source_id = selected_item.data(Qt.ItemDataRole.UserRole)
        source = next((item for item in self._screen_model.state.sources if item.source_id == source_id), None)
        if source is None:
            self._selected_source_label.setText("No source selected.")
            self._selected_adapter_label.setText("No adapter match")
            with QSignalBlocker(self._role_combo):
                self._role_combo.setCurrentText("primary")
            self._role_combo.setEnabled(False)
            return

        self._selected_source_label.setText(f"{source.label}\n{source.location}")
        adapter_summary = ", ".join(source.matching_adapter_ids) if source.matching_adapter_ids else "No adapter match"
        self._selected_adapter_label.setText(adapter_summary)
        with QSignalBlocker(self._role_combo):
            self._role_combo.setCurrentText(source.role)
        self._role_combo.setEnabled(True)

    def _apply_selected_role(self, role: str) -> None:
        selected_item = self._source_list.currentItem()
        if selected_item is None:
            return
        source_id = selected_item.data(Qt.ItemDataRole.UserRole)
        if source_id is None:
            return
        self._screen_model.set_source_role(str(source_id), role)
