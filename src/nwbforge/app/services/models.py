"""Result models for application-level orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from nwbforge.domain.models import (
    ConversionSession,
    ExtractionResult,
    MappingPlan,
    NormalizedMetadataBundle,
    ProvenanceArtifact,
    ProvenanceRecord,
    ValidationReviewOutcome,
    ValidationSummary,
)


@dataclass(frozen=True, slots=True)
class ConversionPreview:
    session: ConversionSession
    extraction_results: tuple[ExtractionResult, ...]
    normalized_metadata: NormalizedMetadataBundle
    mapping_plan: MappingPlan
    provenance_record: ProvenanceRecord


@dataclass(frozen=True, slots=True)
class ConversionExecution:
    preview: ConversionPreview
    session: ConversionSession
    output_artifacts: tuple[ProvenanceArtifact, ...]
    provenance_record: ProvenanceRecord
    validation_summary: ValidationSummary
    review_outcome: ValidationReviewOutcome
