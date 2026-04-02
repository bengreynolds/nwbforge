"""Registry for source adapter discovery."""

from __future__ import annotations

from dataclasses import dataclass, field

from nwbforge.adapters.base import SourceAdapter
from nwbforge.domain.models import SourceReference


@dataclass(slots=True)
class AdapterRegistry:
    _adapters: dict[str, SourceAdapter] = field(default_factory=dict)

    def register(self, adapter: SourceAdapter) -> None:
        if adapter.adapter_id in self._adapters:
            raise ValueError(f"Adapter '{adapter.adapter_id}' is already registered.")
        self._adapters[adapter.adapter_id] = adapter

    def get(self, adapter_id: str) -> SourceAdapter:
        try:
            return self._adapters[adapter_id]
        except KeyError as exc:
            raise KeyError(f"Unknown adapter '{adapter_id}'.") from exc

    def matching_adapters(self, source: SourceReference) -> tuple[SourceAdapter, ...]:
        matches = [adapter for adapter in self._adapters.values() if adapter.can_handle(source)]
        return tuple(sorted(matches, key=lambda adapter: adapter.adapter_id))

    def registered_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters.keys()))
