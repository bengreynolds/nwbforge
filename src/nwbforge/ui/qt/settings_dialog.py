"""Qt dialog for desktop settings."""

from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from nwbforge.ui.models import SettingsScreenState
from nwbforge.ui.qt.bridge import StateBridge
from nwbforge.ui.settings import SettingsScreenModel
from nwbforge.ui.qt.styling import apply_window_chrome, build_page_header


class SettingsDialog(QWidget):
    """Embedded panel bound to `SettingsScreenModel`."""

    dismissed = Signal()

    def __init__(self, screen_model: SettingsScreenModel, parent=None) -> None:
        super().__init__(parent)
        self.resize(640, 360)
        apply_window_chrome(self)
        self._screen_model = screen_model

        self._verbose_checkbox = QCheckBox("Enable verbose logging", self)
        self._verbose_checkbox.toggled.connect(self._screen_model.set_verbose_logging_enabled)

        self._file_logging_checkbox = QCheckBox("Mirror logs to file", self)
        self._file_logging_checkbox.toggled.connect(self._screen_model.set_file_logging_enabled)

        self._log_path_edit = QLineEdit(self)
        self._log_path_edit.textChanged.connect(self._screen_model.set_log_file_path)

        self._restore_snapshot_checkbox = QCheckBox("Restore latest snapshot when loading a session", self)
        self._restore_snapshot_checkbox.toggled.connect(self._screen_model.set_restore_latest_snapshot_on_load)

        self._recent_item_limit_spin = QSpinBox(self)
        self._recent_item_limit_spin.setRange(1, 25)
        self._recent_item_limit_spin.valueChanged.connect(self._screen_model.set_recent_item_limit)

        self._snapshot_history_limit_spin = QSpinBox(self)
        self._snapshot_history_limit_spin.setRange(1, 50)
        self._snapshot_history_limit_spin.valueChanged.connect(self._screen_model.set_snapshot_history_limit)

        self._status_label = QLabel("Loading settings...", self)
        self._status_label.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.addRow(self._verbose_checkbox)
        form_layout.addRow(self._file_logging_checkbox)
        form_layout.addRow("Log file path", self._log_path_edit)

        recovery_layout = QFormLayout()
        recovery_layout.addRow(self._restore_snapshot_checkbox)
        recovery_layout.addRow("Recent history size", self._recent_item_limit_spin)
        recovery_layout.addRow("Snapshot history size", self._snapshot_history_limit_spin)

        self._save_button = QPushButton("Save", self)
        self._save_button.clicked.connect(self._screen_model.save)
        self._discard_button = QPushButton("Discard", self)
        self._discard_button.clicked.connect(self._screen_model.discard_changes)
        self._close_button = QPushButton("Close", self)
        self._close_button.clicked.connect(self.reject)
        self._discard_button.setProperty("secondary", True)
        self._close_button.setProperty("secondary", True)

        (
            self._header_frame,
            self._header_title_label,
            self._header_subtitle_label,
            self._header_badge_label,
        ) = build_page_header(
            "Settings",
            "Control desktop logging behavior, file-log mirroring, and other persisted local preferences.",
            badge_text="Desktop Preferences",
            parent=self,
        )

        logging_group = QGroupBox("Logging", self)
        logging_group.setLayout(form_layout)

        recovery_group = QGroupBox("Recovery and History", self)
        recovery_group.setLayout(recovery_layout)

        button_row = QHBoxLayout()
        button_row.addWidget(self._save_button)
        button_row.addWidget(self._discard_button)
        button_row.addStretch(1)
        button_row.addWidget(self._close_button)

        button_widget = QWidget(self)
        button_widget.setLayout(button_row)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        content = QWidget(self)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(14)
        content_layout.addWidget(self._header_frame)
        content_layout.addWidget(logging_group)
        content_layout.addWidget(recovery_group)
        content_layout.addWidget(self._status_label)
        content_layout.addWidget(button_widget)
        content_layout.addStretch(1)

        self._scroll_area = QScrollArea(self)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setWidget(content)
        layout.addWidget(self._scroll_area)

        self._bridge = StateBridge(self)
        self._bridge.state_changed.connect(self._apply_state)
        self._screen_model.subscribe(self._bridge.publish)
        self._screen_model.load()

    def reject(self) -> None:
        self.dismissed.emit()

    def _apply_state(self, state: SettingsScreenState) -> None:
        with QSignalBlocker(self._verbose_checkbox):
            self._verbose_checkbox.setChecked(state.verbose_logging_enabled)

        with QSignalBlocker(self._file_logging_checkbox):
            self._file_logging_checkbox.setChecked(state.file_logging_enabled)

        with QSignalBlocker(self._log_path_edit):
            if self._log_path_edit.text() != state.log_file_path:
                self._log_path_edit.setText(state.log_file_path)

        with QSignalBlocker(self._restore_snapshot_checkbox):
            self._restore_snapshot_checkbox.setChecked(state.restore_latest_snapshot_on_load)

        with QSignalBlocker(self._recent_item_limit_spin):
            self._recent_item_limit_spin.setValue(state.recent_item_limit)

        with QSignalBlocker(self._snapshot_history_limit_spin):
            self._snapshot_history_limit_spin.setValue(state.snapshot_history_limit)

        self._log_path_edit.setEnabled(state.file_logging_enabled)
        self._discard_button.setEnabled(state.has_unsaved_changes)
        self._save_button.setEnabled(state.has_unsaved_changes)
        self._status_label.setText(state.user_error.message if state.user_error is not None else state.status_message)
