"""Concrete normalization services."""

from __future__ import annotations

from dataclasses import replace

from nwbforge.domain.contracts import NormalizationService
from nwbforge.domain.enums import ReviewStatus, ValueOrigin
from nwbforge.domain.models import (
    ConversionSession,
    ExtractedField,
    ExtractionResult,
    NormalizedMetadataBundle,
    NormalizedSessionMetadata,
    NormalizedSubject,
    NormalizedValue,
)
from nwbforge.normalization.rules import DEFAULT_FIELD_ALIASES, NormalizationRuleSet


class RuleBasedNormalizationService(NormalizationService):
    """Normalize extracted fields with a conservative alias-driven rule set."""

    def __init__(self, rules: NormalizationRuleSet | None = None) -> None:
        self._rules = rules or NormalizationRuleSet(field_aliases=DEFAULT_FIELD_ALIASES)

    def normalize(
        self,
        session: ConversionSession,
        extraction_results: tuple[ExtractionResult, ...],
    ) -> NormalizedMetadataBundle:
        subject = NormalizedSubject()
        session_metadata = NormalizedSessionMetadata()
        additional_metadata: dict[str, NormalizedValue[object]] = {}

        for result in extraction_results:
            for extracted_field in result.fields.values():
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
