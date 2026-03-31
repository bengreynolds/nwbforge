"""Session and input models for orchestrating conversion work."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path

from nwbforge.domain.enums import ConversionPathway, SessionStatus, SourceType


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True)
class SourceReference:
    """A raw input added to a conversion session."""

    source_id: str
    location: Path
    source_type: SourceType
    label: str
    role: str = "primary"
    media_type: str | None = None
    adapter_hint: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    sidecar_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ConversionSession:
    """The top-level unit of workflow state for a conversion attempt."""

    session_id: str
    pathway: ConversionPathway
    status: SessionStatus = SessionStatus.DRAFT
    sources: tuple[SourceReference, ...] = ()
    title: str | None = None
    lab_profile: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    notes: tuple[str, ...] = ()

    def add_source(self, source: SourceReference, updated_at: datetime | None = None) -> "ConversionSession":
        return replace(
            self,
            sources=self.sources + (source,),
            status=SessionStatus.SOURCES_ADDED,
            updated_at=updated_at or utc_now(),
        )

    def transition(self, status: SessionStatus, updated_at: datetime | None = None) -> "ConversionSession":
        return replace(self, status=status, updated_at=updated_at or utc_now())

    @property
    def source_ids(self) -> tuple[str, ...]:
        return tuple(source.source_id for source in self.sources)
