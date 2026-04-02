"""Qt application helpers for NWB Forge."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication
from nwbforge.ui.qt.styling import apply_nwbforge_application_style


def ensure_application() -> QApplication:
    """Return the active `QApplication`, creating one if needed."""

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        app.setApplicationName("NWB Forge")
    apply_nwbforge_application_style(app)
    return app
