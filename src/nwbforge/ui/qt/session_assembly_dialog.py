"""Qt dialog for direct file/folder session assembly."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import (
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
        self._issue_list = QListWidget(self)
        self._session_id_edit = QLineEdit(self)
        self._session_id_edit.textChanged.connect(self._screen_model.set_session_id)
        self._title_edit = QLineEdit(self)
        self._title_edit.textChanged.connect(self._screen_model.set_title)
        self._pathway_label = QLabel("custom", self)
        self._summary_label = QLabel("Add files or folders to build a conversion session.", self)
        self._error_label = QLabel("", self)
        self._error_label.setWordWrap(True)

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
                f"[{source.suggested_pathway}] {source.label} -> {adapter_summary}"
            )
            item.setToolTip(str(source.location))
            self._source_list.addItem(item)

        self._issue_list.clear()
        for issue in state.issues:
            item = QListWidgetItem(f"[{issue.severity}] {issue.message}")
            if issue.location is not None:
                item.setToolTip(str(issue.location))
            self._issue_list.addItem(item)

        self._remove_selected_button.setEnabled(self._input_list.count() > 0)
        self._create_button.setEnabled(state.can_create_session)
