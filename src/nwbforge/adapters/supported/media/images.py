"""NeuroConv-backed adapters for still-image sources."""

from __future__ import annotations

from neuroconv.datainterfaces import ImageInterface

from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.adapters.neuroconv import (
    NeuroConvDirectConversionAdapter,
    NeuroConvSourceConfig,
    extracted_fields_from_mapping,
)
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ExtractedField, ReviewIssue, SourceReference


class NeuroConvImageAdapter(NeuroConvDirectConversionAdapter):
    """Inspect and convert still-image sources through NeuroConv."""

    adapter_id = "neuroconv_image"
    display_name = "NeuroConv image adapter"
    version = "0.1.0"
    interface_cls = ImageInterface
    record_type = "neuroconv_image"
    source_types = (SourceType.FILE, SourceType.DIRECTORY)
    capabilities = AdapterCapabilities(
        supported_pathways=(ConversionPathway.SUPPORTED,),
        supports_multi_source_sessions=True,
    )
    supported_suffixes = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif")

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
            interface_kwargs["folder_path"] = source.location
        return self.interface_cls(**interface_kwargs)

    def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
        del config
        if source.source_type == SourceType.FILE:
            return source.location.suffix.lower() in self.supported_suffixes
        try:
            return any(
                path.is_file() and path.suffix.lower() in self.supported_suffixes
                for path in source.location.iterdir()
            )
        except OSError:
            return False

    def extract(
        self,
        *,
        source: SourceReference,
        interface,
        config: NeuroConvSourceConfig,
    ) -> tuple[dict[str, ExtractedField], list[ReviewIssue], tuple[str, ...]]:
        del interface
        images_location = str(config.interface_kwargs.get("images_location", "acquisition"))
        image_count = self._image_count(source)
        fields = extracted_fields_from_mapping(
            prefix="images",
            payload={
                "count": image_count,
                "images_location": images_location,
                "source_kind": source.source_type.value,
            },
            source_id=source.source_id,
        )
        notes = (f"Prepared NeuroConv image conversion with {image_count} image source(s).",)
        return fields, [], notes

    def _image_count(self, source: SourceReference) -> int:
        if source.source_type == SourceType.FILE:
            return 1
        return sum(
            1
            for path in source.location.iterdir()
            if path.is_file() and path.suffix.lower() in self.supported_suffixes
        )
