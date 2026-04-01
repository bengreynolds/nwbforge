"""Qt bridges for forwarding model state changes onto the UI thread."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class StateBridge(QObject):
    """Forward arbitrary state payloads through a queued Qt signal."""

    state_changed = Signal(object)

    def publish(self, state: object) -> None:
        self.state_changed.emit(state)
