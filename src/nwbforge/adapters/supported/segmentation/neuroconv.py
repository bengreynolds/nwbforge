"""NeuroConv-backed adapters for supported segmentation routes."""

from __future__ import annotations

from pathlib import Path

try:
    from neuroconv.datainterfaces import CaimanSegmentationInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    CaimanSegmentationInterface = None

try:
    from neuroconv.datainterfaces import CnmfeSegmentationInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    CnmfeSegmentationInterface = None

try:
    from neuroconv.datainterfaces import ExtractSegmentationInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    ExtractSegmentationInterface = None

try:
    from neuroconv.datainterfaces import InscopixSegmentationInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    InscopixSegmentationInterface = None

try:
    from neuroconv.datainterfaces import Suite2pSegmentationInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    Suite2pSegmentationInterface = None

from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.adapters.neuroconv import (
    NeuroConvDirectConversionAdapter,
    NeuroConvSourceConfig,
    extracted_fields_from_mapping,
)
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ExtractedField, ReviewIssue, SourceReference


def _contains_any_token(location: Path, tokens: tuple[str, ...]) -> bool:
    lowered_name = location.name.lower()
    return any(token in lowered_name for token in tokens)


def _ophys_metadata_payload(metadata: dict[str, object], *, default_name: str) -> dict[str, object]:
    ophys_metadata = metadata.get("Ophys", {})
    device_metadata = ophys_metadata.get("Device") or [{}]
    return {
        "device_name": device_metadata[0].get("name", default_name),
        "ophys_metadata_key_count": len(ophys_metadata),
        "has_image_segmentation": "ImageSegmentation" in ophys_metadata,
        "has_fluorescence": "Fluorescence" in ophys_metadata,
        "has_session_start_time": "session_start_time" in metadata.get("NWBFile", {}),
    }


def _looks_like_suite2p_folder(location: Path) -> bool:
    if not location.is_dir():
        return False
    required_files = ("ops.npy", "stat.npy", "iscell.npy")
    return all((location / filename).is_file() for filename in required_files)


class _NeuroConvSegmentationAdapter(NeuroConvDirectConversionAdapter):
    """Shared extraction helpers for NeuroConv-backed segmentation routes."""

    extraction_prefix = "ophys.segmentation"
    default_device_name = "SegmentationDevice"
    source_format = "segmentation"

    def extract(
        self,
        *,
        source: SourceReference,
        interface,
        config: NeuroConvSourceConfig,
    ) -> tuple[dict[str, ExtractedField], list[ReviewIssue], tuple[str, ...]]:
        metadata = interface.get_metadata()
        payload = {
            "source_format": self.source_format,
            **_ophys_metadata_payload(metadata, default_name=self.default_device_name),
            **self.additional_payload(source=source, metadata=metadata, config=config),
        }
        fields = extracted_fields_from_mapping(
            prefix=self.extraction_prefix,
            payload=payload,
            source_id=source.source_id,
        )
        return fields, [], self.extraction_notes()

    def additional_payload(
        self,
        *,
        source: SourceReference,
        metadata: dict[str, object],
        config: NeuroConvSourceConfig,
    ) -> dict[str, object]:
        del source, metadata, config
        return {}

    def extraction_notes(self) -> tuple[str, ...]:
        return ("Prepared NeuroConv segmentation conversion into NWB ophys segmentation data.",)


if CaimanSegmentationInterface is not None:

    class NeuroConvCaimanSegmentationAdapter(_NeuroConvSegmentationAdapter):
        """Inspect and convert Caiman segmentation outputs through NeuroConv."""

        adapter_id = "neuroconv_caiman_segmentation"
        display_name = "NeuroConv Caiman segmentation adapter"
        version = "0.1.0"
        interface_cls = CaimanSegmentationInterface
        record_type = "neuroconv_caiman_segmentation"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".h5", ".hdf5")
        extraction_prefix = "ophys.caiman_segmentation"
        default_device_name = "Caiman"
        source_format = "caiman_file"

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return source.adapter_hint == self.adapter_id or _contains_any_token(
                source.location,
                ("caiman", "cnmf", "estimates"),
            )

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv Caiman segmentation conversion into NWB ophys segmentation data.",
                "Caiman segmentation stays conservative and prefers explicit hints or distinctive Caiman-style filenames over generic HDF5 matching.",
            )


