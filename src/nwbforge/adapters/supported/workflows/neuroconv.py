"""Combined supported workflow adapters built over existing NeuroConv routes."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from nwbforge.adapters.base import AdapterCapabilities, SourceAdapter
from nwbforge.adapters.neuroconv import (
    NeuroConvDirectConversionAdapter,
    NeuroConvWorkflowAdapter,
    NeuroConvWorkflowRouteConfig,
    WorkflowExecutionPlan,
    WorkflowExecutionStep,
    WorkflowSourceRequirement,
)
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ConversionSession, ExtractionResult, ProvenanceArtifact, SourceReference


class _DelegatingCombinedWorkflowAdapter(NeuroConvWorkflowAdapter):
    """A lightweight workflow adapter that delegates inspection to matched route adapters."""

    capabilities = AdapterCapabilities(
        supported_pathways=(ConversionPathway.SUPPORTED,),
        supports_multi_source_sessions=True,
    )

    def __init__(self, delegates: dict[str, SourceAdapter]) -> None:
        super().__init__()
        self._delegates = delegates

    def inspect_matched_sources(
        self,
        matched_sources: dict[str, SourceReference],
    ) -> tuple[ExtractionResult, ...]:
        results: list[ExtractionResult] = []
        for role, source in matched_sources.items():
            adapter = self._delegates[role]
            result = adapter.inspect(source)
            results.append(
                replace(
                    result,
                    notes=result.notes
                    + (
                        f"Matched combined workflow '{self.adapter_id}' as role '{role}'.",
                    ),
                )
            )
        return tuple(results)

    def direct_execution_plan(
        self,
        sources: tuple[SourceReference, ...],
    ) -> WorkflowExecutionPlan | None:
        matched_sources = self.match_sources(sources)
        if matched_sources is None:
            return None

        steps: list[WorkflowExecutionStep] = []
        for role, source in matched_sources.items():
            adapter = self._delegates[role]
            if not isinstance(adapter, NeuroConvDirectConversionAdapter):
                return None
            steps.append(WorkflowExecutionStep(role=role, source=source, adapter=adapter))
        return WorkflowExecutionPlan(
            workflow_adapter_id=self.adapter_id,
            workflow_display_name=self.display_name,
            steps=tuple(steps),
        )

    def write_conversion(
        self,
        *,
        session: ConversionSession,
        output_path: str,
        nwbfile,
    ) -> tuple[ProvenanceArtifact, ...]:
        plan = self.direct_execution_plan(session.sources)
        if plan is None:
            raise ValueError(f"Workflow adapter '{self.adapter_id}' could not build a direct execution plan.")

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        for step in plan.steps:
            step.adapter.write_conversion(
                session=session,
                source=step.source,
                output_path=str(output_file),
                nwbfile=nwbfile,
            )
        return (
            ProvenanceArtifact(
                artifact_type="nwb",
                location=output_file,
                description=(
                    f"NWB file written through combined workflow '{self.adapter_id}' "
                    f"with {len(plan.steps)} direct NeuroConv steps."
                ),
            ),
        )


class NeuroConvSpikeGLXPhyWorkflowAdapter(_DelegatingCombinedWorkflowAdapter):
    route_config = NeuroConvWorkflowRouteConfig(
        adapter_id="neuroconv_spikeglx_phy_workflow",
        display_name="SpikeGLX + Phy Workflow",
        source_requirements=(
            WorkflowSourceRequirement(
                role="recording",
                source_types=(SourceType.DIRECTORY, SourceType.FILE),
                required_adapter_hints=("neuroconv_spikeglx",),
                required_roles=("primary",),
            ),
            WorkflowSourceRequirement(
                role="sorting",
                source_types=(SourceType.DIRECTORY,),
                required_adapter_hints=("neuroconv_phy_sorting",),
            ),
        ),
    )


class NeuroConvTiffSuite2pWorkflowAdapter(_DelegatingCombinedWorkflowAdapter):
    route_config = NeuroConvWorkflowRouteConfig(
        adapter_id="neuroconv_tiff_suite2p_workflow",
        display_name="TIFF + Suite2p Workflow",
        source_requirements=(
            WorkflowSourceRequirement(
                role="imaging",
                source_types=(SourceType.FILE, SourceType.DIRECTORY),
                required_adapter_hints=("neuroconv_tiff_imaging",),
                required_roles=("primary",),
            ),
            WorkflowSourceRequirement(
                role="segmentation",
                source_types=(SourceType.DIRECTORY,),
                required_adapter_hints=("neuroconv_suite2p_segmentation",),
            ),
        ),
    )


class NeuroConvOpenEphysDeepLabCutWorkflowAdapter(_DelegatingCombinedWorkflowAdapter):
    route_config = NeuroConvWorkflowRouteConfig(
        adapter_id="neuroconv_openephys_deeplabcut_workflow",
        display_name="OpenEphys Binary + DeepLabCut Workflow",
        source_requirements=(
            WorkflowSourceRequirement(
                role="recording",
                source_types=(SourceType.DIRECTORY,),
                required_adapter_hints=("neuroconv_openephys_binary",),
                required_roles=("primary",),
            ),
            WorkflowSourceRequirement(
                role="behavior",
                source_types=(SourceType.FILE, SourceType.DIRECTORY),
                required_adapter_hints=("neuroconv_deeplabcut",),
            ),
        ),
    )
