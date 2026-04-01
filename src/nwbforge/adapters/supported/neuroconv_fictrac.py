"""NeuroConv-backed adapters for FicTrac behavior sources."""

from __future__ import annotations

from pathlib import Path

from neuroconv.datainterfaces import FicTracDataInterface

from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.adapters.neuroconv import (
    NeuroConvDirectConversionAdapter,
    NeuroConvSourceConfig,
    extracted_fields_from_mapping,
)
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ExtractedField, ReviewIssue, SourceReference


class NeuroConvFicTracAdapter(NeuroConvDirectConversionAdapter):
    """Inspect and convert FicTrac `.dat` sources through NeuroConv."""

    adapter_id = "neuroconv_fictrac"
    display_name = "NeuroConv FicTrac adapter"
    version = "0.1.0"
    interface_cls = FicTracDataInterface
    record_type = "neuroconv_fictrac"
    source_types = (SourceType.FILE,)
    capabilities = AdapterCapabilities(
        supported_pathways=(ConversionPathway.SUPPORTED,),
        supports_multi_source_sessions=True,
    )
    supported_suffixes = (".dat",)

    def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
        del config
        return source.location.suffix.lower() in self.supported_suffixes

    def extract(
        self,
        *,
        source: SourceReference,
        interface,
        config: NeuroConvSourceConfig,
    ) -> tuple[dict[str, ExtractedField], list[ReviewIssue], tuple[str, ...]]:
        metadata = interface.get_metadata()
        behavior_metadata = metadata.get("Behavior", {}).get("FicTrac", {})
        fields = extracted_fields_from_mapping(
            prefix="behavior.fictrac",
            payload={
                "source_format": "fictrac_dat",
                "spatial_series_count": len(getattr(interface, "column_to_nwb_mapping", {})),
                "has_session_start_time": "session_start_time" in metadata.get("NWBFile", {}),
                "container_name": behavior_metadata.get("name", "FicTrac"),
                "has_config": str(config.interface_kwargs.get("configuration_file_path", "")) != "",
                "radius": config.interface_kwargs.get("radius"),
            },
            source_id=source.source_id,
        )
        notes = ("Prepared NeuroConv FicTrac conversion into behavior processing data.",)
        return fields, [], notes

    def build_interface(self, source: SourceReference, config: NeuroConvSourceConfig):
        interface_kwargs = {self.source_path_kwarg: source.location}
        interface_kwargs.update(config.interface_kwargs)
        if "configuration_file_path" not in interface_kwargs:
            candidate = source.location.parent / "config.txt"
            if candidate.is_file():
                interface_kwargs["configuration_file_path"] = candidate
        interface_kwargs.setdefault("verbose", False)
        return self.interface_cls(**interface_kwargs)
