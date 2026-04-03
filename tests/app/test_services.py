from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path

import pytest

from nwbforge.adapters import AdapterCapabilities, AdapterRegistry
from nwbforge.adapters.neuroconv import NeuroConvWorkflowAdapter, NeuroConvWorkflowRouteConfig, WorkflowSourceRequirement
from nwbforge.app.services import (
    AdapterSelectionError,
    RegistrySourceInspectionService,
    SessionProvenanceService,
    SourceNotFoundError,
)
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import (
    ConversionSession,
    ExtractedField,
    ExtractionResult,
    ProvenanceArtifact,
    SourceReference,
)


@dataclass(frozen=True)
class DummyAdapter:
    adapter_id: str
    display_name: str = "Dummy"
    version: str = "0.1.0"
    source_types: tuple[SourceType, ...] = (SourceType.DIRECTORY,)
    capabilities: AdapterCapabilities = AdapterCapabilities()

    def can_handle(self, source: SourceReference) -> bool:
        return source.source_type in self.source_types and self.adapter_id in source.label.lower()

    def inspect(self, source: SourceReference) -> ExtractionResult:
        return ExtractionResult(
            source_id=source.source_id,
            adapter_id=self.adapter_id,
            record_type="session",
            fields={
                "label": ExtractedField(
                    key="label",
                    value=source.label,
                    source_id=source.source_id,
                )
            },
        )


class DummyWorkflowAdapter(NeuroConvWorkflowAdapter):
    route_config = NeuroConvWorkflowRouteConfig(
        adapter_id="dummy_workflow",
        display_name="Dummy Workflow",
        source_requirements=(
            WorkflowSourceRequirement(
                role="recording",
                source_types=(SourceType.DIRECTORY,),
                required_adapter_hints=("alpha",),
            ),
            WorkflowSourceRequirement(
                role="sorting",
                source_types=(SourceType.DIRECTORY,),
                required_adapter_hints=("recording",),
            ),
        ),
    )

    def __init__(self) -> None:
        super().__init__()

    def inspect_matched_sources(
        self,
        matched_sources: dict[str, SourceReference],
    ) -> tuple[ExtractionResult, ...]:
        return tuple(
            ExtractionResult(
                source_id=source.source_id,
                adapter_id=self.adapter_id,
                record_type=f"workflow_{role}",
                notes=(f"Matched role {role}.",),
            )
            for role, source in matched_sources.items()
        )


def make_session(*sources: SourceReference) -> ConversionSession:
    return ConversionSession(
        session_id="sess-001",
        pathway=ConversionPathway.SUPPORTED,
        sources=tuple(sources),
    )


def test_registry_source_inspection_uses_adapter_hint_when_present() -> None:
    registry = AdapterRegistry()
    registry.register(DummyAdapter(adapter_id="alpha"))
    session = make_session(
        SourceReference(
            source_id="source-1",
            location=Path("data/source-1"),
            source_type=SourceType.DIRECTORY,
            label="alpha hinted session",
            adapter_hint="alpha",
        )
    )

    result = RegistrySourceInspectionService(registry).inspect(session, "source-1")

    assert result.adapter_id == "alpha"


def test_registry_source_inspection_uses_single_matching_adapter_without_hint() -> None:
    registry = AdapterRegistry()
    registry.register(DummyAdapter(adapter_id="alpha"))
    session = make_session(
        SourceReference(
            source_id="source-1",
            location=Path("data/source-1"),
            source_type=SourceType.DIRECTORY,
            label="alpha recording session",
        )
    )

    result = RegistrySourceInspectionService(registry).inspect(session, "source-1")

    assert result.field_keys() == ("label",)


def test_registry_source_inspection_raises_for_missing_source() -> None:
    service = RegistrySourceInspectionService(AdapterRegistry())

    with pytest.raises(SourceNotFoundError, match="missing"):
        service.inspect(make_session(), "missing")


def test_registry_source_inspection_raises_for_ambiguous_match() -> None:
    registry = AdapterRegistry()
    registry.register(DummyAdapter(adapter_id="alpha"))
    registry.register(DummyAdapter(adapter_id="recording"))
    session = make_session(
        SourceReference(
            source_id="source-1",
            location=Path("data/source-1"),
            source_type=SourceType.DIRECTORY,
            label="alpha recording session",
        )
    )

    with pytest.raises(AdapterSelectionError, match="Multiple adapters matched"):
        RegistrySourceInspectionService(registry).inspect(session, "source-1")


def test_registry_source_inspection_applies_source_specific_metadata_overrides() -> None:
    registry = AdapterRegistry()
    registry.register(DummyAdapter(adapter_id="alpha"))
    session = ConversionSession(
        session_id="sess-001",
        pathway=ConversionPathway.SUPPORTED,
        sources=(
            SourceReference(
                source_id="source-1",
                location=Path("data/source-1"),
                source_type=SourceType.DIRECTORY,
                label="alpha recording session",
            ),
        ),
        source_metadata_overrides={
            "source-1": {
                "subject.subject_id": "override-mouse-01",
            }
        },
    )

    result = RegistrySourceInspectionService(registry).inspect(session, "source-1")

    assert result.fields["subject.subject_id"].value == "override-mouse-01"
    assert result.fields["subject.subject_id"].is_user_override is True
    assert "Applied from source-specific metadata override." in result.fields["subject.subject_id"].notes


def test_registry_source_inspection_can_use_workflow_adapter_for_whole_session() -> None:
    registry = AdapterRegistry()
    registry.register(DummyAdapter(adapter_id="alpha"))
    registry.register(DummyAdapter(adapter_id="recording"))
    registry.register_workflow(DummyWorkflowAdapter())
    session = make_session(
        SourceReference(
            source_id="source-1",
            location=Path("data/source-1"),
            source_type=SourceType.DIRECTORY,
            label="alpha recording session",
            adapter_hint="alpha",
        ),
        SourceReference(
            source_id="source-2",
            location=Path("data/source-2"),
            source_type=SourceType.DIRECTORY,
            label="recording session",
            adapter_hint="recording",
        ),
    )

    results = RegistrySourceInspectionService(registry).inspect_session(session)

    assert results is not None
    assert tuple(result.record_type for result in results) == ("workflow_recording", "workflow_sorting")


def test_session_provenance_service_uses_session_metadata() -> None:
    session = make_session(
        SourceReference(
            source_id="source-1",
            location=Path("data/source-1"),
            source_type=SourceType.DIRECTORY,
            label="alpha recording session",
            adapter_hint="alpha",
        ),
        SourceReference(
            source_id="source-2",
            location=Path("data/source-2"),
            source_type=SourceType.DIRECTORY,
            label="alpha recording session",
            adapter_hint="alpha",
        ),
    )
    session = ConversionSession(
        session_id=session.session_id,
        pathway=session.pathway,
        sources=session.sources,
        lab_profile="default-lab",
        notes=("reviewed locally",),
    )
    input_artifact = ProvenanceArtifact(
        artifact_type="input",
        location=Path("data/source-1/file.bin"),
    )
    generated_artifact = ProvenanceArtifact(
        artifact_type="report",
        location=Path("artifacts/session/report.json"),
    )

    record = SessionProvenanceService().build_record(
        session,
        input_artifacts=(input_artifact,),
        generated_artifacts=(generated_artifact,),
    )

    assert record.adapter_ids == ("alpha",)
    assert record.lab_profile == "default-lab"
    assert record.notes == ("reviewed locally",)
