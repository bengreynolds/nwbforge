"""A structured manifest adapter used as the first end-to-end pilot source."""

from __future__ import annotations

import json
from pathlib import Path

from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.domain.enums import ConversionPathway, IssueSeverity, SourceType
from nwbforge.domain.models import ExtractedField, ExtractionResult, ReviewIssue, SourceReference


class SessionManifestAdapter:
    """Read a structured JSON session manifest into extracted fields."""

    adapter_id = "session_manifest"
    display_name = "Session manifest adapter"
    version = "0.1.0"
    source_types = (SourceType.FILE, SourceType.DIRECTORY)
    capabilities = AdapterCapabilities(
        supported_pathways=(ConversionPathway.SUPPORTED,),
        supports_multi_source_sessions=False,
    )

    def can_handle(self, source: SourceReference) -> bool:
        if source.source_type == SourceType.FILE:
            return source.location.name.lower() == "session_manifest.json"
        if source.source_type == SourceType.DIRECTORY:
            return (source.location / "session_manifest.json").exists()
        return False

    def inspect(self, source: SourceReference) -> ExtractionResult:
        manifest_path = self._manifest_path(source)
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        fields: dict[str, ExtractedField] = {}
        issues: list[ReviewIssue] = []

        for field_key, value in self._flatten_payload(payload).items():
            fields[field_key] = ExtractedField(
                key=field_key,
                value=value,
                source_id=source.source_id,
                path=field_key,
            )

        if "session" not in payload:
            issues.append(
                ReviewIssue(
                    code="manifest-missing-session-block",
                    message="Manifest did not include a top-level 'session' block.",
                    severity=IssueSeverity.WARNING,
                    field="session",
                    source_ids=(source.source_id,),
                )
            )

        return ExtractionResult(
            source_id=source.source_id,
            adapter_id=self.adapter_id,
            record_type="session_manifest",
            fields=fields,
            issues=tuple(issues),
            notes=(f"Loaded manifest from {manifest_path.name}.",),
        )

    @staticmethod
    def _manifest_path(source: SourceReference) -> Path:
        if source.source_type == SourceType.FILE:
            return source.location
        return source.location / "session_manifest.json"

    @classmethod
    def _flatten_payload(cls, payload: dict[str, object]) -> dict[str, object]:
        fields: dict[str, object] = {}
        for key, value in payload.items():
            cls._collect_fields(fields, prefix=key, value=value)
        return fields

    @classmethod
    def _collect_fields(cls, fields: dict[str, object], prefix: str, value: object) -> None:
        if isinstance(value, dict):
            for nested_key, nested_value in value.items():
                cls._collect_fields(fields, prefix=f"{prefix}.{nested_key}", value=nested_value)
            return

        if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
            for index, nested_value in enumerate(value):
                cls._collect_fields(fields, prefix=f"{prefix}.{index}", value=nested_value)
            return

        fields[prefix] = value
