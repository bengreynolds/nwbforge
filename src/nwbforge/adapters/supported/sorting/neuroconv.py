"""NeuroConv-backed adapters for supported sorting routes."""

from __future__ import annotations

from pathlib import Path

try:
    from neuroconv.datainterfaces import BlackrockSortingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    BlackrockSortingInterface = None

try:
    from neuroconv.datainterfaces import CellExplorerSortingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    CellExplorerSortingInterface = None

try:
    from neuroconv.datainterfaces import KiloSortSortingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    KiloSortSortingInterface = None

try:
    from neuroconv.datainterfaces import NeuralynxSortingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    NeuralynxSortingInterface = None

try:
    from neuroconv.datainterfaces import NeuroScopeSortingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    NeuroScopeSortingInterface = None

try:
    from neuroconv.datainterfaces import PhySortingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    PhySortingInterface = None

try:
    from neuroconv.datainterfaces import PlexonSortingInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    PlexonSortingInterface = None

from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.adapters.neuroconv import (
    NeuroConvDirectConversionAdapter,
    NeuroConvSourceConfig,
    extracted_fields_from_mapping,
)
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ExtractedField, ReviewIssue, SourceReference


def _directory_has_any_suffix(folder_path: Path, suffixes: tuple[str, ...]) -> bool:
    return any(path.is_file() and path.suffix.lower() in suffixes for path in folder_path.rglob("*"))


def _directory_has_named_files(folder_path: Path, filenames: tuple[str, ...]) -> bool:
    lowered = {name.lower() for name in filenames}
    return any(path.is_file() and path.name.lower() in lowered for path in folder_path.rglob("*"))


class _NeuroConvSortingAdapter(NeuroConvDirectConversionAdapter):
    """Shared extraction helpers for NeuroConv-backed sorting routes."""

    extraction_prefix = "sorting.generic"
    default_device_name = "SortingDevice"
    source_format = "sorting"

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
        unit_properties = ecephys_metadata.get("UnitProperties") or ()
        electrode_groups = ecephys_metadata.get("ElectrodeGroup") or ()
        fields = extracted_fields_from_mapping(
            prefix=self.extraction_prefix,
            payload={
                "source_format": self.source_format,
                "device_name": device_metadata[0].get("name", self.default_device_name),
                "unit_property_count": len(unit_properties),
                "electrode_group_count": len(electrode_groups),
                "has_session_start_time": "session_start_time" in metadata.get("NWBFile", {}),
                **self.additional_payload(source=source, metadata=metadata, config=config),
            },
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
        return ("Prepared NeuroConv sorting conversion into NWB units data.",)


if BlackrockSortingInterface is not None:

    class NeuroConvBlackrockSortingAdapter(_NeuroConvSortingAdapter):
        """Inspect and convert Blackrock sorting sources through NeuroConv."""

        adapter_id = "neuroconv_blackrock_sorting"
        display_name = "NeuroConv Blackrock sorting adapter"
        version = "0.1.0"
        interface_cls = BlackrockSortingInterface
        record_type = "neuroconv_blackrock_sorting"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".nev",)
        extraction_prefix = "sorting.blackrock"
        default_device_name = "Blackrock"
        source_format = "blackrock_nev"

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return source.location.suffix.lower() in self.supported_suffixes

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
                "nsx_to_load": config.interface_kwargs.get("nsx_to_load"),
            }

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv Blackrock sorting conversion into NWB units data.",
                "Blackrock sorting matches distinctive .nev files and does not overlap with the recording path that prefers .nsx files.",
            )


if CellExplorerSortingInterface is not None:

    class NeuroConvCellExplorerSortingAdapter(_NeuroConvSortingAdapter):
        """Inspect and convert Cell Explorer sorting sources through NeuroConv."""

        adapter_id = "neuroconv_cellexplorer_sorting"
        display_name = "NeuroConv Cell Explorer sorting adapter"
        version = "0.1.0"
        interface_cls = CellExplorerSortingInterface
        record_type = "neuroconv_cellexplorer_sorting"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".mat",)
        extraction_prefix = "sorting.cellexplorer"
        default_device_name = "CellExplorer"
        source_format = "cellexplorer_cellinfo_mat"

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            name = source.location.name.lower()
            return source.location.suffix.lower() == ".mat" and "cellinfo" in name and "spikes" in name

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv Cell Explorer sorting conversion into NWB units data.",
                "Cell Explorer sorting matches explicit spikes.cellinfo.mat-style files rather than generic MATLAB files.",
            )


if KiloSortSortingInterface is not None:

    class NeuroConvKiloSortSortingAdapter(_NeuroConvSortingAdapter):
        """Inspect and convert KiloSort sorting folders through NeuroConv."""

        adapter_id = "neuroconv_kilosort_sorting"
        display_name = "NeuroConv KiloSort sorting adapter"
        version = "0.1.0"
        interface_cls = KiloSortSortingInterface
        source_path_kwarg = "folder_path"
        record_type = "neuroconv_kilosort_sorting"
        source_types = (SourceType.DIRECTORY,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        extraction_prefix = "sorting.kilosort"
        default_device_name = "KiloSort"
        source_format = "kilosort_folder"

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            if not source.location.is_dir():
                return False
            return (source.location / "params.py").is_file() and (
                (source.location / "ops.npy").is_file() or (source.location / "rez.mat").is_file()
            )

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
            return {"keep_good_only": bool(config.interface_kwargs.get("keep_good_only", False))}

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv KiloSort sorting conversion into NWB units data.",
                "KiloSort sorting matches Phy-style folders only when KiloSort-specific markers such as ops.npy or rez.mat are present.",
            )


