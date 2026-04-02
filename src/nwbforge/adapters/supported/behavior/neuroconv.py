"""NeuroConv-backed adapters for supported behavior routes."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from neuroconv.datainterfaces import DeepLabCutInterface, FicTracDataInterface

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


class NeuroConvDeepLabCutAdapter(NeuroConvDirectConversionAdapter):
    """Inspect and convert DeepLabCut output files through NeuroConv."""

    adapter_id = "neuroconv_deeplabcut"
    display_name = "NeuroConv DeepLabCut adapter"
    version = "0.1.0"
    interface_cls = DeepLabCutInterface
    record_type = "neuroconv_deeplabcut"
    source_types = (SourceType.FILE,)
    capabilities = AdapterCapabilities(
        supported_pathways=(ConversionPathway.SUPPORTED,),
        supports_multi_source_sessions=True,
    )
    supported_suffixes = (".csv", ".h5")

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
        bodypart_count, subject_count = self._counts_from_source(source)
        fields = extracted_fields_from_mapping(
            prefix="behavior.deeplabcut",
            payload={
                "source_format": source.location.suffix.lower().lstrip("."),
                "bodypart_count": bodypart_count,
                "subject_count": subject_count,
                "subject_name": config.interface_kwargs.get("subject_name", "ind1"),
                "has_config_file": str(config.interface_kwargs.get("config_file_path", "")) != "",
                "pose_container_name": metadata.get("PoseEstimation", {})
                .get("PoseEstimationContainers", {})
                .get(config.interface_kwargs.get("pose_estimation_metadata_key", "PoseEstimationDeepLabCut"), {})
                .get("name", "PoseEstimationDeepLabCut"),
            },
            source_id=source.source_id,
        )
        notes = ("Prepared NeuroConv DeepLabCut conversion into pose-estimation processing data.",)
        return fields, [], notes

    @staticmethod
    def _counts_from_source(source: SourceReference) -> tuple[int, int]:
        if source.location.suffix.lower() == ".csv":
            dataframe = pd.read_csv(source.location, header=[0, 1, 2], index_col=0)
        else:
            dataframe = pd.read_hdf(source.location)

        bodyparts = dataframe.columns.get_level_values("bodyparts").unique()
        if "individuals" in dataframe.columns.names:
            subject_count = len(dataframe.columns.get_level_values("individuals").unique())
        else:
            subject_count = 1
        return len(bodyparts), subject_count