if CnmfeSegmentationInterface is not None:

    class NeuroConvCnmfeSegmentationAdapter(_NeuroConvSegmentationAdapter):
        """Inspect and convert CNMFE segmentation outputs through NeuroConv."""

        adapter_id = "neuroconv_cnmfe_segmentation"
        display_name = "NeuroConv CNMFE segmentation adapter"
        version = "0.1.0"
        interface_cls = CnmfeSegmentationInterface
        record_type = "neuroconv_cnmfe_segmentation"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".mat",)
        extraction_prefix = "ophys.cnmfe_segmentation"
        default_device_name = "CNMFE"
        source_format = "cnmfe_mat"

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return source.adapter_hint == self.adapter_id or _contains_any_token(
                source.location,
                ("cnmfe", "cnmf"),
            )

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv CNMFE segmentation conversion into NWB ophys segmentation data.",
                "CNMFE segmentation prefers explicit hints or CNMFE-style filenames instead of claiming generic MATLAB files.",
            )


if ExtractSegmentationInterface is not None:

    class NeuroConvExtractSegmentationAdapter(_NeuroConvSegmentationAdapter):
        """Inspect and convert EXTRACT segmentation outputs through NeuroConv."""

        adapter_id = "neuroconv_extract_segmentation"
        display_name = "NeuroConv EXTRACT segmentation adapter"
        version = "0.1.0"
        interface_cls = ExtractSegmentationInterface
        record_type = "neuroconv_extract_segmentation"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".mat",)
        extraction_prefix = "ophys.extract_segmentation"
        default_device_name = "EXTRACT"
        source_format = "extract_mat"

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            has_sampling_frequency = "sampling_frequency" in config.interface_kwargs
            return has_sampling_frequency and (
                source.adapter_hint == self.adapter_id or _contains_any_token(source.location, ("extract",))
            )

        def additional_payload(
            self,
            *,
            source: SourceReference,
            metadata: dict[str, object],
            config: NeuroConvSourceConfig,
        ) -> dict[str, object]:
            del source, metadata
            return {
                "sampling_frequency": config.interface_kwargs.get("sampling_frequency"),
                "has_output_struct_name": "output_struct_name" in config.interface_kwargs,
            }

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv EXTRACT segmentation conversion into NWB ophys segmentation data.",
                "EXTRACT segmentation is configuration-driven and requires an explicit sampling_frequency to avoid claiming arbitrary MATLAB files.",
            )


if InscopixSegmentationInterface is not None:

    class NeuroConvInscopixSegmentationAdapter(_NeuroConvSegmentationAdapter):
        """Inspect and convert Inscopix segmentation outputs through NeuroConv."""

        adapter_id = "neuroconv_inscopix_segmentation"
        display_name = "NeuroConv Inscopix segmentation adapter"
        version = "0.1.0"
        interface_cls = InscopixSegmentationInterface
        record_type = "neuroconv_inscopix_segmentation"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".isxd",)
        extraction_prefix = "ophys.inscopix_segmentation"
        default_device_name = "Inscopix"
        source_format = "inscopix_segmentation_isxd"

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return source.location.suffix.lower() in self.supported_suffixes and (
                source.adapter_hint == self.adapter_id or _contains_any_token(source.location, ("cellset", "cnmfe", "seg"))
            )

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv Inscopix segmentation conversion into NWB ophys segmentation data.",
                "Inscopix segmentation stays on .isxd outputs and can be selected explicitly when imaging and segmentation exports sit side by side.",
            )


if Suite2pSegmentationInterface is not None:

    class NeuroConvSuite2pSegmentationAdapter(_NeuroConvSegmentationAdapter):
        """Inspect and convert Suite2p segmentation folders through NeuroConv."""

        adapter_id = "neuroconv_suite2p_segmentation"
        display_name = "NeuroConv Suite2p segmentation adapter"
        version = "0.1.0"
        interface_cls = Suite2pSegmentationInterface
        source_path_kwarg = "folder_path"
        record_type = "neuroconv_suite2p_segmentation"
        source_types = (SourceType.DIRECTORY,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        extraction_prefix = "ophys.suite2p_segmentation"
        default_device_name = "Suite2p"
        source_format = "suite2p_folder"

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return _looks_like_suite2p_folder(source.location)

        def build_interface(self, source: SourceReference, config: NeuroConvSourceConfig):
            interface_kwargs = {"folder_path": source.location}
            interface_kwargs.update(config.interface_kwargs)
            interface_kwargs.setdefault("verbose", False)
            return self.interface_cls(**interface_kwargs)

        def additional_payload(
            self,
            *,
            source: SourceReference,
            metadata: dict[str, object],
            config: NeuroConvSourceConfig,
        ) -> dict[str, object]:
            del source, metadata
            return {
                "channel_name": config.interface_kwargs.get("channel_name"),
                "plane_name": config.interface_kwargs.get("plane_name"),
                "plane_segmentation_name": config.interface_kwargs.get("plane_segmentation_name"),
            }

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv Suite2p segmentation conversion into NWB ophys segmentation data.",
                "Suite2p segmentation matches only folders with stat.npy, iscell.npy, and ops.npy so it does not collide with KiloSort sorting folders.",
            )
