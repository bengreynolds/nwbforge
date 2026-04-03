"""Shared base classes for combined NeuroConv workflow adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from pynwb import NWBFile

from nwbforge.adapters.neuroconv.base import NeuroConvDirectConversionAdapter
from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ConversionSession, ExtractionResult, ProvenanceArtifact, SourceReference


@dataclass(frozen=True, slots=True)
class WorkflowSourceRequirement:
    """Declarative requirement for one source role within a workflow."""

    role: str
    source_types: tuple[SourceType, ...]
    supported_suffixes: tuple[str, ...] = ()
    required_adapter_hints: tuple[str, ...] = ()
    required_roles: tuple[str, ...] = ()
    required_metadata: tuple[tuple[str, str], ...] = ()

    def matches(self, source: SourceReference) -> bool:
        if source.source_type not in self.source_types:
            return False
        if self.supported_suffixes and source.location.suffix.lower() not in self.supported_suffixes:
            return False
        if self.required_adapter_hints and source.adapter_hint not in self.required_adapter_hints:
            return False
        if self.required_roles and source.role not in self.required_roles:
            return False
        for key, expected_value in self.required_metadata:
            if str(source.metadata.get(key)) != expected_value:
                return False
        return True


@dataclass(frozen=True, slots=True)
class NeuroConvWorkflowRouteConfig:
    """Declarative route config for a combined NeuroConv workflow."""

    adapter_id: str
    display_name: str
    source_requirements: tuple[WorkflowSourceRequirement, ...]
    version: str = "0.1.0"


@dataclass(frozen=True, slots=True)
class WorkflowExecutionStep:
    """One matched direct-conversion step within a combined workflow."""

    role: str
    source: SourceReference
    adapter: NeuroConvDirectConversionAdapter


@dataclass(frozen=True, slots=True)
class WorkflowExecutionPlan:
    """Executable direct-conversion plan for a matched combined workflow."""

    workflow_adapter_id: str
    workflow_display_name: str
    steps: tuple[WorkflowExecutionStep, ...]


class NeuroConvWorkflowAdapter(ABC):
    """Base class for multi-source NeuroConv workflows."""

    capabilities = AdapterCapabilities(
        supported_pathways=(ConversionPathway.SUPPORTED,),
        supports_multi_source_sessions=True,
    )
    route_config: NeuroConvWorkflowRouteConfig

    def __init__(self) -> None:
        self.adapter_id = self.route_config.adapter_id
        self.display_name = self.route_config.display_name
        self.version = self.route_config.version

    def can_handle_sources(self, sources: tuple[SourceReference, ...]) -> bool:
        return self.match_sources(sources) is not None

    def inspect_sources(self, sources: tuple[SourceReference, ...]) -> tuple[ExtractionResult, ...]:
        matched_sources = self.match_sources(sources)
        if matched_sources is None:
            raise ValueError(f"Workflow adapter '{self.adapter_id}' could not match the supplied sources.")
        return self.inspect_matched_sources(matched_sources)

    def direct_execution_plan(
        self,
        sources: tuple[SourceReference, ...],
    ) -> WorkflowExecutionPlan | None:
        """Return a direct NeuroConv execution plan when the workflow can write in one pass."""

        del sources
        return None

    def write_conversion(
        self,
        *,
        session: ConversionSession,
        output_path: str,
        nwbfile: NWBFile,
    ) -> tuple[ProvenanceArtifact, ...]:
        """Run a combined direct NeuroConv conversion for a matched workflow."""

        del session, output_path, nwbfile
        raise TypeError(f"Workflow adapter '{self.adapter_id}' does not support direct NeuroConv execution.")

    def match_sources(
        self,
        sources: tuple[SourceReference, ...],
    ) -> dict[str, SourceReference] | None:
        remaining_sources = list(sources)
        matched_sources: dict[str, SourceReference] = {}

        for requirement in self.route_config.source_requirements:
            candidates = [source for source in remaining_sources if requirement.matches(source)]
            if len(candidates) != 1:
                return None
            selected_source = candidates[0]
            matched_sources[requirement.role] = selected_source
            remaining_sources.remove(selected_source)

        return matched_sources

    @abstractmethod
    def inspect_matched_sources(
        self,
        matched_sources: dict[str, SourceReference],
    ) -> tuple[ExtractionResult, ...]:
        """Inspect a matched multi-source workflow and emit extracted fields."""
