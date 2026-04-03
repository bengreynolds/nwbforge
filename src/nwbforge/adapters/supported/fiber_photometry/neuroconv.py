"""NeuroConv-backed adapters for supported fiber photometry routes."""

from __future__ import annotations

from pathlib import Path

try:
    from neuroconv.datainterfaces import TDTFiberPhotometryInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    TDTFiberPhotometryInterface = None

from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.adapters.neuroconv import (
    NeuroConvDirectConversionAdapter,
    NeuroConvSourceConfig,
    extracted_fields_from_mapping,
)
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ExtractedField, ReviewIssue, SourceReference


def _looks_like_tdt_block(location: Path) -> bool:
    if not location.is_dir():
        return False
    suffixes = {path.suffix.lower().lstrip(".") for path in location.iterdir() if path.is_file()}
    return bool({"tbk", "tdx", "tev", "tin", "tsq"} & suffixes)


if TDTFiberPhotometryInterface is not None:

    class NeuroConvTdtFiberPhotometryAdapter(NeuroConvDirectConversionAdapter):
        """Inspect and convert TDT fiber photometry block folders through NeuroConv."""

        adapter_id = "neuroconv_tdt_fiber_photometry"
        display_name = "NeuroConv TDT fiber photometry adapter"
        version = "0.1.0"
        interface_cls = TDTFiberPhotometryInterface
        source_path_kwarg = "folder_path"
        record_type = "neuroconv_tdt_fiber_photometry"
        source_types = (SourceType.DIRECTORY,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return source.adapter_hint == self.adapter_id and _looks_like_tdt_block(source.location)

        def build_interface(self, source: SourceReference, config: NeuroConvSourceConfig):
            interface_kwargs = {"folder_path": source.location}
            interface_kwargs.update(config.interface_kwargs)
            interface_kwargs.setdefault("verbose", False)
            return self.interface_cls(**interface_kwargs)

        def extract(
            self,
            *,
            source: SourceReference,
            interface,
            config: NeuroConvSourceConfig,
        ) -> tuple[dict[str, ExtractedField], list[ReviewIssue], tuple[str, ...]]:
            del config
            metadata = interface.get_metadata()
            fiber_metadata = metadata.get("Ophys", {}).get("FiberPhotometry", {})
            table_metadata = fiber_metadata.get("FiberPhotometryTable", {})
            fields = extracted_fields_from_mapping(
                prefix="ophys.tdt_fiber_photometry",
                payload={
                    "source_format": "tdt_fiber_photometry_folder",
                    "has_session_start_time": "session_start_time" in metadata.get("NWBFile", {}),
                    "fiber_photometry_key_count": len(fiber_metadata),
                    "has_fiber_photometry_table": bool(table_metadata),
                    "fiber_photometry_row_count": len(tuple(table_metadata.get("rows", ()))),
                },
                source_id=source.source_id,
            )
            notes = (
                "Prepared NeuroConv TDT fiber photometry conversion into NWB fiber photometry data.",
                "TDT fiber photometry is currently hint-driven because TDT block folders can also represent ecephys recording sessions.",
            )
            return fields, [], notes
