"""Shared models for NeuroConv-backed adapters."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class NeuroConvSourceConfig:
    """Parsed per-source settings for a NeuroConv-backed adapter."""

    interface_kwargs: dict[str, object] = field(default_factory=dict)
    read_kwargs: dict[str, object] = field(default_factory=dict)
    metadata_overrides: dict[str, object] = field(default_factory=dict)
    column_name_mapping: dict[str, str] = field(default_factory=dict)
    column_descriptions: dict[str, str] = field(default_factory=dict)
    conversion_options: dict[str, object] = field(default_factory=dict)