if NeuralynxSortingInterface is not None:

    class NeuroConvNeuralynxSortingAdapter(_NeuroConvSortingAdapter):
        """Inspect and convert Neuralynx sorting folders through NeuroConv."""

        adapter_id = "neuroconv_neuralynx_sorting"
        display_name = "NeuroConv Neuralynx sorting adapter"
        version = "0.1.0"
        interface_cls = NeuralynxSortingInterface
        source_path_kwarg = "folder_path"
        record_type = "neuroconv_neuralynx_sorting"
        source_types = (SourceType.DIRECTORY,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        extraction_prefix = "sorting.neuralynx"
        default_device_name = "Neuralynx"
        source_format = "neuralynx_sorting_folder"

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return (
                source.location.is_dir()
                and source.adapter_hint == self.adapter_id
                and _directory_has_any_suffix(source.location, (".nse", ".ntt", ".nev"))
            )

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
                "sampling_frequency": config.interface_kwargs.get("sampling_frequency"),
                "stream_id": config.interface_kwargs.get("stream_id"),
            }

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv Neuralynx sorting conversion into NWB units data.",
                "Neuralynx sorting is currently hint-driven in the app because the folder-level sorting and recording readers overlap too heavily for safe auto-selection.",
            )


if NeuroScopeSortingInterface is not None:

    class NeuroConvNeuroScopeSortingAdapter(_NeuroConvSortingAdapter):
        """Inspect and convert NeuroScope sorting folders through NeuroConv."""

        adapter_id = "neuroconv_neuroscope_sorting"
        display_name = "NeuroConv NeuroScope sorting adapter"
        version = "0.1.0"
        interface_cls = NeuroScopeSortingInterface
        source_path_kwarg = "folder_path"
        record_type = "neuroconv_neuroscope_sorting"
        source_types = (SourceType.DIRECTORY,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        extraction_prefix = "sorting.neuroscope"
        default_device_name = "NeuroScope"
        source_format = "neuroscope_sorting_folder"

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return (
                source.location.is_dir()
                and any(path.is_file() and ".res." in path.name.lower() for path in source.location.rglob("*"))
                and any(path.is_file() and ".clu." in path.name.lower() for path in source.location.rglob("*"))
            )

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
            del metadata
            exclude_shanks = tuple(config.interface_kwargs.get("exclude_shanks", ()))
            return {
                "keep_mua_units": bool(config.interface_kwargs.get("keep_mua_units", True)),
                "exclude_shank_count": len(exclude_shanks),
                "has_xml_sidecar": "xml_file_path" in config.interface_kwargs
                or any(path.is_file() and path.suffix.lower() == ".xml" for path in source.location.iterdir()),
            }

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv NeuroScope sorting conversion into NWB units data.",
                "NeuroScope sorting prefers folders with paired .res.* and .clu.* files rather than the .dat recording path.",
            )


if PhySortingInterface is not None:

    class NeuroConvPhySortingAdapter(_NeuroConvSortingAdapter):
        """Inspect and convert Phy sorting folders through NeuroConv."""

        adapter_id = "neuroconv_phy_sorting"
        display_name = "NeuroConv Phy sorting adapter"
        version = "0.1.0"
        interface_cls = PhySortingInterface
        source_path_kwarg = "folder_path"
        record_type = "neuroconv_phy_sorting"
        source_types = (SourceType.DIRECTORY,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        extraction_prefix = "sorting.phy"
        default_device_name = "Phy"
        source_format = "phy_folder"

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            if not source.location.is_dir():
                return False
            has_params = (source.location / "params.py").is_file()
            has_phy_cluster_files = _directory_has_named_files(
                source.location,
                ("cluster_info.tsv", "cluster_info.csv", "cluster_group.tsv", "cluster_group.csv"),
            )
            has_kilosort_markers = (source.location / "ops.npy").is_file() or (source.location / "rez.mat").is_file()
            return has_params and has_phy_cluster_files and not has_kilosort_markers

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
            excluded = tuple(config.interface_kwargs.get("exclude_cluster_groups", ()))
            return {"excluded_cluster_group_count": len(excluded)}

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv Phy sorting conversion into NWB units data.",
                "Phy sorting prefers params.py folders with cluster_info or cluster_group tables and defers folders with stronger KiloSort markers to the KiloSort route.",
            )


if PlexonSortingInterface is not None:

    class NeuroConvPlexonSortingAdapter(_NeuroConvSortingAdapter):
        """Inspect and convert Plexon sorting `.plx` sources through NeuroConv."""

        adapter_id = "neuroconv_plexon_sorting"
        display_name = "NeuroConv Plexon sorting adapter"
        version = "0.1.0"
        interface_cls = PlexonSortingInterface
        record_type = "neuroconv_plexon_sorting"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".plx",)
        extraction_prefix = "sorting.plexon"
        default_device_name = "Plexon"
        source_format = "plexon_plx_sorting"

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return source.adapter_hint == self.adapter_id and source.location.suffix.lower() in self.supported_suffixes

        def extraction_notes(self) -> tuple[str, ...]:
            return (
                "Prepared NeuroConv Plexon sorting conversion into NWB units data.",
                "Plexon sorting is currently hint-driven in the app because the same .plx files can also represent the recording route.",
            )
