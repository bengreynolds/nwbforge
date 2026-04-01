"""UI-facing log sink abstractions for an in-app log viewer."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
import logging
from typing import Any, Callable, Protocol


def ui_log_utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True)
class UiLogEntry:
    """A log entry formatted for UI consumption."""

    level_name: str
    message: str
    logger_name: str
    context: dict[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=ui_log_utc_now)


UiLogListener = Callable[[tuple[UiLogEntry, ...]], None]


class UiLogSink(Protocol):
    """Protocol for recording UI-visible log entries."""

    def append(self, entry: UiLogEntry) -> None:
        """Store a UI-facing log entry."""

    def entries(self) -> tuple[UiLogEntry, ...]:
        """Return the current entry buffer."""


class InMemoryUiLogSink:
    """Keep a bounded in-memory log buffer for a future log viewer."""

    def __init__(self, *, capacity: int = 200) -> None:
        self._entries: deque[UiLogEntry] = deque(maxlen=capacity)
        self._listeners: list[UiLogListener] = []

    def append(self, entry: UiLogEntry) -> None:
        self._entries.append(entry)
        snapshot = self.entries()
        for listener in self._listeners:
            listener(snapshot)

    def entries(self) -> tuple[UiLogEntry, ...]:
        return tuple(self._entries)

    def subscribe(self, listener: UiLogListener, *, emit_initial: bool = True) -> None:
        self._listeners.append(listener)
        if emit_initial:
            listener(self.entries())


class UiLogHandler(logging.Handler):
    """Bridge standard logging records into a UI log sink."""

    def __init__(self, sink: UiLogSink, *, level: int = logging.NOTSET) -> None:
        super().__init__(level=level)
        self._sink = sink

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
        except Exception:
            message = record.getMessage()
        context = getattr(record, "nwbforge_context", {})
        if not isinstance(context, dict):
            context = {"raw_context": context}
        self._sink.append(
            UiLogEntry(
                level_name=record.levelname,
                message=message,
                logger_name=record.name,
                context=dict(context),
            )
        )
