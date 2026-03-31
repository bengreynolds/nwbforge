"""High-level orchestration services for preview and execution flows."""

from __future__ import annotations

from dataclasses import replace

from nwbforge.domain.contracts import (
    MappingPlanner,
    NormalizationService,
    ProvenanceService,
    SourceInspectionService,
    ValidationService,
)
from nwbforge.domain.enums import SessionStatus
from nwbforge.domain.models import ConversionSession, ProvenanceArtifact

from nwbforge.app.services.models import ConversionExecution, ConversionPreview


class ConversionPipelineService:
    """Coordinate inspection, normalization, mapping, provenance, and validation."""

    def __init__(
        self,
        inspection_service: SourceInspectionService,
        normalization_service: NormalizationService,
        mapping_planner: MappingPlanner,
        provenance_service: ProvenanceService,
        validation_service: ValidationService,
    ) -> None:
        self._inspection_service = inspection_service
        self._normalization_service = normalization_service
        self._mapping_planner = mapping_planner
        self._provenance_service = provenance_service
        self._validation_service = validation_service

    def build_preview(self, session: ConversionSession) -> ConversionPreview:
        working_session = session.transition(SessionStatus.INSPECTING)
        extraction_results = tuple(
            self._inspection_service.inspect(working_session, source_id)
            for source_id in working_session.source_ids
        )

        working_session = working_session.transition(SessionStatus.NORMALIZING)
        normalized_metadata = self._normalization_service.normalize(working_session, extraction_results)

        working_session = working_session.transition(SessionStatus.MAPPING)
        mapping_plan = self._mapping_planner.plan(working_session, normalized_metadata)

        review_status = SessionStatus.REVIEW if mapping_plan.requires_manual_review() else SessionStatus.READY_TO_WRITE
        working_session = working_session.transition(review_status)

        input_artifacts = tuple(
            ProvenanceArtifact(
                artifact_type="input",
                location=source.location,
                description=source.label,
            )
            for source in working_session.sources
        )
        provenance_record = self._provenance_service.build_record(
            working_session,
            input_artifacts=input_artifacts,
            generated_artifacts=(),
        )
        adapter_ids = tuple(
            sorted({result.adapter_id for result in extraction_results if result.adapter_id})
        )
        if adapter_ids and provenance_record.adapter_ids != adapter_ids:
            provenance_record = replace(provenance_record, adapter_ids=adapter_ids)

        return ConversionPreview(
            session=working_session,
            extraction_results=extraction_results,
            normalized_metadata=normalized_metadata,
            mapping_plan=mapping_plan,
            provenance_record=provenance_record,
        )

    def evaluate_outputs(
        self,
        preview: ConversionPreview,
        output_artifacts: tuple[ProvenanceArtifact, ...],
    ) -> ConversionExecution:
        validating_session = preview.session.transition(SessionStatus.VALIDATING)
        validation_summary = self._validation_service.validate(validating_session, output_artifacts)
        final_status = SessionStatus.COMPLETED if validation_summary.is_passing() else SessionStatus.FAILED
        final_session = validating_session.transition(final_status)
        provenance_record = self._provenance_service.build_record(
            final_session,
            input_artifacts=preview.provenance_record.input_artifacts,
            generated_artifacts=output_artifacts,
        )
        if preview.provenance_record.adapter_ids and provenance_record.adapter_ids != preview.provenance_record.adapter_ids:
            provenance_record = replace(
                provenance_record,
                adapter_ids=preview.provenance_record.adapter_ids,
            )

        return ConversionExecution(
            preview=preview,
            session=final_session,
            output_artifacts=output_artifacts,
            provenance_record=provenance_record,
            validation_summary=validation_summary,
        )
