"""Concrete source-inspection services."""

from __future__ import annotations

from nwbforge.adapters import AdapterRegistry
from nwbforge.app.services.errors import AdapterSelectionError, SourceNotFoundError
from nwbforge.domain.contracts import SourceInspectionService
from nwbforge.domain.models import ConversionSession, ExtractionResult, SourceReference


class RegistrySourceInspectionService(SourceInspectionService):
    """Resolve an adapter from the registry and inspect a session source."""

    def __init__(self, registry: AdapterRegistry) -> None:
        self._registry = registry

    def inspect(self, session: ConversionSession, source_id: str) -> ExtractionResult:
        source = self._find_source(session, source_id)
        adapter = self._select_adapter(source)
        return adapter.inspect(source)

    @staticmethod
    def _find_source(session: ConversionSession, source_id: str) -> SourceReference:
        for source in session.sources:
            if source.source_id == source_id:
                return source
        raise SourceNotFoundError(f"Source '{source_id}' is not attached to session '{session.session_id}'.")

    def _select_adapter(self, source: SourceReference):
        if source.adapter_hint is not None:
            adapter = self._registry.get(source.adapter_hint)
            if not adapter.can_handle(source):
                raise AdapterSelectionError(
                    f"Adapter hint '{source.adapter_hint}' cannot handle source '{source.source_id}'."
                )
            return adapter

        matches = self._registry.matching_adapters(source)
        if not matches:
            raise AdapterSelectionError(f"No adapter matched source '{source.source_id}'.")
        if len(matches) > 1:
            adapter_ids = ", ".join(adapter.adapter_id for adapter in matches)
            raise AdapterSelectionError(
                f"Multiple adapters matched source '{source.source_id}': {adapter_ids}."
            )
        return matches[0]
