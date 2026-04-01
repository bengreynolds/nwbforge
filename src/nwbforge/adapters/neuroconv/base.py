"""Shared base classes for NeuroConv-backed source adapters."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pynwb import NWBFile

from nwbforge.adapters.neuroconv.models import NeuroConvSourceConfig
from nwbforge.adapters.neuroconv.metadata import merge_neuroconv_metadata
from nwbforge.domain.models import (
    ConversionSession,
    ExtractionResult,
    ProvenanceArtifact,
    ReviewIssue,
    SourceReference,
)


class NeuroConvInterfaceAdapter(ABC):
    """Base class for supported adapters backed by one NeuroConv DataInterface."""

    interface_cls: type
    record_type: str
    source_path_kwarg = "file_path"
    supported_suffixes: tuple[str, ...] = ()

    def can_handle(self, source: SourceReference) -> bool:
        if source.source_type not in self.source_types:
            return False
        if self.supported_suffixes and source.location.suffix.lower() not in self.supported_suffixes:
            return False
        try:
            config = self.build_source_config(source)
        except ValueError:
            return False
        return self.matches_source(source, config)

    def inspect(self, source: SourceReference) -> ExtractionResult:
        config = self.build_source_config(source)
        interface = self.build_interface(source, config)
        fields, issues, notes = self.extract(source=source, interface=interface, config=config)
        return ExtractionResult(
            source_id=source.source_id,
            adapter_id=self.adapter_id,
            record_type=self.record_type,
            fields=fields,
            issues=tuple(issues),
            notes=self.base_notes(source=source, config=config) + tuple(notes),
        )

    def build_source_config(self, source: SourceReference) -> NeuroConvSourceConfig:
        """Parse source-local NeuroConv configuration from ``SourceReference.metadata``."""

        return NeuroConvSourceConfig(
            interface_kwargs=self._json_dict(source, "neuroconv.interface_kwargs_json"),
            read_kwargs=self._json_dict(source, "neuroconv.read_kwargs_json"),
            metadata_overrides=self._json_dict(source, "neuroconv.metadata_overrides_json"),
            column_name_mapping=self._json_str_dict(source, "neuroconv.column_name_mapping_json"),
            column_descriptions=self._json_str_dict(source, "neuroconv.column_descriptions_json"),
            conversion_options=self._json_dict(source, "neuroconv.conversion_options_json"),
        )

    def build_interface(self, source: SourceReference, config: NeuroConvSourceConfig):
        """Instantiate the NeuroConv interface for the supplied source."""

        interface_kwargs = {self.source_path_kwarg: source.location}
        interface_kwargs.update(config.interface_kwargs)
        if config.read_kwargs:
            interface_kwargs.setdefault("read_kwargs", config.read_kwargs)
        interface_kwargs.setdefault("verbose", False)
        return self.interface_cls(**interface_kwargs)

    def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
        """Subclass hook for source-specific sniffing beyond suffix/type checks."""

        return True

    def base_notes(
        self,
        *,
        source: SourceReference,
        config: NeuroConvSourceConfig,
    ) -> tuple[str, ...]:
        notes = [f"Inspected with NeuroConv {self.interface_cls.__name__} from {source.location.name}."]
        if config.read_kwargs:
            notes.append("Applied NeuroConv read kwargs from source metadata.")
        if config.metadata_overrides:
            notes.append("Source metadata includes NeuroConv metadata overrides for downstream conversion.")
        return tuple(notes)

    @abstractmethod
    def extract(
        self,
        *,
        source: SourceReference,
        interface,
        config: NeuroConvSourceConfig,
    ) -> tuple[dict[str, Any], tuple[ReviewIssue, ...] | list[ReviewIssue], tuple[str, ...]]:
        """Extract stable fields, issues, and additional notes from a NeuroConv interface."""

    @staticmethod
    def _json_dict(source: SourceReference, key: str) -> dict[str, object]:
        value = source.metadata.get(key)
        if value is None:
            return {}
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Source metadata key '{key}' must contain valid JSON.") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"Source metadata key '{key}' must decode to a JSON object.")
        return parsed

    @staticmethod
    def _json_str_dict(source: SourceReference, key: str) -> dict[str, str]:
        parsed = NeuroConvInterfaceAdapter._json_dict(source, key)
        return {str(inner_key): str(inner_value) for inner_key, inner_value in parsed.items()}


class NeuroConvDirectConversionAdapter(NeuroConvInterfaceAdapter):
    """Base class for supported routes that write NWB via NeuroConv directly."""

    writes_time_interval_tables = False
    writes_acquisition_streams = False

    def build_conversion_metadata(self, source: SourceReference, config: NeuroConvSourceConfig) -> dict[str, object]:
        interface = self.build_interface(source, config)
        metadata = interface.get_metadata()
        if config.metadata_overrides:
            metadata = merge_neuroconv_metadata(metadata, config.metadata_overrides)
        return metadata

    def write_conversion(
        self,
        *,
        session: ConversionSession,
        source: SourceReference,
        output_path: str,
        nwbfile: NWBFile,
    ) -> tuple[ProvenanceArtifact, ...]:
        del session
        config = self.build_source_config(source)
        interface = self.build_interface(source, config)
        metadata = interface.get_metadata()
        if config.metadata_overrides:
            metadata = merge_neuroconv_metadata(metadata, config.metadata_overrides)

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        interface.run_conversion(
            nwbfile_path=output_file,
            nwbfile=nwbfile,
            metadata=metadata,
            overwrite=True,
            **config.conversion_options,
        )
        return (
            ProvenanceArtifact(
                artifact_type="nwb",
                location=output_file,
                description=f"NWB file written through NeuroConv adapter '{self.adapter_id}'.",
            ),
        )
