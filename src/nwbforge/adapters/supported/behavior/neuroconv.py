"""NeuroConv-backed adapters for supported behavior routes."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from neuroconv.datainterfaces import DeepLabCutInterface, FicTracDataInterface

try:
    from neuroconv.datainterfaces import LightningPoseDataInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    LightningPoseDataInterface = None

try:
    from neuroconv.datainterfaces import MedPCInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    MedPCInterface = None

try:
    from neuroconv.datainterfaces import NeuralynxNvtInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    NeuralynxNvtInterface = None

try:
    from neuroconv.datainterfaces import SLEAPInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    SLEAPInterface = None

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


if LightningPoseDataInterface is not None:

    class NeuroConvLightningPoseAdapter(NeuroConvDirectConversionAdapter):
        """Inspect and convert LightningPose output files through NeuroConv."""

        adapter_id = "neuroconv_lightningpose"
        display_name = "NeuroConv LightningPose adapter"
        version = "0.1.0"
        interface_cls = LightningPoseDataInterface
        record_type = "neuroconv_lightningpose"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".csv",)

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            return source.location.suffix.lower() in self.supported_suffixes and self._resolve_original_video_path(
                source, config
            ) is not None

        def build_interface(self, source: SourceReference, config: NeuroConvSourceConfig):
            interface_kwargs = {self.source_path_kwarg: source.location}
            interface_kwargs.update(config.interface_kwargs)
            original_video_file_path = self._resolve_original_video_path(source, config)
            if original_video_file_path is None:
                raise ValueError(
                    "LightningPose conversion requires original_video_file_path or a same-stem .mp4 sidecar."
                )
            interface_kwargs["original_video_file_path"] = original_video_file_path
            if "labeled_video_file_path" not in interface_kwargs:
                labeled_candidate = source.location.with_name(f"{source.location.stem}.labeled.mp4")
                if labeled_candidate.is_file():
                    interface_kwargs["labeled_video_file_path"] = labeled_candidate
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
            pose_metadata = metadata.get("Behavior", {}).get("PoseEstimation", {})
            keypoint_count = self._keypoint_count_from_source(source.location)
            original_video_file_path = self._resolve_original_video_path(source, config)
            labeled_video_file_path = self._resolve_labeled_video_path(source, config)
            fields = extracted_fields_from_mapping(
                prefix="behavior.lightningpose",
                payload={
                    "source_format": "csv",
                    "keypoint_count": keypoint_count,
                    "pose_container_name": pose_metadata.get("name", "PoseEstimation"),
                    "camera_name": pose_metadata.get("camera_name", "CameraPoseEstimation"),
                    "has_original_video": original_video_file_path is not None,
                    "has_labeled_video": labeled_video_file_path is not None,
                },
                source_id=source.source_id,
            )
            notes = (
                "Prepared NeuroConv LightningPose conversion into pose-estimation processing data.",
                "LightningPose requires an original video sidecar or explicit original_video_file_path.",
            )
            return fields, [], notes

        @staticmethod
        def _keypoint_count_from_source(location: Path) -> int:
            dataframe = pd.read_csv(location, header=[0, 1, 2])
            scorer_name = next(
                name
                for name in dataframe.columns.get_level_values(0).unique()
                if not str(name).startswith("Unnamed")
            )
            keypoints = dataframe[scorer_name].columns.get_level_values(0).unique()
            return len(keypoints)

        @staticmethod
        def _resolve_original_video_path(source: SourceReference, config: NeuroConvSourceConfig) -> Path | None:
            configured_path = config.interface_kwargs.get("original_video_file_path")
            if configured_path:
                return Path(configured_path)
            candidate = source.location.with_suffix(".mp4")
            if candidate.is_file():
                return candidate
            return None

        @staticmethod
        def _resolve_labeled_video_path(source: SourceReference, config: NeuroConvSourceConfig) -> Path | None:
            configured_path = config.interface_kwargs.get("labeled_video_file_path")
            if configured_path:
                return Path(configured_path)
            candidate = source.location.with_name(f"{source.location.stem}.labeled.mp4")
            if candidate.is_file():
                return candidate
            return None


if MedPCInterface is not None:

    class NeuroConvMedPCAdapter(NeuroConvDirectConversionAdapter):
        """Inspect and convert MedPC task output files through NeuroConv."""

        adapter_id = "neuroconv_medpc"
        display_name = "NeuroConv MedPC adapter"
        version = "0.1.0"
        interface_cls = MedPCInterface
        record_type = "neuroconv_medpc"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".txt",)

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            return source.location.suffix.lower() in self.supported_suffixes and self._has_required_config(config)

        def build_interface(self, source: SourceReference, config: NeuroConvSourceConfig):
            if not self._has_required_config(config):
                raise ValueError(
                    "MedPC conversion requires session_conditions, start_variable, and "
                    "metadata_medpc_name_to_info_dict in neuroconv.interface_kwargs_json."
                )
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
            medpc_metadata = metadata.get("MedPC", {})
            metadata_mapping = config.interface_kwargs.get("metadata_medpc_name_to_info_dict", {})
            aligned_timestamp_names = tuple(config.interface_kwargs.get("aligned_timestamp_names", ()))
            fields = extracted_fields_from_mapping(
                prefix="behavior.medpc",
                payload={
                    "source_format": "txt",
                    "mapped_variable_count": len(metadata_mapping),
                    "aligned_timestamp_count": len(aligned_timestamp_names),
                    "start_variable": config.interface_kwargs.get("start_variable"),
                    "has_session_conditions": bool(config.interface_kwargs.get("session_conditions")),
                    "metadata_key_count": len(medpc_metadata),
                },
                source_id=source.source_id,
            )
            notes = (
                "Prepared NeuroConv MedPC conversion into behavior events and intervals.",
                "MedPC route matching is configuration-driven and requires explicit session selection metadata.",
            )
            return fields, [], notes

        @staticmethod
        def _has_required_config(config: NeuroConvSourceConfig) -> bool:
            interface_kwargs = config.interface_kwargs
            return all(
                key in interface_kwargs
                for key in ("session_conditions", "start_variable", "metadata_medpc_name_to_info_dict")
            )


if SLEAPInterface is not None:

    class NeuroConvSLEAPAdapter(NeuroConvDirectConversionAdapter):
        """Inspect and convert SLEAP `.slp` sources through NeuroConv."""

        adapter_id = "neuroconv_sleap"
        display_name = "NeuroConv SLEAP adapter"
        version = "0.1.0"
        interface_cls = SLEAPInterface
        record_type = "neuroconv_sleap"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".slp",)

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            return source.location.suffix.lower() in self.supported_suffixes

        def build_interface(self, source: SourceReference, config: NeuroConvSourceConfig):
            interface_kwargs = {self.source_path_kwarg: source.location}
            interface_kwargs.update(config.interface_kwargs)
            if "video_file_path" not in interface_kwargs:
                candidate = source.location.with_suffix(".mp4")
                if candidate.is_file():
                    interface_kwargs["video_file_path"] = candidate
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
            pose_metadata = metadata.get("PoseEstimation", {}).get("PoseEstimationContainers", {})
            pose_names = tuple(str(name) for name in pose_metadata.keys())
            has_video_file = str(config.interface_kwargs.get("video_file_path", "")) != "" or source.location.with_suffix(
                ".mp4"
            ).is_file()
            fields = extracted_fields_from_mapping(
                prefix="behavior.sleap",
                payload={
                    "source_format": "slp",
                    "pose_container_count": len(pose_names),
                    "pose_container_name": pose_names[0] if pose_names else "PoseEstimation",
                    "has_video_file": has_video_file,
                    "frames_per_second": config.interface_kwargs.get("frames_per_second"),
                },
                source_id=source.source_id,
            )
            notes = ("Prepared NeuroConv SLEAP conversion into pose-estimation processing data.",)
            return fields, [], notes


if NeuralynxNvtInterface is not None:

    class NeuroConvNeuralynxNvtAdapter(NeuroConvDirectConversionAdapter):
        """Inspect and convert Neuralynx NVT position-tracking files through NeuroConv."""

        adapter_id = "neuroconv_neuralynx_nvt"
        display_name = "NeuroConv Neuralynx NVT adapter"
        version = "0.1.0"
        interface_cls = NeuralynxNvtInterface
        record_type = "neuroconv_neuralynx_nvt"
        source_types = (SourceType.FILE,)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".nvt",)

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
            del config
            metadata = interface.get_metadata()
            behavior_metadata = metadata.get("Behavior", {})
            container_name = next(iter(behavior_metadata.keys()), source.location.name)
            fields = extracted_fields_from_mapping(
                prefix="behavior.neuralynx_nvt",
                payload={
                    "source_format": "nvt",
                    "container_name": container_name,
                    "has_session_start_time": "session_start_time" in metadata.get("NWBFile", {}),
                    "writes_position": True,
                    "writes_angle": True,
                },
                source_id=source.source_id,
            )
            notes = (
                "Prepared NeuroConv Neuralynx NVT conversion into behavior position tracking data.",
                "Neuralynx NVT support shares the Neuralynx install gate but stays distinct from Neuralynx ecephys folder ingestion.",
            )
            return fields, [], notes
