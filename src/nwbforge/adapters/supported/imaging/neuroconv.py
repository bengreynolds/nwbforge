"""NeuroConv-backed adapters for supported imaging routes."""

from __future__ import annotations

from pathlib import Path

try:
    from neuroconv.datainterfaces import Hdf5ImagingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    Hdf5ImagingInterface = None

try:
    from neuroconv.datainterfaces import ScanImageImagingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    ScanImageImagingInterface = None

from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.adapters.neuroconv import (
    NeuroConvDirectConversionAdapter,
    NeuroConvSourceConfig,
    extracted_fields_from_mapping,
)
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ExtractedField, ReviewIssue, SourceReference


if ScanImageImagingInterface is not None:

    class NeuroConvScanImageAdapter(NeuroConvDirectConversionAdapter):
        """Inspect and convert ScanImage TIFF sources through NeuroConv."""

        adapter_id = "neuroconv_scanimage"
        display_name = "NeuroConv ScanImage adapter"
        version = "0.1.0"
        interface_cls = ScanImageImagingInterface
        record_type = "neuroconv_scanimage"
        source_types = (SourceType.FILE, SourceType.DIRECTORY)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".tif", ".tiff")

        def can_handle(self, source: SourceReference) -> bool:
            if source.source_type not in self.source_types:
                return False
            try:
                config = self.build_source_config(source)
            except ValueError:
                return False
            return self.matches_source(source, config)

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            if source.source_type == SourceType.FILE:
                return source.location.suffix.lower() in self.supported_suffixes
            try:
                return len(self._tiff_files(source.location)) > 0
            except OSError:
                return False

        def build_interface(self, source: SourceReference, config: NeuroConvSourceConfig):
            interface_kwargs = dict(config.interface_kwargs)
            interface_kwargs.setdefault("verbose", False)
            if source.source_type == SourceType.FILE:
                interface_kwargs.setdefault("file_path", source.location)
            else:
                file_paths = self._tiff_files(source.location)
                if not file_paths:
                    raise ValueError(f"No ScanImage-compatible TIFF files found in {source.location}.")
                interface_kwargs.setdefault("file_path", file_paths[0])
                if len(file_paths) > 1:
                    interface_kwargs.setdefault("file_paths", file_paths)
            return self.interface_cls(**interface_kwargs)

        def extract(
            self,
            *,
            source: SourceReference,
            interface,
            config: NeuroConvSourceConfig,
        ) -> tuple[dict[str, ExtractedField], list[ReviewIssue], tuple[str, ...]]:
            metadata = interface.get_metadata()
            ophys_metadata = metadata.get("Ophys", {})
            photon_series_type = "TwoPhotonSeries" if ophys_metadata.get("TwoPhotonSeries") else "OnePhotonSeries"
            file_count = 1 if source.source_type == SourceType.FILE else len(self._tiff_files(source.location))
            fields = extracted_fields_from_mapping(
                prefix="ophys.scanimage",
                payload={
                    "source_format": "scanimage_tiff",
                    "file_count": file_count,
                    "channel_name": config.interface_kwargs.get("channel_name"),
                    "plane_index": config.interface_kwargs.get("plane_index"),
                    "photon_series_type": photon_series_type,
                    "has_session_start_time": "session_start_time" in metadata.get("NWBFile", {}),
                },
                source_id=source.source_id,
            )
            notes = (
                "Prepared NeuroConv ScanImage conversion into ophys imaging data.",
                "Multi-channel datasets may require an explicit channel_name in source metadata or the UI.",
            )
            return fields, [], notes

        def _tiff_files(self, location: Path) -> list[Path]:
            return sorted(
                path
                for path in location.iterdir()
                if path.is_file() and path.suffix.lower() in self.supported_suffixes
            )


if Hdf5ImagingInterface is not None:

    class NeuroConvHdf5ImagingAdapter(NeuroConvDirectConversionAdapter):
        """Inspect and convert extractor-backed HDF5 imaging sources through NeuroConv."""

        adapter_id = "neuroconv_hdf5_imaging"
        display_name = "NeuroConv HDF5 imaging adapter"
        version = "0.1.0"
        interface_cls = Hdf5ImagingInterface
        record_type = "neuroconv_hdf5_imaging"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".h5", ".hdf5")

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return source.location.suffix.lower() in self.supported_suffixes

        def build_interface(self, source: SourceReference, config: NeuroConvSourceConfig):
            interface_kwargs = {self.source_path_kwarg: source.location}
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
            metadata = interface.get_metadata()
            ophys_metadata = metadata.get("Ophys", {})
            fields = extracted_fields_from_mapping(
                prefix="ophys.hdf5",
                payload={
                    "source_format": source.location.suffix.lower().lstrip("."),
                    "mov_field": config.interface_kwargs.get("mov_field", "mov"),
                    "sampling_frequency": config.interface_kwargs.get("sampling_frequency"),
                    "channel_names": tuple(config.interface_kwargs.get("channel_names", ())),
                    "photon_series_type": config.interface_kwargs.get("photon_series_type", "TwoPhotonSeries"),
                    "has_imaging_plane_metadata": "ImagingPlane" in ophys_metadata,
                },
                source_id=source.source_id,
            )
            notes = (
                "Prepared NeuroConv HDF5 imaging conversion into ophys imaging data.",
                "HDF5 imaging sources may require mov_field and sampling_frequency metadata when not embedded in the file.",
            )
            return fields, [], notes
