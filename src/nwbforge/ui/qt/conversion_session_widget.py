"""Qt widget for one conversion-session workflow."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

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
        self._status_label = QLabel("Ready.", self)
        self._result_label = QLabel("No preview or execution yet.", self)

        form_layout = QFormLayout()
        form_layout.addRow("Session", self._session_label)
        form_layout.addRow("Output", self._output_path_edit)

        button_row = QHBoxLayout()
        button_row.addWidget(self._preview_button)
        button_row.addWidget(self._execute_button)

        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addWidget(QLabel("Sources", self))
        layout.addWidget(self._source_list, stretch=1)
        layout.addLayout(button_row)
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

        if state.output_path is not None and self._output_path_edit.text() != str(state.output_path):
            self._output_path_edit.setText(str(state.output_path))

        self._preview_button.setEnabled(state.can_run_preview)
        self._refresh_execute_enabled()

    def _sync_sources(self, state: ConversionSessionScreenState) -> None:
        self._source_list.clear()
        for source in state.sources:
            item = QListWidgetItem(f"{source.label} [{source.source_type}]")
            item.setToolTip(str(source.location))
            self._source_list.addItem(item)

    def _refresh_execute_enabled(self) -> None:
        state = self._screen_model.state
        self._execute_button.setEnabled(state.can_run_execution and bool(self._output_path_edit.text().strip()))

    def _on_execute_clicked(self) -> None:
        output_text = self._output_path_edit.text().strip()
        if not output_text:
            self._status_label.setText("Output path is required before writing NWB.")
            return
        self._screen_model.start_execution(Path(output_text))
