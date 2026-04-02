"""Models representing adapter output before normalization."""

from __future__ import annotations

from dataclasses import dataclass, field

from nwbforge.domain.models.common import ReviewIssue


@dataclass(frozen=True, slots=True)
class ExtractedField:
    key: str
    value: object
    source_id: str
    path: str | None = None
    notes: tuple[str, ...] = ()
    is_user_override: bool = False


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    source_id: str
    adapter_id: str
    record_type: str
    fields: dict[str, ExtractedField] = field(default_factory=dict)
    issues: tuple[ReviewIssue, ...] = ()
    notes: tuple[str, ...] = ()

    def field_keys(self) -> tuple[str, ...]:
        return tuple(self.fields.keys())
