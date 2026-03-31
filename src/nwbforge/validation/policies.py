"""Validation policies for generated conversion artifacts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValidationPolicy:
    require_nwb_output: bool = True
    allowed_nwb_suffixes: tuple[str, ...] = (".nwb",)
    require_existing_files: bool = True
    reject_empty_files: bool = True
