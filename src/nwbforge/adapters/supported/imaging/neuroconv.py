"""NeuroConv-backed adapters for supported imaging routes."""

from __future__ import annotations

from pathlib import Path

try:
    from neuroconv.datainterfaces import BrukerTiffMultiPlaneImagingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    BrukerTiffMultiPlaneImagingInterface = None

try:
    from neuroconv.datainterfaces import BrukerTiffSinglePlaneImagingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    BrukerTiffSinglePlaneImagingInterface = None

try:
    from neuroconv.datainterfaces import FemtonicsImagingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    FemtonicsImagingInterface = None

try:
    from neuroconv.datainterfaces import Hdf5ImagingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    Hdf5ImagingInterface = None

try:
    from neuroconv.datainterfaces import InscopixImagingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    InscopixImagingInterface = None

try:
    from neuroconv.datainterfaces import MicroManagerTiffImagingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    MicroManagerTiffImagingInterface = None

try:
    from neuroconv.datainterfaces import MiniscopeImagingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    MiniscopeImagingInterface = None

try:
    from neuroconv.datainterfaces import ScanImageImagingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    ScanImageImagingInterface = None

try:
    from neuroconv.datainterfaces import ScanImageLegacyImagingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    ScanImageLegacyImagingInterface = None

try:
    from neuroconv.datainterfaces import ThorImagingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    ThorImagingInterface = None

from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.adapters.neuroconv import (
    NeuroConvDirectConversionAdapter,
    NeuroConvSourceConfig,
    extracted_fields_from_mapping,
)
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ExtractedField, ReviewIssue, SourceReference


def _tiff_files(location: Path) -> list[Path]:
    if location.is_file():
        return [location]
    return sorted(
        path
        for path in location.iterdir()
        if path.is_file() and path.suffix.lower() in (".tif", ".tiff")
    )


def _scanimage_version(file_path: Path) -> int | None:
    if ScanImageImagingInterface is None:
        return None
    try:
        return int(ScanImageImagingInterface.get_scanimage_version(file_path))
    except Exception:
        return None


def _scanimage_matches_current(location: Path) -> bool:
    file_paths = _tiff_files(location)
    if not file_paths:
        return False
    version = _scanimage_version(file_paths[0])
    return version is None or version >= 4


def _scanimage_matches_legacy(location: Path) -> bool:
    file_paths = _tiff_files(location)
    if not file_paths:
        return False
    version = _scanimage_version(file_paths[0])
    return version is not None and version < 4


def _looks_like_bruker_directory(location: Path) -> bool:
    if not location.is_dir():
        return False
    has_ome_tiff = any(path.is_file() for path in location.glob("*.ome.tif*"))
    has_descriptor = any(path.is_file() and path.suffix.lower() in (".xml", ".env") for path in location.iterdir())
    return has_ome_tiff and has_descriptor


def _bruker_streams(location: Path) -> dict[str, object]:
    if BrukerTiffMultiPlaneImagingInterface is None:
        return {}
    try:
        return BrukerTiffMultiPlaneImagingInterface.get_streams(folder_path=location)
    except Exception:
        return {}


def _bruker_is_multiplane(location: Path) -> bool:
    streams = _bruker_streams(location)
    plane_streams = streams.get("plane_streams", {})
    return any(len(tuple(stream_names)) > 1 for stream_names in plane_streams.values())


def _ophys_device_name(metadata: dict[str, object], default_name: str) -> str:
    device_metadata = metadata.get("Ophys", {}).get("Device") or [{}]
    return device_metadata[0].get("name", default_name)


