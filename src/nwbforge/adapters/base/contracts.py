"""Base contracts for source adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ExtractionResult, SourceReference


@dataclass(frozen=True, slots=True)
class AdapterCapabilities:
    supported_pathways: tuple[ConversionPathway, ...] = (ConversionPathway.SUPPORTED,)
    supports_multi_source_sessions: bool = False
    supports_hybrid_merge: bool = False
    emits_binary_payloads: bool = False


@runtime_checkable
class SourceAdapter(Protocol):
    adapter_id: str
    display_name: str
    version: str
    source_types: tuple[SourceType, ...]
    capabilities: AdapterCapabilities

    def can_handle(self, source: SourceReference) -> bool:
        """Return whether this adapter can inspect the supplied source."""

    def inspect(self, source: SourceReference) -> ExtractionResult:
        """Inspect a source and emit extracted fields for normalization."""
