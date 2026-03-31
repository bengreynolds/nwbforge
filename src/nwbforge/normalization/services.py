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
    NormalizedValue,
)
from nwbforge.normalization.rules import DEFAULT_FIELD_ALIASES, NormalizationRuleSet


class RuleBasedNormalizationService(NormalizationService):
    """Normalize extracted fields with a conservative alias-driven rule set."""

    _DEVICE_FIELD_PATTERN = re.compile(r"^devices\.(?P<device_key>[^.]+)\.(?P<field_name>[^.]+)$")
    _STREAM_FIELD_PATTERN = re.compile(
        r"^acquisition_streams\.(?P<stream_key>[^.]+)\.(?P<field_name>[^.]+)$"
    )

    def __init__(self, rules: NormalizationRuleSet | None = None) -> None:
        self._rules = rules or NormalizationRuleSet(field_aliases=DEFAULT_FIELD_ALIASES)

    def normalize(
        self,
        session: ConversionSession,
        extraction_results: tuple[ExtractionResult, ...],
    ) -> NormalizedMetadataBundle:
        subject = NormalizedSubject()
        session_metadata = NormalizedSessionMetadata()
        devices: dict[str, NormalizedDevice] = {}
        acquisition_streams: dict[str, AcquisitionStream] = {}
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
                    subject = self._assign_subject(subject, field_name, extracted_field)
                    continue

                if canonical_key.startswith("session."):
                    field_name = canonical_key.removeprefix("session.")
                    session_metadata = self._assign_session(session_metadata, field_name, extracted_field)
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

        return NormalizedMetadataBundle(
            subject=subject,
            session=session_metadata,
            devices=tuple(devices[key] for key in sorted(devices)),
            acquisition_streams=tuple(
                acquisition_streams[key] for key in sorted(acquisition_streams)
            ),
            additional_metadata=additional_metadata,
        )

    def _assign_subject(
        self,
        subject: NormalizedSubject,
        field_name: str,
        extracted_field: ExtractedField,
    ) -> NormalizedSubject:
        current_value = getattr(subject, field_name)
        normalized_value = self._merge_value(current_value, extracted_field)
        return replace(subject, **{field_name: normalized_value})

    def _assign_session(
        self,
        session_metadata: NormalizedSessionMetadata,
        field_name: str,
        extracted_field: ExtractedField,
    ) -> NormalizedSessionMetadata:
        if field_name == "keywords":
            existing_keywords = session_metadata.keywords
            next_keywords = self._normalize_keywords(extracted_field)
            return replace(session_metadata, keywords=existing_keywords + next_keywords)

        current_value = getattr(session_metadata, field_name)
        normalized_value = self._merge_value(current_value, extracted_field)
        return replace(session_metadata, **{field_name: normalized_value})

    def _assign_device(
        self,
        device: NormalizedDevice | None,
        *,
        device_key: str,
        field_name: str,
        extracted_field: ExtractedField,
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
            normalized_value = self._merge_value(current_value, extracted_field)
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
            normalized_value = self._merge_value(stream.name, extracted_field)
            return replace(stream, name=normalized_value, source_ids=merged_source_ids)
        if normalized_field_name == "modality":
            return replace(stream, modality=str(extracted_field.value), source_ids=merged_source_ids)
        if normalized_field_name in {"description", "start_time", "end_time"}:
            current_value = getattr(stream, normalized_field_name)
            normalized_value = self._merge_value(current_value, extracted_field)
            return replace(stream, **{normalized_field_name: normalized_value}, source_ids=merged_source_ids)

        metadata = dict(stream.metadata)
        metadata[normalized_field_name] = self._to_value(extracted_field)
        return replace(stream, metadata=metadata, source_ids=merged_source_ids)

    def _merge_value(
        self,
        current_value: NormalizedValue[object] | None,
        extracted_field: ExtractedField,
    ) -> NormalizedValue[object]:
        next_value = self._to_value(extracted_field)
        if current_value is None:
            return next_value

        merged_notes = current_value.notes + (
            f"Multiple extracted fields mapped to the same canonical value: {extracted_field.key}",
        )
        merged_sources = tuple(dict.fromkeys(current_value.source_ids + next_value.source_ids))
        return replace(
            next_value,
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
            origin=ValueOrigin.ADAPTER_EXTRACTED,
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
