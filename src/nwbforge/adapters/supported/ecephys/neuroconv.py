"""NeuroConv-backed adapters for supported ecephys routes."""

from __future__ import annotations

try:
    from neuroconv.datainterfaces import IntanRecordingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    IntanRecordingInterface = None

from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.adapters.neuroconv import (
    NeuroConvDirectConversionAdapter,
    NeuroConvSourceConfig,
    extracted_fields_from_mapping,
)
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ExtractedField, ReviewIssue, SourceReference


if IntanRecordingInterface is not None:

    class NeuroConvIntanAdapter(NeuroConvDirectConversionAdapter):
        """Inspect and convert Intan `.rhd` and `.rhs` sources through NeuroConv."""

        adapter_id = "neuroconv_intan"
        display_name = "NeuroConv Intan adapter"
        version = "0.1.0"
        interface_cls = IntanRecordingInterface
        record_type = "neuroconv_intan"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".rhd", ".rhs")

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
            ecephys_metadata = metadata.get("Ecephys", {})
            device_metadata = ecephys_metadata.get("Device") or [{}]
            electrode_groups = ecephys_metadata.get("ElectrodeGroup") or ()
            fields = extracted_fields_from_mapping(
                prefix="ecephys.intan",
                payload={
                    "source_format": source.location.suffix.lower().lstrip("."),
                    "device_name": device_metadata[0].get("name", "Intan"),
                    "electrode_group_count": len(electrode_groups),
                    "electrical_series_name": config.interface_kwargs.get("es_key", "ElectricalSeries"),
                    "ignore_integrity_checks": bool(config.interface_kwargs.get("ignore_integrity_checks", False)),
                    "has_session_start_time": "session_start_time" in metadata.get("NWBFile", {}),
                },
                source_id=source.source_id,
            )
            notes = (
                "Prepared NeuroConv Intan conversion into ecephys acquisition data.",
                "Intan route matching prefers distinctive .rhd and .rhs acquisition files rather than broader ecephys catch-all readers.",
            )
            return fields, [], notes
