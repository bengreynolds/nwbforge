"""Qt application helpers for NWB Forge."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication


def ensure_application() -> QApplication:
    """Return the active `QApplication`, creating one if needed."""

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        app.setApplicationName("NWB Forge")
    return app
