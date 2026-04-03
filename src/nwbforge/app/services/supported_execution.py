"""Direct execution services for supported NeuroConv-backed routes."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path

from nwbforge.adapters.neuroconv import NeuroConvDirectConversionAdapter, NeuroConvWorkflowAdapter
from nwbforge.adapters.registry import AdapterRegistry
from nwbforge.app.logging import get_logger, log_event
from nwbforge.app.services.models import ConversionPreview
from nwbforge.domain.models import ProvenanceArtifact
from nwbforge.mapping import PyNWBAssemblyService


@dataclass(frozen=True, slots=True)
class DirectExecutionSelection:
    mode: str
    source_id: str | None = None
    adapter_id: str | None = None
    workflow_adapter_id: str | None = None


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
        workflow_matches = self._registry.matching_workflow_adapters(preview.session.sources)
        if len(workflow_matches) == 1:
            workflow_adapter = workflow_matches[0]
            if self._workflow_can_execute_direct(workflow_adapter, preview):
                return DirectExecutionSelection(
                    mode="workflow",
                    workflow_adapter_id=workflow_adapter.adapter_id,
                )
        if len(workflow_matches) > 1:
            return None

        candidates: list[DirectExecutionSelection] = []
        for result in preview.extraction_results:
            adapter = self._registry.get(result.adapter_id)
            if isinstance(adapter, NeuroConvDirectConversionAdapter):
                candidates.append(
                    DirectExecutionSelection(
                        mode="single",
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

        log_context = {
            "session_id": preview.session.session_id,
            "output_path": str(output_path),
            "mode": selection.mode,
        }
        if selection.mode == "workflow":
            workflow_adapter = self._registry.get_workflow(selection.workflow_adapter_id)
            if not isinstance(workflow_adapter, NeuroConvWorkflowAdapter):
                raise TypeError(
                    f"Workflow adapter '{selection.workflow_adapter_id}' does not support direct NeuroConv execution."
                )
            log_event(
                self._logger,
                logging.INFO,
                "Executing supported combined workflow through NeuroConv.",
                workflow_adapter_id=selection.workflow_adapter_id,
                **log_context,
            )
        else:
            adapter = self._registry.get(selection.adapter_id)
            if not isinstance(adapter, NeuroConvDirectConversionAdapter):
                raise TypeError(f"Adapter '{selection.adapter_id}' does not support direct NeuroConv execution.")
            source = next(source for source in preview.session.sources if source.source_id == selection.source_id)
            log_event(
                self._logger,
                logging.INFO,
                "Executing supported route through NeuroConv.",
                source_id=selection.source_id,
                adapter_id=selection.adapter_id,
                **log_context,
            )

        writes_acquisition_streams, writes_time_interval_tables = self._written_content_flags(preview, selection)
        base_nwbfile = self._base_assembly_service.build_nwbfile(
            preview.session,
            preview.normalized_metadata,
            preview.mapping_plan,
            include_acquisition_streams=not writes_acquisition_streams,
            include_time_interval_tables=not writes_time_interval_tables,
        )
        if selection.mode == "workflow":
            workflow_adapter = self._registry.get_workflow(selection.workflow_adapter_id)
            artifacts = workflow_adapter.write_conversion(
                session=preview.session,
                output_path=str(output_path),
                nwbfile=base_nwbfile,
            )
            log_event(
                self._logger,
                logging.INFO,
                "Supported combined workflow execution completed.",
                session_id=preview.session.session_id,
                workflow_adapter_id=selection.workflow_adapter_id,
                artifact_count=len(artifacts),
            )
        else:
            adapter = self._registry.get(selection.adapter_id)
            source = next(source for source in preview.session.sources if source.source_id == selection.source_id)
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

    def _workflow_can_execute_direct(
        self,
        workflow_adapter: object,
        preview: ConversionPreview,
    ) -> bool:
        if not isinstance(workflow_adapter, NeuroConvWorkflowAdapter):
            return False
        return workflow_adapter.direct_execution_plan(preview.session.sources) is not None

    def _written_content_flags(
        self,
        preview: ConversionPreview,
        selection: DirectExecutionSelection,
    ) -> tuple[bool, bool]:
        if selection.mode == "workflow":
            workflow_adapter = self._registry.get_workflow(selection.workflow_adapter_id)
            plan = workflow_adapter.direct_execution_plan(preview.session.sources)
            if plan is None:
                return False, False
            writes_acquisition_streams = any(step.adapter.writes_acquisition_streams for step in plan.steps)
            writes_time_interval_tables = any(step.adapter.writes_time_interval_tables for step in plan.steps)
            return writes_acquisition_streams, writes_time_interval_tables

        adapter = self._registry.get(selection.adapter_id)
        if not isinstance(adapter, NeuroConvDirectConversionAdapter):
            return False, False
        return adapter.writes_acquisition_streams, adapter.writes_time_interval_tables