def _ophys_series_type(metadata: dict[str, object], default_value: str = "") -> str:
    ophys_metadata = metadata.get("Ophys", {})
    if ophys_metadata.get("TwoPhotonSeries"):
        return "TwoPhotonSeries"
    if ophys_metadata.get("OnePhotonSeries"):
        return "OnePhotonSeries"
    return default_value


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
                return source.location.suffix.lower() in self.supported_suffixes and _scanimage_matches_current(
                    source.location
                )
            try:
                return _scanimage_matches_current(source.location)
            except OSError:
                return False

        def build_interface(self, source: SourceReference, config: NeuroConvSourceConfig):
            interface_kwargs = dict(config.interface_kwargs)
            interface_kwargs.setdefault("verbose", False)
            if source.source_type == SourceType.FILE:
                interface_kwargs.setdefault("file_path", source.location)
            else:
                file_paths = _tiff_files(source.location)
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
            file_count = 1 if source.source_type == SourceType.FILE else len(_tiff_files(source.location))
            fields = extracted_fields_from_mapping(
                prefix="ophys.scanimage",
                payload={
                    "source_format": "scanimage_tiff",
                    "file_count": file_count,
                    "channel_name": config.interface_kwargs.get("channel_name"),
                    "plane_index": config.interface_kwargs.get("plane_index"),
                    "photon_series_type": _ophys_series_type(metadata, default_value="OnePhotonSeries"),
                    "has_session_start_time": "session_start_time" in metadata.get("NWBFile", {}),
                },
                source_id=source.source_id,
            )
            notes = (
                "Prepared NeuroConv ScanImage conversion into ophys imaging data.",
                "ScanImage route matching now excludes legacy TIFFs so current and legacy readers do not overlap.",
            )
            return fields, [], notes


if ScanImageLegacyImagingInterface is not None:

    class NeuroConvScanImageLegacyAdapter(NeuroConvDirectConversionAdapter):
        """Inspect and convert ScanImage legacy TIFF sources through NeuroConv."""

        adapter_id = "neuroconv_scanimage_legacy"
        display_name = "NeuroConv ScanImage Legacy adapter"
        version = "0.1.0"
        interface_cls = ScanImageLegacyImagingInterface
        record_type = "neuroconv_scanimage_legacy"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".tif", ".tiff")

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return source.location.suffix.lower() in self.supported_suffixes and _scanimage_matches_legacy(
                source.location
            )

        def extract(
            self,
            *,
            source: SourceReference,
            interface,
            config: NeuroConvSourceConfig,
        ) -> tuple[dict[str, ExtractedField], list[ReviewIssue], tuple[str, ...]]:
            metadata = interface.get_metadata()
            fields = extracted_fields_from_mapping(
                prefix="ophys.scanimage_legacy",
                payload={
                    "source_format": "scanimage_legacy_tiff",
                    "fallback_sampling_frequency": config.interface_kwargs.get("fallback_sampling_frequency"),
                    "scanimage_version": _scanimage_version(source.location),
                    "photon_series_type": _ophys_series_type(metadata, default_value="TwoPhotonSeries"),
                    "has_session_start_time": "session_start_time" in metadata.get("NWBFile", {}),
                },
                source_id=source.source_id,
            )
            notes = (
                "Prepared NeuroConv ScanImage Legacy conversion into ophys imaging data.",
                "Legacy ScanImage routing is restricted to TIFF sources detected as pre-v4 scanimage files.",
            )
            return fields, [], notes


