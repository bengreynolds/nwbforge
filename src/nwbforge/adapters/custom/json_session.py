"""Custom JSON adapter for the first direct custom-path workflow."""

from __future__ import annotations

import json
from pathlib import Path

from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.domain.enums import ConversionPathway, IssueSeverity, SourceType
from nwbforge.domain.models import ExtractedField, ExtractionResult, ReviewIssue, SourceReference


class CustomJsonSessionAdapter:
    """Read a lab-defined custom session JSON source into extracted fields."""

    adapter_id = "custom_json_session"
    display_name = "Custom JSON session adapter"
    version = "0.1.0"
    source_types = (SourceType.FILE, SourceType.DIRECTORY)
    capabilities = AdapterCapabilities(
        supported_pathways=(ConversionPathway.CUSTOM, ConversionPathway.HYBRID),
        supports_multi_source_sessions=False,
    )

    def can_handle(self, source: SourceReference) -> bool:
        if source.source_type == SourceType.FILE:
            return source.location.name.lower() == "custom_session.json"
        if source.source_type == SourceType.DIRECTORY:
            return (source.location / "custom_session.json").exists()
        return False

    def inspect(self, source: SourceReference) -> ExtractionResult:
        payload_path = self._payload_path(source)
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        fields: dict[str, ExtractedField] = {}
        issues: list[ReviewIssue] = []

        for key, value in self._flatten_payload(payload).items():
            fields[key] = ExtractedField(
                key=key,
                value=value,
                source_id=source.source_id,
                path=key,
            )

        if "recording_context" not in payload:
            issues.append(
                ReviewIssue(
                    code="custom-json-missing-recording-context",
                    message="Custom session JSON is missing the top-level 'recording_context' block.",
                    severity=IssueSeverity.WARNING,
                    field="recording_context",
                    source_ids=(source.source_id,),
                )
            )

        if "signal_sets" not in payload:
            issues.append(
                ReviewIssue(
                    code="custom-json-missing-signal-sets",
                    message="Custom session JSON is missing 'signal_sets'; no acquisition streams were extracted.",
                    severity=IssueSeverity.WARNING,
                    field="signal_sets",
                    source_ids=(source.source_id,),
                )
            )

        return ExtractionResult(
            source_id=source.source_id,
            adapter_id=self.adapter_id,
            record_type="custom_json_session",
            fields=fields,
            issues=tuple(issues),
            notes=(f"Loaded custom session JSON from {payload_path.name}.",),
        )

    @staticmethod
    def _payload_path(source: SourceReference) -> Path:
        if source.source_type == SourceType.FILE:
            return source.location
        return source.location / "custom_session.json"

    @classmethod
    def _flatten_payload(cls, payload: dict[str, object]) -> dict[str, object]:
        fields: dict[str, object] = {}

        for key in ("recording_context", "animal_profile", "annotations", "analysis_context"):
            value = payload.get(key)
            if isinstance(value, dict):
                cls._collect_nested_fields(fields, prefix=key, value=value)

        equipment = payload.get("equipment")
        if isinstance(equipment, list):
            for index, device in enumerate(equipment):
                if not isinstance(device, dict):
                    continue
                device_key = str(device.get("device_key", index))
                cls._emit_record_fields(fields, f"devices.{device_key}", device)

        signal_sets = payload.get("signal_sets")
        if isinstance(signal_sets, list):
            for index, signal_set in enumerate(signal_sets):
                if not isinstance(signal_set, dict):
                    continue
                stream_key = str(signal_set.get("stream_key", index))
                cls._emit_record_fields(fields, f"acquisition_streams.{stream_key}", signal_set)

        return fields

    @classmethod
    def _collect_nested_fields(cls, fields: dict[str, object], prefix: str, value: dict[str, object]) -> None:
        for nested_key, nested_value in value.items():
            field_key = f"{prefix}.{nested_key}"
            if isinstance(nested_value, dict):
                cls._collect_nested_fields(fields, field_key, nested_value)
                continue
            fields[field_key] = nested_value

    @staticmethod
    def _emit_record_fields(fields: dict[str, object], prefix: str, record: dict[str, object]) -> None:
        for field_name, value in record.items():
            normalized_name = field_name.strip().lower().replace("-", "_")
            if normalized_name in {"device_key", "stream_key"}:
                continue
            fields[f"{prefix}.{normalized_name}"] = value
