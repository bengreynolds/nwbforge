"""Shared extraction helpers for NeuroConv-backed adapters."""

from __future__ import annotations

from collections.abc import Mapping
from math import isnan

from nwbforge.domain.models import ExtractedField


def coerce_neuroconv_value(value: object) -> object:
    """Convert pandas/numpy scalar values into plain Python values."""

    coerced = value.item() if hasattr(value, "item") else value
    if isinstance(coerced, float) and isnan(coerced):
        return None
    return coerced


def extracted_fields_from_mapping(
    *,
    prefix: str,
    payload: Mapping[str, object],
    source_id: str,
) -> dict[str, ExtractedField]:
    """Flatten a mapping into extracted fields under a stable prefix."""

    fields: dict[str, ExtractedField] = {}
    for key, value in payload.items():
        field_key = f"{prefix}.{key}"
        fields[field_key] = ExtractedField(
            key=field_key,
            value=coerce_neuroconv_value(value),
            source_id=source_id,
            path=field_key,
        )
    return fields


def extracted_fields_from_dataframe(
    *,
    prefix: str,
    dataframe,
    source_id: str,
) -> dict[str, ExtractedField]:
    """Flatten a tabular object with ``iterrows()`` into row-addressable fields."""

    fields: dict[str, ExtractedField] = {}
    normalized_frame = dataframe.where(dataframe.notna(), None)
    for row_index, row in normalized_frame.iterrows():
        for column_name, value in row.to_dict().items():
            field_key = f"{prefix}.{row_index}.{column_name}"
            fields[field_key] = ExtractedField(
                key=field_key,
                value=coerce_neuroconv_value(value),
                source_id=source_id,
                path=field_key,
            )
    return fields
