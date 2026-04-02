"""Direct execution services for supported NeuroConv-backed routes."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path

from nwbforge.adapters.neuroconv import NeuroConvDirectConversionAdapter
from nwbforge.adapters.registry import AdapterRegistry
from nwbforge.app.logging import get_logger, log_event
from nwbforge.app.services.models import ConversionPreview
from nwbforge.domain.models import ProvenanceArtifact
from nwbforge.mapping import PyNWBAssemblyService


@dataclass(frozen=True, slots=True)
class DirectExecutionSelection:
    source_id: str
    adapter_id: str


class NeuroConvSupportedExecutionService:
    """Execute supported conversions by delegating the write path to NeuroConv."""

    _logger = get_logger(__name__)

    def __init__(
        self,
        registry: AdapterRegistry,
        *,
        base_assembly_service: PyNWBAssemblyService | None = None,
    ) -> None:
        self._registry = registry
        self._base_assembly_service = base_assembly_service or PyNWBAssemblyService()

    def can_execute(self, preview: ConversionPreview) -> bool:
        return self.select(preview) is not None

    def select(self, preview: ConversionPreview) -> DirectExecutionSelection | None:
        candidates: list[DirectExecutionSelection] = []
        for result in preview.extraction_results:
            adapter = self._registry.get(result.adapter_id)
            if isinstance(adapter, NeuroConvDirectConversionAdapter):
                candidates.append(
                    DirectExecutionSelection(
                        source_id=result.source_id,
                        adapter_id=result.adapter_id,
                    )
                )
        if len(candidates) != 1:
            return None
        return candidates[0]

    def write(
        self,
        preview: ConversionPreview,
        output_path: Path,
    ) -> tuple[ProvenanceArtifact, ...]:
        selection = self.select(preview)
        if selection is None:
            raise ValueError("Preview does not resolve to a single direct NeuroConv execution route.")

        adapter = self._registry.get(selection.adapter_id)
        if not isinstance(adapter, NeuroConvDirectConversionAdapter):
            raise TypeError(f"Adapter '{selection.adapter_id}' does not support direct NeuroConv execution.")

        source = next(source for source in preview.session.sources if source.source_id == selection.source_id)
        log_event(
            self._logger,
            logging.INFO,
            "Executing supported route through NeuroConv.",
            session_id=preview.session.session_id,
            source_id=selection.source_id,
            adapter_id=selection.adapter_id,
            output_path=str(output_path),
        )
        base_nwbfile = self._base_assembly_service.build_nwbfile(
            preview.session,
            preview.normalized_metadata,
            preview.mapping_plan,
            include_acquisition_streams=not adapter.writes_acquisition_streams,
            include_time_interval_tables=not adapter.writes_time_interval_tables,
        )
        artifacts = adapter.write_conversion(
            session=preview.session,
            source=source,
            output_path=str(output_path),
            nwbfile=base_nwbfile,
        )
        log_event(
            self._logger,
            logging.INFO,
            "Supported NeuroConv execution completed.",
            session_id=preview.session.session_id,
            source_id=selection.source_id,
            adapter_id=selection.adapter_id,
            artifact_count=len(artifacts),
        )
        return artifacts
