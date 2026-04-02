"""UI-facing log sink abstractions for an in-app log viewer."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
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


class UiLogSubscriptionSink(UiLogSink, Protocol):
    """A UI log sink that can publish snapshot updates to listeners."""

    def subscribe(self, listener: UiLogListener, *, emit_initial: bool = True) -> None:
        """Subscribe to entry-buffer updates."""


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


class FileUiLogSink:
    """Append UI log entries to a JSON-lines file for later inspection."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def append(self, entry: UiLogEntry) -> None:
        payload = {
            "created_at": entry.created_at.isoformat(),
            "level_name": entry.level_name,
            "message": entry.message,
            "logger_name": entry.logger_name,
            "context": entry.context,
        }
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True))
            handle.write("\n")

    def entries(self) -> tuple[UiLogEntry, ...]:
        return ()


class CompositeUiLogSink:
    """Mirror log entries to one UI-visible sink and any number of secondary sinks."""

    def __init__(self, primary: UiLogSubscriptionSink, *secondary_sinks: UiLogSink) -> None:
        self._primary = primary
        self._secondary_sinks = secondary_sinks

    def append(self, entry: UiLogEntry) -> None:
        self._primary.append(entry)
        for sink in self._secondary_sinks:
            sink.append(entry)

    def entries(self) -> tuple[UiLogEntry, ...]:
        return self._primary.entries()

    def subscribe(self, listener: UiLogListener, *, emit_initial: bool = True) -> None:
        self._primary.subscribe(listener, emit_initial=emit_initial)


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
        created_at = datetime.fromtimestamp(record.created, tz=UTC)
        self._sink.append(
            UiLogEntry(
                level_name=record.levelname,
                message=message,
                logger_name=record.name,
                context=dict(context),
                created_at=created_at,
            )
        )
