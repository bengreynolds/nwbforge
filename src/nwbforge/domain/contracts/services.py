"""Service protocols for orchestrating the conversion pipeline."""

from __future__ import annotations

from typing import Protocol

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


class SourceInspectionService(Protocol):
    def inspect(self, session: ConversionSession, source_id: str) -> ExtractionResult:
        """Inspect a source attached to a session and return extracted structure."""


class NormalizationService(Protocol):
    def normalize(
        self,
        session: ConversionSession,
        extraction_results: tuple[ExtractionResult, ...],
    ) -> NormalizedMetadataBundle:
        """Normalize adapter output into canonical metadata models."""


class MappingPlanner(Protocol):
    def plan(
        self,
        session: ConversionSession,
        metadata: NormalizedMetadataBundle,
    ) -> MappingPlan:
        """Build an NWB-oriented mapping plan from canonical metadata."""


class AssemblyService(Protocol):
    def write(
        self,
        session: ConversionSession,
        metadata: NormalizedMetadataBundle,
        mapping_plan: MappingPlan,
        output_path: str,
    ) -> tuple[ProvenanceArtifact, ...]:
        """Write conversion outputs for the supplied mapping plan."""


class ValidationService(Protocol):
    def validate(
        self,
        session: ConversionSession,
        output_artifacts: tuple[ProvenanceArtifact, ...],
    ) -> ValidationSummary:
        """Validate generated conversion artifacts."""


class ValidationPolicyService(Protocol):
    def assess(
        self,
        session: ConversionSession,
        validation_summary: ValidationSummary,
    ) -> ValidationReviewOutcome:
        """Assess validation results into an explicit review outcome for workflow consumers."""


class ProvenanceService(Protocol):
    def build_record(
        self,
        session: ConversionSession,
        input_artifacts: tuple[ProvenanceArtifact, ...],
        generated_artifacts: tuple[ProvenanceArtifact, ...],
    ) -> ProvenanceRecord:
        """Build a provenance record for a conversion session."""


class ValidationReportService(Protocol):
    def write_report(
        self,
        session: ConversionSession,
        provenance_record: ProvenanceRecord,
        validation_summary: ValidationSummary,
        review_outcome: ValidationReviewOutcome,
    ) -> ProvenanceArtifact:
        """Write a machine-readable validation report and return its artifact metadata."""
