"""Runtime-facing models for background execution and UI status."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Callable


def runtime_utc_now() -> datetime:
    return datetime.now(tz=UTC)


class PipelineStage(str, Enum):
    """High-level stages the UI can surface during conversion work."""

    QUEUED = "queued"
    INSPECTING = "inspecting"
    NORMALIZING = "normalizing"
    MAPPING = "mapping"
    REVIEW = "review"
    READY_TO_WRITE = "ready_to_write"
    WRITING = "writing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class PipelineProgressEvent:
    """A stage/progress update emitted from real pipeline steps."""

    session_id: str
    stage: PipelineStage
    percent_complete: int
    message: str
    source_id: str | None = None
    created_at: datetime = field(default_factory=runtime_utc_now)


class PipelineRuntimeError(RuntimeError):
    """A user-facing runtime error enriched with pipeline context."""

    def __init__(
        self,
        *,
        stage: PipelineStage,
        user_message: str,
        session_id: str | None = None,
        detail: str | None = None,
        source_id: str | None = None,
    ) -> None:
        super().__init__(user_message)
        self.stage = stage
        self.user_message = user_message
        self.session_id = session_id
        self.detail = detail
        self.source_id = source_id


ProgressCallback = Callable[[PipelineProgressEvent], None]
