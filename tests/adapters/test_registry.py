from dataclasses import dataclass
from pathlib import Path

import pytest

from nwbforge.adapters import AdapterCapabilities, AdapterRegistry
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ExtractedField, ExtractionResult, SourceReference


@dataclass(frozen=True)
class DummyAdapter:
    adapter_id: str
    display_name: str = "Dummy adapter"
    version: str = "0.1.0"
    source_types: tuple[SourceType, ...] = (SourceType.DIRECTORY,)
    capabilities: AdapterCapabilities = AdapterCapabilities(
        supported_pathways=(ConversionPathway.SUPPORTED,)
    )

    def can_handle(self, source: SourceReference) -> bool:
        return source.source_type in self.source_types and self.adapter_id in source.label.lower()

    def inspect(self, source: SourceReference) -> ExtractionResult:
        return ExtractionResult(
            source_id=source.source_id,
            adapter_id=self.adapter_id,
            record_type="session",
            fields={
                "session_id": ExtractedField(
                    key="session_id",
                    value=source.source_id,
                    source_id=source.source_id,
                )
            },
        )


def test_registry_returns_matching_adapters_in_sorted_order() -> None:
    registry = AdapterRegistry()
    registry.register(DummyAdapter(adapter_id="zeta"))
    registry.register(DummyAdapter(adapter_id="alpha"))
    source = SourceReference(
        source_id="session-01",
        location=Path("data/alpha-session"),
        source_type=SourceType.DIRECTORY,
        label="alpha adapter session",
    )

    matches = registry.matching_adapters(source)

    assert tuple(adapter.adapter_id for adapter in matches) == ("alpha",)
    assert registry.registered_ids() == ("alpha", "zeta")


def test_registry_rejects_duplicate_adapter_ids() -> None:
    registry = AdapterRegistry()
    registry.register(DummyAdapter(adapter_id="alpha"))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(DummyAdapter(adapter_id="alpha"))


def test_extraction_result_exposes_field_keys() -> None:
    result = DummyAdapter(adapter_id="alpha").inspect(
        SourceReference(
            source_id="session-01",
            location=Path("data/session"),
            source_type=SourceType.DIRECTORY,
            label="alpha adapter session",
        )
    )

    assert result.field_keys() == ("session_id",)
