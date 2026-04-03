"""NeuroConv-backed adapters for external video sources."""

from __future__ import annotations

try:
    from neuroconv.datainterfaces import ExternalVideoInterface
except ImportError:  # pragma: no cover - optional route dependency gate
    ExternalVideoInterface = None

from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.adapters.neuroconv import (
    NeuroConvDirectConversionAdapter,
    NeuroConvSourceConfig,
    extracted_fields_from_mapping,
)
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ExtractedField, ReviewIssue, SourceReference


if ExternalVideoInterface is not None:

    class NeuroConvVideoAdapter(NeuroConvDirectConversionAdapter):
        """Inspect and convert external video sources through NeuroConv."""

        adapter_id = "neuroconv_video"
        display_name = "NeuroConv video adapter"
        version = "0.1.0"
        interface_cls = ExternalVideoInterface
        record_type = "neuroconv_video"
        source_types = (SourceType.FILE, SourceType.DIRECTORY)
        capabilities = AdapterCapabilities(
            supported_pathways=(ConversionPathway.SUPPORTED,),
            supports_multi_source_sessions=True,
        )
        supported_suffixes = (".mp4", ".avi", ".wmv", ".mov", ".flv", ".mkv")

        def can_handle(self, source: SourceReference) -> bool:
            if source.source_type not in self.source_types:
                return False
            try:
                config = self.build_source_config(source)
            except ValueError:
                return False
            return self.matches_source(source, config)

        def build_interface(self, source: SourceReference, config: NeuroConvSourceConfig):
            interface_kwargs = dict(config.interface_kwargs)
            interface_kwargs.setdefault("verbose", False)
            if source.source_type == SourceType.FILE:
                interface_kwargs["file_paths"] = [source.location]
            else:
                interface_kwargs["file_paths"] = self._video_files(source)
            return self.interface_cls(**interface_kwargs)

        def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
            del config
            if source.source_type == SourceType.FILE:
                return source.location.suffix.lower() in self.supported_suffixes
            try:
                return len(self._video_files(source)) > 0
            except OSError:
                return False

        def extract(
            self,
            *,
            source: SourceReference,
            interface,
            config: NeuroConvSourceConfig,
        ) -> tuple[dict[str, ExtractedField], list[ReviewIssue], tuple[str, ...]]:
            metadata = interface.get_metadata()
            behavior_metadata = metadata.get("Behavior", {}).get("ExternalVideos", {})
            file_count = 1 if source.source_type == SourceType.FILE else len(self._video_files(source))
            video_names = tuple(str(name) for name in behavior_metadata.keys())
            fields = extracted_fields_from_mapping(
                prefix="video",
                payload={
                    "count": file_count,
                    "source_kind": source.source_type.value,
                    "video_name": config.interface_kwargs.get("video_name") or (
                        video_names[0] if video_names else f"Video {source.location.stem}"
                    ),
                    "has_external_video_metadata": bool(behavior_metadata),
                },
                source_id=source.source_id,
            )
            notes = (f"Prepared NeuroConv video conversion with {file_count} external video file(s).",)
            return fields, [], notes

        def _video_files(self, source: SourceReference) -> list:
            return sorted(
                path
                for path in source.location.iterdir()
                if path.is_file() and path.suffix.lower() in self.supported_suffixes
            )
