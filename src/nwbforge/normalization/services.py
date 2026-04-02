"""Concrete normalization services."""

from __future__ import annotations

import re
from dataclasses import replace

from nwbforge.domain.contracts import NormalizationService
from nwbforge.domain.enums import ReviewStatus, ValueOrigin
from nwbforge.domain.models import (
    AcquisitionStream,
    ConversionSession,
    ExtractedField,
    ExtractionResult,
    NormalizedMetadataBundle,
    NormalizedDevice,
    NormalizedSessionMetadata,
    NormalizedSubject,
    NormalizedTimeIntervalTable,
    NormalizedValue,
    TimeIntervalRow,
)
from nwbforge.normalization.rules import DEFAULT_FIELD_ALIASES, NormalizationRuleSet


class RuleBasedNormalizationService(NormalizationService):
    """Normalize extracted fields with a conservative alias-driven rule set."""

    _SOURCE_ROLE_PRIORITY = {
        "primary": 3,
        "metadata": 2,
        "supplemental": 1,
    }
    _DEVICE_FIELD_PATTERN = re.compile(r"^devices\.(?P<device_key>[^.]+)\.(?P<field_name>[^.]+)$")
    _STREAM_FIELD_PATTERN = re.compile(
        r"^acquisition_streams\.(?P<stream_key>[^.]+)\.(?P<field_name>[^.]+)$"
    )
    _TIME_INTERVAL_TABLE_FIELD_PATTERN = re.compile(
        r"^time_intervals\.(?P<table_key>[^.]+)\.(?P<field_name>table_name|table_description)$"
    )
    _TIME_INTERVAL_ROW_FIELD_PATTERN = re.compile(
        r"^time_intervals\.(?P<table_key>[^.]+)\.rows\.(?P<row_key>[^.]+)\.(?P<field_name>[^.]+)$"
    )

    def __init__(self, rules: NormalizationRuleSet | None = None) -> None:
        self._rules = rules or NormalizationRuleSet(field_aliases=DEFAULT_FIELD_ALIASES)

    def normalize(
        self,
        session: ConversionSession,
        extraction_results: tuple[ExtractionResult, ...],
    ) -> NormalizedMetadataBundle:
        source_roles = {source.source_id: source.role for source in session.sources}
        subject = NormalizedSubject()
        session_metadata = NormalizedSessionMetadata()
        devices: dict[str, NormalizedDevice] = {}
        acquisition_streams: dict[str, AcquisitionStream] = {}
        time_interval_tables: dict[str, NormalizedTimeIntervalTable] = {}
        additional_metadata: dict[str, NormalizedValue[object]] = {}

        for result in extraction_results:
            for extracted_field in result.fields.values():
                device_match = self._DEVICE_FIELD_PATTERN.match(extracted_field.key)
                if device_match is not None:
                    device_key = device_match.group("device_key")
                    field_name = device_match.group("field_name")
                    devices[device_key] = self._assign_device(
                        devices.get(device_key),
                        device_key=device_key,
                        field_name=field_name,
                        extracted_field=extracted_field,
                        source_roles=source_roles,
                    )
                    continue

                stream_match = self._STREAM_FIELD_PATTERN.match(extracted_field.key)
                if stream_match is not None:
                    stream_key = stream_match.group("stream_key")
                    field_name = stream_match.group("field_name")
                    acquisition_streams[stream_key] = self._assign_acquisition_stream(
                        acquisition_streams.get(stream_key),
                        stream_key=stream_key,
                        field_name=field_name,
                        extracted_field=extracted_field,
                        source_roles=source_roles,
                    )
                    continue

                time_interval_table_match = self._TIME_INTERVAL_TABLE_FIELD_PATTERN.match(extracted_field.key)
                if time_interval_table_match is not None:
                    table_key = time_interval_table_match.group("table_key")
                    field_name = time_interval_table_match.group("field_name")
                    time_interval_tables[table_key] = self._assign_time_interval_table(
                        time_interval_tables.get(table_key),
                        table_key=table_key,
                        field_name=field_name,
                        extracted_field=extracted_field,
                        source_roles=source_roles,
                    )
                    continue

                time_interval_row_match = self._TIME_INTERVAL_ROW_FIELD_PATTERN.match(extracted_field.key)
                if time_interval_row_match is not None:
                    table_key = time_interval_row_match.group("table_key")
                    row_key = time_interval_row_match.group("row_key")
                    field_name = time_interval_row_match.group("field_name")
                    time_interval_tables[table_key] = self._assign_time_interval_row(
                        time_interval_tables.get(table_key),
                        table_key=table_key,
                        row_key=row_key,
                        field_name=field_name,
                        extracted_field=extracted_field,
                        source_roles=source_roles,
                    )
                    continue

                canonical_key = self._rules.canonical_key_for(extracted_field.key)
                if canonical_key is None:
                    additional_metadata[extracted_field.key] = self._to_value(
                        extracted_field,
                        review_status=ReviewStatus.NEEDS_REVIEW,
                        notes=("No normalization rule matched this field.",),
                    )
                    continue

                if canonical_key.startswith("subject."):
                    field_name = canonical_key.removeprefix("subject.")
                    subject = self._assign_subject(subject, field_name, extracted_field, source_roles=source_roles)
                    continue

                if canonical_key.startswith("session."):
                    field_name = canonical_key.removeprefix("session.")
                    session_metadata = self._assign_session(
                        session_metadata,
                        field_name,
                        extracted_field,
                        source_roles=source_roles,
                    )
                    continue

        if session_metadata.session_id is None:
            session_metadata = replace(
                session_metadata,
                session_id=NormalizedValue(
                    value=session.session_id,
                    origin=ValueOrigin.COMPUTED,
                    notes=("Filled from conversion session identifier.",),
                ),
            )

        bundle = NormalizedMetadataBundle(
            subject=subject,
            session=session_metadata,
            devices=tuple(devices[key] for key in sorted(devices)),
            acquisition_streams=tuple(
                acquisition_streams[key] for key in sorted(acquisition_streams)
            ),
            time_interval_tables=tuple(
                time_interval_tables[key] for key in sorted(time_interval_tables)
            ),
            additional_metadata=additional_metadata,
        )
        return self._apply_session_metadata_overrides(session, bundle)

    def _assign_subject(
        self,
        subject: NormalizedSubject,
        field_name: str,
        extracted_field: ExtractedField,
        *,
        source_roles: dict[str, str],
    ) -> NormalizedSubject:
        current_value = getattr(subject, field_name)
        normalized_value = self._merge_value(current_value, extracted_field, source_roles=source_roles)
        return replace(subject, **{field_name: normalized_value})

    def _assign_session(
        self,
        session_metadata: NormalizedSessionMetadata,
        field_name: str,
        extracted_field: ExtractedField,
        *,
        source_roles: dict[str, str],
    ) -> NormalizedSessionMetadata:
        if field_name == "keywords":
            existing_keywords = session_metadata.keywords
            next_keywords = self._normalize_keywords(extracted_field)
            return replace(session_metadata, keywords=existing_keywords + next_keywords)

        current_value = getattr(session_metadata, field_name)
        normalized_value = self._merge_value(current_value, extracted_field, source_roles=source_roles)
        return replace(session_metadata, **{field_name: normalized_value})

    def _assign_device(
        self,
        device: NormalizedDevice | None,
        *,
        device_key: str,
        field_name: str,
        extracted_field: ExtractedField,
        source_roles: dict[str, str],
    ) -> NormalizedDevice:
        normalized_field_name = field_name.strip().lower().replace("-", "_")
        device = device or NormalizedDevice(
            device_id=device_key,
            name=NormalizedValue(
                value=device_key,
                origin=ValueOrigin.COMPUTED,
                source_ids=(extracted_field.source_id,),
                notes=("Filled from manifest device key until a device name is provided.",),
            ),
        )

        if normalized_field_name == "device_id":
            return replace(device, device_id=str(extracted_field.value))
        if normalized_field_name in {"name", "description", "manufacturer"}:
            current_value = getattr(device, normalized_field_name)
            normalized_value = self._merge_value(current_value, extracted_field, source_roles=source_roles)
            return replace(device, **{normalized_field_name: normalized_value})
        if normalized_field_name == "modality":
            modality = str(extracted_field.value)
            return replace(device, modality=modality)

        additional_fields = dict(device.additional_fields)
        additional_fields[normalized_field_name] = self._to_value(
            extracted_field,
            review_status=ReviewStatus.NEEDS_REVIEW,
            notes=("No device normalization rule matched this field.",),
        )
        return replace(device, additional_fields=additional_fields)

    def _assign_acquisition_stream(
        self,
        stream: AcquisitionStream | None,
        *,
        stream_key: str,
        field_name: str,
        extracted_field: ExtractedField,
        source_roles: dict[str, str],
    ) -> AcquisitionStream:
        normalized_field_name = field_name.strip().lower().replace("-", "_")
        stream = stream or AcquisitionStream(
            stream_id=stream_key,
            name=NormalizedValue(
                value=stream_key,
                origin=ValueOrigin.COMPUTED,
                source_ids=(extracted_field.source_id,),
                notes=("Filled from manifest stream key until a stream name is provided.",),
            ),
            modality=None,
            source_ids=(extracted_field.source_id,),
        )
        merged_source_ids = tuple(dict.fromkeys(stream.source_ids + (extracted_field.source_id,)))

        if normalized_field_name == "stream_id":
            return replace(stream, stream_id=str(extracted_field.value), source_ids=merged_source_ids)
        if normalized_field_name == "name":
            normalized_value = self._merge_value(stream.name, extracted_field, source_roles=source_roles)
            return replace(stream, name=normalized_value, source_ids=merged_source_ids)
        if normalized_field_name == "modality":
            return replace(stream, modality=str(extracted_field.value), source_ids=merged_source_ids)
        if normalized_field_name in {"description", "start_time", "end_time"}:
            current_value = getattr(stream, normalized_field_name)
            normalized_value = self._merge_value(current_value, extracted_field, source_roles=source_roles)
            return replace(stream, **{normalized_field_name: normalized_value}, source_ids=merged_source_ids)

        metadata = dict(stream.metadata)
        metadata[normalized_field_name] = self._to_value(extracted_field)
        return replace(stream, metadata=metadata, source_ids=merged_source_ids)

    def _assign_time_interval_table(
        self,
        table: NormalizedTimeIntervalTable | None,
        *,
        table_key: str,
        field_name: str,
        extracted_field: ExtractedField,
        source_roles: dict[str, str],
    ) -> NormalizedTimeIntervalTable:
        table = table or NormalizedTimeIntervalTable(
            table_id=table_key,
            table_name=NormalizedValue(
                value=table_key,
                origin=ValueOrigin.COMPUTED,
                source_ids=(extracted_field.source_id,),
                notes=("Filled from extracted interval table key until a table name is provided.",),
            ),
        )
        if field_name == "table_name":
            return replace(
                table,
                table_name=self._merge_value(table.table_name, extracted_field, source_roles=source_roles),
            )
        if field_name == "table_description":
            return replace(
                table,
                table_description=self._merge_value(
                    table.table_description,
                    extracted_field,
                    source_roles=source_roles,
                ),
            )
        return table

    def _assign_time_interval_row(
        self,
        table: NormalizedTimeIntervalTable | None,
        *,
        table_key: str,
        row_key: str,
        field_name: str,
        extracted_field: ExtractedField,
        source_roles: dict[str, str],
    ) -> NormalizedTimeIntervalTable:
        table = table or NormalizedTimeIntervalTable(
            table_id=table_key,
            table_name=NormalizedValue(
                value=table_key,
                origin=ValueOrigin.COMPUTED,
                source_ids=(extracted_field.source_id,),
                notes=("Filled from extracted interval table key until a table name is provided.",),
            ),
        )
        rows_by_id = {row.row_id: row for row in table.rows}
        row = rows_by_id.get(row_key) or TimeIntervalRow(row_id=row_key, source_ids=(extracted_field.source_id,))
        merged_source_ids = tuple(dict.fromkeys(row.source_ids + (extracted_field.source_id,)))
        normalized_field_name = field_name.strip().lower().replace("-", "_")

        if normalized_field_name == "start_time":
            row = replace(
                row,
                start_time=self._merge_value(row.start_time, extracted_field, source_roles=source_roles),
                source_ids=merged_source_ids,
            )
        elif normalized_field_name == "stop_time":
            row = replace(
                row,
                stop_time=self._merge_value(row.stop_time, extracted_field, source_roles=source_roles),
                source_ids=merged_source_ids,
            )
        else:
            metadata = dict(row.metadata)
            metadata[normalized_field_name] = self._to_value(extracted_field)
            row = replace(row, metadata=metadata, source_ids=merged_source_ids)

        rows_by_id[row_key] = row
        ordered_rows = tuple(self._sort_interval_rows(rows_by_id.values()))
        return replace(table, rows=ordered_rows)

    @staticmethod
    def _sort_interval_rows(rows: list[TimeIntervalRow] | tuple[TimeIntervalRow, ...]):
        def sort_key(row: TimeIntervalRow):
            return (RuleBasedNormalizationService._numeric_or_text_sort_key(row.row_id), row.row_id)

        return sorted(rows, key=sort_key)

    @staticmethod
    def _numeric_or_text_sort_key(value: str) -> tuple[int, int | str]:
        try:
            return (0, int(value))
        except ValueError:
            return (1, value)

    def _merge_value(
        self,
        current_value: NormalizedValue[object] | None,
        extracted_field: ExtractedField,
        *,
        source_roles: dict[str, str],
    ) -> NormalizedValue[object]:
        next_value = self._to_value(extracted_field)
        if current_value is None:
            return next_value
        if current_value.value == next_value.value:
            return replace(
                current_value,
                source_ids=tuple(dict.fromkeys(current_value.source_ids + next_value.source_ids)),
            )
        if current_value.origin is ValueOrigin.COMPUTED and next_value.origin is not ValueOrigin.COMPUTED:
            return next_value

        current_rank = self._source_priority(current_value.source_ids, source_roles)
        next_rank = self._source_priority(next_value.source_ids, source_roles)
        if next_rank >= current_rank:
            retained_value = next_value
            retained_role = self._role_name(next_value.source_ids, source_roles)
            discarded_role = self._role_name(current_value.source_ids, source_roles)
        else:
            retained_value = current_value
            retained_role = self._role_name(current_value.source_ids, source_roles)
            discarded_role = self._role_name(next_value.source_ids, source_roles)

        merged_notes = retained_value.notes + (
            "Multiple extracted fields mapped to the same canonical value.",
            f"Retained value from {retained_role} source over {discarded_role} source.",
            f"Conflicting extracted field: {extracted_field.key}",
        )
        merged_sources = tuple(dict.fromkeys(current_value.source_ids + next_value.source_ids))
        return replace(
            retained_value,
            review_status=ReviewStatus.NEEDS_REVIEW,
            source_ids=merged_sources,
            notes=merged_notes,
        )

    @staticmethod
    def _to_value(
        extracted_field: ExtractedField,
        review_status: ReviewStatus = ReviewStatus.NOT_REVIEWED,
        notes: tuple[str, ...] = (),
    ) -> NormalizedValue[object]:
        return NormalizedValue(
            value=extracted_field.value,
            origin=ValueOrigin.USER_SUPPLIED if extracted_field.is_user_override else ValueOrigin.ADAPTER_EXTRACTED,
            source_ids=(extracted_field.source_id,),
            review_status=review_status,
            notes=notes + extracted_field.notes,
        )

    def _normalize_keywords(self, extracted_field: ExtractedField) -> tuple[NormalizedValue[str], ...]:
        value = extracted_field.value
        if isinstance(value, str):
            raw_keywords = [item.strip() for item in value.replace(";", ",").split(",")]
        elif isinstance(value, (list, tuple, set)):
            raw_keywords = [str(item).strip() for item in value]
        else:
            raw_keywords = [str(value).strip()]

        keywords = []
        for keyword in raw_keywords:
            if not keyword:
                continue
            keywords.append(
                NormalizedValue(
                    value=keyword,
                    origin=ValueOrigin.ADAPTER_EXTRACTED,
                    source_ids=(extracted_field.source_id,),
                )
            )
        return tuple(keywords)

    def _apply_session_metadata_overrides(
        self,
        session: ConversionSession,
        bundle: NormalizedMetadataBundle,
    ) -> NormalizedMetadataBundle:
        if not session.metadata_overrides:
            return bundle

        subject = bundle.subject
        session_metadata = bundle.session
        additional_metadata = dict(bundle.additional_metadata)

        for key, value in session.metadata_overrides.items():
            canonical_key = self._rules.canonical_key_for(key) or key
            override_value = NormalizedValue(
                value=value,
                origin=ValueOrigin.USER_SUPPLIED,
                review_status=ReviewStatus.NOT_REVIEWED,
                notes=("Applied from session-wide metadata override.",),
            )

            if canonical_key.startswith("subject.") and hasattr(subject, canonical_key.removeprefix("subject.")):
                field_name = canonical_key.removeprefix("subject.")
                current_value = getattr(subject, field_name)
                subject = replace(
                    subject,
                    **{
                        field_name: self._merge_override_value(
                            override_value,
                            current_value,
                            canonical_key,
                        )
                    },
                )
                continue

            if canonical_key.startswith("session.") and hasattr(session_metadata, canonical_key.removeprefix("session.")):
                field_name = canonical_key.removeprefix("session.")
                if field_name == "keywords":
                    session_metadata = replace(session_metadata, keywords=(override_value,))
                    continue
                current_value = getattr(session_metadata, field_name)
                session_metadata = replace(
                    session_metadata,
                    **{
                        field_name: self._merge_override_value(
                            override_value,
                            current_value,
                            canonical_key,
                        )
                    },
                )
                continue

            existing_value = additional_metadata.get(canonical_key)
            additional_metadata[canonical_key] = self._merge_override_value(
                override_value,
                existing_value,
                canonical_key,
            )

        return replace(
            bundle,
            subject=subject,
            session=session_metadata,
            additional_metadata=additional_metadata,
        )

    @staticmethod
    def _merge_override_value(
        override_value: NormalizedValue[object],
        current_value: NormalizedValue[object] | None,
        canonical_key: str,
    ) -> NormalizedValue[object]:
        if current_value is None:
            return override_value
        if current_value.value == override_value.value:
            return replace(
                override_value,
                notes=override_value.notes + ("Confirmed existing normalized value.",),
            )
        return replace(
            override_value,
            notes=override_value.notes
            + (
                f"Overrode normalized value for {canonical_key}.",
                f"Previous value came from source(s): {', '.join(current_value.source_ids) or 'session merge'}.",
            ),
        )

    @classmethod
    def _source_priority(cls, source_ids: tuple[str, ...], source_roles: dict[str, str]) -> int:
        if not source_ids:
            return 0
        return max(cls._SOURCE_ROLE_PRIORITY.get(source_roles.get(source_id, "supplemental"), 1) for source_id in source_ids)

    @classmethod
    def _role_name(cls, source_ids: tuple[str, ...], source_roles: dict[str, str]) -> str:
        if not source_ids:
            return "unknown"
        ranked = sorted(
            (
                cls._SOURCE_ROLE_PRIORITY.get(source_roles.get(source_id, "supplemental"), 1),
                source_roles.get(source_id, "supplemental"),
            )
            for source_id in source_ids
        )
        return ranked[-1][1]
