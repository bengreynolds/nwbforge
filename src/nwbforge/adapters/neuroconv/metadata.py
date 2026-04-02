"""Helpers for building NeuroConv metadata payloads."""

from __future__ import annotations

from copy import deepcopy


def merge_neuroconv_metadata(base: dict[str, object], updates: dict[str, object]) -> dict[str, object]:
    """Recursively merge metadata dictionaries without mutating the inputs."""

    merged = deepcopy(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_neuroconv_metadata(merged[key], value)
            continue
        merged[key] = deepcopy(value)
    return merged