if BrukerTiffSinglePlaneImagingInterface is not None:

    class NeuroConvBrukerTiffSinglePlaneAdapter(NeuroConvDirectConversionAdapter):
        """Inspect and convert Bruker single-plane TIFF folders through NeuroConv."""

        adapter_id = "neuroconv_brukertiff_singleplane"
        display_name = "NeuroConv Bruker TIFF single-plane adapter"
        version = "0.1.0"
        interface_cls = BrukerTiffSinglePlaneImagingInterface
        source_path_kwarg = "folder_path"
        record_type = "neuroconv_brukertiff_singleplane"
        source_types = (SourceType.DIRECTORY,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return _looks_like_bruker_directory(source.location) and not _bruker_is_multiplane(source.location)

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
            metadata = interface.get_metadata()
            streams = _bruker_streams(source.location)
            fields = extracted_fields_from_mapping(
                prefix="ophys.brukertiff_singleplane",
                payload={
                    "source_format": "bruker_tiff_directory",
                    "stream_name": config.interface_kwargs.get("stream_name"),
                    "channel_stream_count": len(tuple(streams.get("channel_streams", ()))),
                    "device_name": _ophys_device_name(metadata, "Bruker Microscope"),
                    "photon_series_type": _ophys_series_type(metadata, default_value="TwoPhotonSeries"),
                    "has_session_start_time": "session_start_time" in metadata.get("NWBFile", {}),
                },
                source_id=source.source_id,
            )
            notes = (
                "Prepared NeuroConv Bruker TIFF single-plane conversion into ophys imaging data.",
                "Bruker single-plane routing is separated from multiplane routing through NeuroConv stream inspection.",
            )
            return fields, [], notes


if BrukerTiffMultiPlaneImagingInterface is not None:

    class NeuroConvBrukerTiffMultiPlaneAdapter(NeuroConvDirectConversionAdapter):
        """Inspect and convert Bruker multi-plane TIFF folders through NeuroConv."""

        adapter_id = "neuroconv_brukertiff_multiplane"
        display_name = "NeuroConv Bruker TIFF multi-plane adapter"
        version = "0.1.0"
        interface_cls = BrukerTiffMultiPlaneImagingInterface
        source_path_kwarg = "folder_path"
        record_type = "neuroconv_brukertiff_multiplane"
        source_types = (SourceType.DIRECTORY,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return _looks_like_bruker_directory(source.location) and _bruker_is_multiplane(source.location)

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
            metadata = interface.get_metadata()
            streams = _bruker_streams(source.location)
            plane_streams = streams.get("plane_streams", {})
            max_plane_count = max((len(tuple(stream_names)) for stream_names in plane_streams.values()), default=0)
            fields = extracted_fields_from_mapping(
                prefix="ophys.brukertiff_multiplane",
                payload={
                    "source_format": "bruker_tiff_directory",
                    "stream_name": config.interface_kwargs.get("stream_name"),
                    "channel_stream_count": len(tuple(streams.get("channel_streams", ()))),
                    "max_plane_count": max_plane_count,
                    "device_name": _ophys_device_name(metadata, "Bruker Microscope"),
                    "photon_series_type": _ophys_series_type(metadata, default_value="TwoPhotonSeries"),
                    "has_session_start_time": "session_start_time" in metadata.get("NWBFile", {}),
                },
                source_id=source.source_id,
            )
            notes = (
                "Prepared NeuroConv Bruker TIFF multi-plane conversion into ophys imaging data.",
                "Bruker multi-plane routing stays distinct so volumetric data is not flattened into the single-plane path.",
            )
            return fields, [], notes


if FemtonicsImagingInterface is not None:

    class NeuroConvFemtonicsAdapter(NeuroConvDirectConversionAdapter):
        """Inspect and convert Femtonics MESc sources through NeuroConv."""

        adapter_id = "neuroconv_femtonics"
        display_name = "NeuroConv Femtonics adapter"
        version = "0.1.0"
        interface_cls = FemtonicsImagingInterface
        record_type = "neuroconv_femtonics"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".mesc",)

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
            fields = extracted_fields_from_mapping(
                prefix="ophys.femtonics",
                payload={
                    "source_format": "mesc",
                    "session_name": config.interface_kwargs.get("session_name"),
                    "munit_name": config.interface_kwargs.get("munit_name"),
                    "channel_name": config.interface_kwargs.get("channel_name"),
                    "device_name": _ophys_device_name(metadata, "Femtonics"),
                    "photon_series_type": _ophys_series_type(metadata, default_value="TwoPhotonSeries"),
                    "has_session_start_time": "session_start_time" in metadata.get("NWBFile", {}),
                },
                source_id=source.source_id,
            )
            notes = (
                "Prepared NeuroConv Femtonics conversion into ophys imaging data.",
                "Femtonics MESc sources may require explicit session, MUnit, or channel selection when the file is not singular.",
            )
            return fields, [], notes


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


if InscopixImagingInterface is not None:

    class NeuroConvInscopixAdapter(NeuroConvDirectConversionAdapter):
        """Inspect and convert Inscopix imaging sources through NeuroConv."""

        adapter_id = "neuroconv_inscopix"
        display_name = "NeuroConv Inscopix adapter"
        version = "0.1.0"
        interface_cls = InscopixImagingInterface
        record_type = "neuroconv_inscopix"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".isxd",)

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
            fields = extracted_fields_from_mapping(
                prefix="ophys.inscopix",
                payload={
                    "source_format": "isxd",
                    "device_name": _ophys_device_name(metadata, "Inscopix"),
                    "photon_series_type": _ophys_series_type(metadata, default_value="OnePhotonSeries"),
                    "session_id": metadata.get("NWBFile", {}).get("session_id"),
                    "has_session_start_time": "session_start_time" in metadata.get("NWBFile", {}),
                },
                source_id=source.source_id,
            )
            notes = (
                "Prepared NeuroConv Inscopix conversion into one-photon imaging data.",
                "Inscopix routing stays constrained to .isxd files and inherits NeuroConv's multiplane safety checks.",
            )
            return fields, [], notes


