from pathlib import Path

from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.adapters.neuroconv import (
    NeuroConvWorkflowAdapter,
    NeuroConvWorkflowRouteConfig,
    WorkflowSourceRequirement,
)
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ExtractionResult, SourceReference


class MinimalCombinedWorkflowAdapter(NeuroConvWorkflowAdapter):
    route_config = NeuroConvWorkflowRouteConfig(
        adapter_id="minimal_combined_workflow",
        display_name="Minimal combined workflow",
        source_requirements=(
            WorkflowSourceRequirement(
                role="recording",
                source_types=(SourceType.FILE,),
                supported_suffixes=(".bin",),
                required_metadata=(("workflow.role", "recording"),),
            ),
            WorkflowSourceRequirement(
                role="sorting",
                source_types=(SourceType.DIRECTORY,),
                required_metadata=(("workflow.role", "sorting"),),
            ),
        ),
    )
    capabilities = AdapterCapabilities(
        supported_pathways=(ConversionPathway.SUPPORTED,),
        supports_multi_source_sessions=True,
    )

    def inspect_matched_sources(
        self,
        matched_sources: dict[str, SourceReference],
    ) -> tuple[ExtractionResult, ...]:
        return tuple(
            ExtractionResult(
                source_id=source.source_id,
                adapter_id=self.adapter_id,
                record_type=f"workflow_{role}",
                fields={},
                issues=(),
                notes=(f"Matched workflow role '{role}'.",),
            )
            for role, source in matched_sources.items()
        )


def test_neuroconv_workflow_framework_matches_required_sources() -> None:
    adapter = MinimalCombinedWorkflowAdapter()
    sources = (
        SourceReference(
            source_id="recording-1",
            location=Path("data/recording.bin"),
            source_type=SourceType.FILE,
            label="recording",
            metadata={"workflow.role": "recording"},
        ),
        SourceReference(
            source_id="sorting-1",
            location=Path("data/sorting"),
            source_type=SourceType.DIRECTORY,
            label="sorting",
            metadata={"workflow.role": "sorting"},
        ),
    )

    assert adapter.can_handle_sources(sources) is True

    results = adapter.inspect_sources(sources)

    assert tuple(result.record_type for result in results) == ("workflow_recording", "workflow_sorting")


def test_neuroconv_workflow_framework_rejects_ambiguous_source_sets() -> None:
    adapter = MinimalCombinedWorkflowAdapter()
    sources = (
        SourceReference(
            source_id="recording-1",
            location=Path("data/recording-1.bin"),
            source_type=SourceType.FILE,
            label="recording 1",
            metadata={"workflow.role": "recording"},
        ),
        SourceReference(
            source_id="recording-2",
            location=Path("data/recording-2.bin"),
            source_type=SourceType.FILE,
            label="recording 2",
            metadata={"workflow.role": "recording"},
        ),
        SourceReference(
            source_id="sorting-1",
            location=Path("data/sorting"),
            source_type=SourceType.DIRECTORY,
            label="sorting",
            metadata={"workflow.role": "sorting"},
        ),
    )

    assert adapter.can_handle_sources(sources) is False
