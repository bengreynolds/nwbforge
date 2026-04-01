"""Qt dialog for desktop settings."""

from __future__ import annotations

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from nwbforge.ui.models import SettingsScreenState
from nwbforge.ui.qt.bridge import StateBridge
from nwbforge.ui.settings import SettingsScreenModel


class SettingsDialog(QDialog):
    """Dialog bound to `SettingsScreenModel`."""

    def __init__(self, screen_model: SettingsScreenModel, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(560, 260)
        self._screen_model = screen_model

        self._verbose_checkbox = QCheckBox("Enable verbose logging", self)
        self._verbose_checkbox.toggled.connect(self._screen_model.set_verbose_logging_enabled)

        self._file_logging_checkbox = QCheckBox("Mirror logs to file", self)
        self._file_logging_checkbox.toggled.connect(self._screen_model.set_file_logging_enabled)

        self._log_path_edit = QLineEdit(self)
        self._log_path_edit.textChanged.connect(self._screen_model.set_log_file_path)

        self._status_label = QLabel("Loading settings...", self)
        self._status_label.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.addRow(self._verbose_checkbox)
        form_layout.addRow(self._file_logging_checkbox)
        form_layout.addRow("Log file path", self._log_path_edit)

        self._save_button = QPushButton("Save", self)
        self._save_button.clicked.connect(self._screen_model.save)
        self._discard_button = QPushButton("Discard", self)
        self._discard_button.clicked.connect(self._screen_model.discard_changes)
        self._close_button = QPushButton("Close", self)
        self._close_button.clicked.connect(self.reject)

        button_row = QHBoxLayout()
        button_row.addWidget(self._save_button)
        button_row.addWidget(self._discard_button)
        button_row.addStretch(1)
        button_row.addWidget(self._close_button)

        button_widget = QWidget(self)
        button_widget.setLayout(button_row)

        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addWidget(self._status_label)
        layout.addWidget(button_widget)

        self._bridge = StateBridge(self)
        self._bridge.state_changed.connect(self._apply_state)
        self._screen_model.subscribe(self._bridge.publish)
        self._screen_model.load()

    def _apply_state(self, state: SettingsScreenState) -> None:
        with QSignalBlocker(self._verbose_checkbox):
            self._verbose_checkbox.setChecked(state.verbose_logging_enabled)

        with QSignalBlocker(self._file_logging_checkbox):
            self._file_logging_checkbox.setChecked(state.file_logging_enabled)

        with QSignalBlocker(self._log_path_edit):
            if self._log_path_edit.text() != state.log_file_path:
                self._log_path_edit.setText(state.log_file_path)

        self._log_path_edit.setEnabled(state.file_logging_enabled)
        self._discard_button.setEnabled(state.has_unsaved_changes)
        self._save_button.setEnabled(state.has_unsaved_changes)
        self._status_label.setText(state.user_error.message if state.user_error is not None else state.status_message)