if MicroManagerTiffImagingInterface is not None:

    class NeuroConvMicroManagerTiffAdapter(NeuroConvDirectConversionAdapter):
        """Inspect and convert Micro-Manager TIFF directory sources through NeuroConv."""

        adapter_id = "neuroconv_micromanager_tiff"
        display_name = "NeuroConv Micro-Manager TIFF adapter"
        version = "0.1.0"
        interface_cls = MicroManagerTiffImagingInterface
        record_type = "neuroconv_micromanager_tiff"
        source_types = (SourceType.DIRECTORY,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return self._looks_like_micromanager_directory(source.location)

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
            metadata = interface.get_metadata()
            fields = extracted_fields_from_mapping(
                prefix="ophys.micromanager",
                payload={
                    "source_format": "micromanager_tiff_directory",
                    "file_count": len(tuple(source.location.glob("*.ome.tif*"))),
                    "has_session_start_time": "session_start_time" in metadata.get("NWBFile", {}),
                    "photon_series_type": _ophys_series_type(metadata),
                },
                source_id=source.source_id,
            )
            notes = ("Prepared NeuroConv Micro-Manager TIFF conversion into ophys imaging data.",)
            return fields, [], notes

        @staticmethod
        def _looks_like_micromanager_directory(location: Path) -> bool:
            if not location.is_dir():
                return False
            has_ome_tiff = any(path.is_file() for path in location.glob("*.ome.tif*"))
            has_settings = any("displaysettings" in path.name.lower() for path in location.glob("*.json"))
            return has_ome_tiff and has_settings


if MiniscopeImagingInterface is not None:

    class NeuroConvMiniscopeAdapter(NeuroConvDirectConversionAdapter):
        """Inspect and convert Miniscope recording folders through NeuroConv."""

        adapter_id = "neuroconv_miniscope"
        display_name = "NeuroConv Miniscope adapter"
        version = "0.1.0"
        interface_cls = MiniscopeImagingInterface
        record_type = "neuroconv_miniscope"
        source_types = (SourceType.DIRECTORY,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return self._looks_like_miniscope_directory(source.location)

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
            metadata = interface.get_metadata()
            device_metadata = metadata.get("Ophys", {}).get("Device", [{}])
            one_photon_series = metadata.get("Ophys", {}).get("OnePhotonSeries", [{}])
            fields = extracted_fields_from_mapping(
                prefix="ophys.miniscope",
                payload={
                    "source_format": "miniscope_directory",
                    "device_name": device_metadata[0].get("name", "Miniscope"),
                    "series_name": one_photon_series[0].get("name", "OnePhotonSeries"),
                    "has_session_start_time": "session_start_time" in metadata.get("NWBFile", {}),
                    "is_one_photon": bool(one_photon_series and one_photon_series[0]),
                },
                source_id=source.source_id,
            )
            notes = ("Prepared NeuroConv Miniscope conversion into one-photon ophys imaging data.",)
            return fields, [], notes

        @staticmethod
        def _looks_like_miniscope_directory(location: Path) -> bool:
            if not location.is_dir():
                return False
            return (location / "metaData.json").is_file() and any(location.glob("*.avi"))


if ThorImagingInterface is not None:

    class NeuroConvThorAdapter(NeuroConvDirectConversionAdapter):
        """Inspect and convert ThorImageLS TIFF sources through NeuroConv."""

        adapter_id = "neuroconv_thor"
        display_name = "NeuroConv Thor adapter"
        version = "0.1.0"
        interface_cls = ThorImagingInterface
        record_type = "neuroconv_thor"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".tif", ".tiff")

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return source.location.suffix.lower() in self.supported_suffixes and (
                source.location.parent / "Experiment.xml"
            ).is_file()

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
                prefix="ophys.thor",
                payload={
                    "source_format": "thor_tiff",
                    "channel_name": config.interface_kwargs.get("channel_name"),
                    "has_session_start_time": "session_start_time" in metadata.get("NWBFile", {}),
                    "device_name": (ophys_metadata.get("Device") or [{}])[0].get("name", "ThorMicroscope"),
                    "photon_series_type": _ophys_series_type(metadata),
                },
                source_id=source.source_id,
            )
            notes = ("Prepared NeuroConv Thor conversion into ophys imaging data.",)
            return fields, [], notes
