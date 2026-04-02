"""Qt log-viewer widgets."""

from __future__ import annotations

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QDockWidget, QPlainTextEdit, QWidget

from nwbforge.ui.logs import UiLogEntry


def format_log_entry(entry: UiLogEntry) -> str:
    timestamp = entry.created_at.isoformat(timespec="seconds")
    if entry.context:
        return f"[{timestamp}] {entry.level_name} {entry.logger_name}: {entry.message} | {entry.context}"
    return f"[{timestamp}] {entry.level_name} {entry.logger_name}: {entry.message}"


class LogViewerDockWidget(QDockWidget):
    """Dockable log viewer backed by UI log entries."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Log Viewer", parent)
        self.setObjectName("nwbforge-log-viewer")
        self._editor = QPlainTextEdit(self)
        self._editor.setReadOnly(True)
        self.setWidget(self._editor)

    def set_entries(self, entries: tuple[UiLogEntry, ...]) -> None:
        self._editor.setPlainText("\n".join(format_log_entry(entry) for entry in entries))
        self._editor.moveCursor(QTextCursor.MoveOperation.End)

    @property
    def editor(self) -> QPlainTextEdit:
        return self._editor
