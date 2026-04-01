"""NeuroConv-backed adapters for audio sources."""

from __future__ import annotations

import ndx_sound  # noqa: F401
import scipy  # noqa: F401

from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.adapters.neuroconv import (
    NeuroConvDirectConversionAdapter,
    NeuroConvSourceConfig,
    extracted_fields_from_mapping,
)
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ExtractedField, ReviewIssue, SourceReference

from neuroconv.datainterfaces import AudioInterface


class NeuroConvAudioAdapter(NeuroConvDirectConversionAdapter):
    """Inspect and convert audio sources through NeuroConv."""

    adapter_id = "neuroconv_audio"
    display_name = "NeuroConv audio adapter"
    version = "0.1.0"
    interface_cls = AudioInterface
    record_type = "neuroconv_audio"
    source_types = (SourceType.FILE, SourceType.DIRECTORY)
    capabilities = AdapterCapabilities(
        supported_pathways=(ConversionPathway.SUPPORTED,),
        supports_multi_source_sessions=True,
    )
    supported_suffixes = (".wav",)

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
            interface_kwargs["file_paths"] = self._audio_files(source)
        return self.interface_cls(**interface_kwargs)

    def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
        del config
        if source.source_type == SourceType.FILE:
            return source.location.suffix.lower() in self.supported_suffixes
        try:
            return len(self._audio_files(source)) > 0
        except OSError:
            return False

    def extract(
        self,
        *,
        source: SourceReference,
        interface,
        config: NeuroConvSourceConfig,
    ) -> tuple[dict[str, ExtractedField], list[ReviewIssue], tuple[str, ...]]:
        del interface, config
        file_count = 1 if source.source_type == SourceType.FILE else len(self._audio_files(source))
        fields = extracted_fields_from_mapping(
            prefix="audio",
            payload={
                "count": file_count,
                "source_kind": source.source_type.value,
            },
            source_id=source.source_id,
        )
        notes = (f"Prepared NeuroConv audio conversion with {file_count} audio file(s).",)
        return fields, [], notes

    def _audio_files(self, source: SourceReference) -> list:
        return sorted(
            [
                path
                for path in source.location.iterdir()
                if path.is_file() and path.suffix.lower() in self.supported_suffixes
            ]
        )
