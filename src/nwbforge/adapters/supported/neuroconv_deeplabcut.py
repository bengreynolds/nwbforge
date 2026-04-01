"""NeuroConv-backed adapters for DeepLabCut pose-estimation sources."""

from __future__ import annotations

import pandas as pd
from neuroconv.datainterfaces import DeepLabCutInterface

from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.adapters.neuroconv import (
    NeuroConvDirectConversionAdapter,
    NeuroConvSourceConfig,
    extracted_fields_from_mapping,
)
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ExtractedField, ReviewIssue, SourceReference


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
