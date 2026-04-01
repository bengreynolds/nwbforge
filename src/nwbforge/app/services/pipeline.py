"""High-level orchestration services for preview and execution flows."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import logging

from nwbforge.app.logging import get_logger, log_event
from nwbforge.app.runtime.models import PipelineProgressEvent, PipelineStage, ProgressCallback
from nwbforge.domain.contracts import (
    AssemblyService,
    MappingPlanner,
    NormalizationService,
    ProvenanceService,
    SourceInspectionService,
    ValidationPolicyService,
    ValidationReportService,
    ValidationService,
)
from nwbforge.domain.enums import ConversionPathway
from nwbforge.domain.enums import SessionStatus
from nwbforge.domain.models import (
    ConversionSession,
    ProvenanceArtifact,
    ProvenanceRecord,
    ValidationReviewOutcome,
    ValidationSummary,
)
from nwbforge.validation import DefaultValidationReviewPolicyService

from nwbforge.app.services.errors import AssemblyConfigurationError
from nwbforge.app.services.models import ConversionExecution, ConversionPreview
from nwbforge.app.services.supported_execution import NeuroConvSupportedExecutionService


class ConversionPipelineService:
    """Coordinate inspection, normalization, mapping, provenance, and validation."""

    _logger = get_logger(__name__)

    def __init__(
        self,
        inspection_service: SourceInspectionService,
        normalization_service: NormalizationService,
        mapping_planner: MappingPlanner,
        provenance_service: ProvenanceService,
        validation_service: ValidationService,
        validation_policy_service: ValidationPolicyService | None = None,
        validation_report_service: ValidationReportService | None = None,
        assembly_service: AssemblyService | None = None,
        supported_execution_service: NeuroConvSupportedExecutionService | None = None,
    ) -> None:
        self._inspection_service = inspection_service
        self._normalization_service = normalization_service
        self._mapping_planner = mapping_planner
        self._provenance_service = provenance_service
        self._validation_service = validation_service
        self._validation_policy_service = validation_policy_service or DefaultValidationReviewPolicyService()
        self._validation_report_service = validation_report_service
        self._assembly_service = assembly_service
        self._supported_execution_service = supported_execution_service

    def build_preview(
        self,
        session: ConversionSession,
        progress_callback: ProgressCallback | None = None,
    ) -> ConversionPreview:
        log_event(
            self._logger,
            logging.INFO,
            "Starting preview build.",
            session_id=session.session_id,
            pathway=session.pathway.value,
            source_count=len(session.sources),
        )
        working_session = session.transition(SessionStatus.INSPECTING)
        self._emit_progress(
            progress_callback,
            working_session.session_id,
            PipelineStage.INSPECTING,
            5,
            "Inspecting sources.",
        )
        extraction_results = []
        total_sources = max(len(working_session.source_ids), 1)
        for index, source_id in enumerate(working_session.source_ids, start=1):
            log_event(
                self._logger,
                logging.DEBUG,
                "Inspecting source.",
                session_id=working_session.session_id,
                source_id=source_id,
                source_index=index,
                source_count=total_sources,
            )
            extraction_results.append(self._inspection_service.inspect(working_session, source_id))
            inspected_percent = 5 + int((index / total_sources) * 35)
            self._emit_progress(
                progress_callback,
                working_session.session_id,
                PipelineStage.INSPECTING,
                inspected_percent,
                f"Inspected source {index} of {total_sources}.",
                source_id=source_id,
            )
        extraction_results = tuple(extraction_results)

        working_session = working_session.transition(SessionStatus.NORMALIZING)
        self._emit_progress(
            progress_callback,
            working_session.session_id,
            PipelineStage.NORMALIZING,
            50,
            "Normalizing extracted metadata.",
        )
        normalized_metadata = self._normalization_service.normalize(working_session, extraction_results)
        log_event(
            self._logger,
            logging.DEBUG,
            "Normalized metadata bundle.",
            session_id=working_session.session_id,
            device_count=len(normalized_metadata.devices),
            acquisition_stream_count=len(normalized_metadata.acquisition_streams),
            time_interval_table_count=len(normalized_metadata.time_interval_tables),
        )

        working_session = working_session.transition(SessionStatus.MAPPING)
        self._emit_progress(
            progress_callback,
            working_session.session_id,
            PipelineStage.MAPPING,
            70,
            "Building NWB mapping plan.",
        )
        mapping_plan = self._mapping_planner.plan(working_session, normalized_metadata)
        log_event(
            self._logger,
            logging.DEBUG,
            "Built mapping plan.",
            session_id=working_session.session_id,
            decision_count=len(mapping_plan.decisions),
            issue_count=len(mapping_plan.issues),
            requires_manual_review=mapping_plan.requires_manual_review(),
        )

        review_status = SessionStatus.REVIEW if mapping_plan.requires_manual_review() else SessionStatus.READY_TO_WRITE
        working_session = working_session.transition(review_status)
        terminal_preview_stage = (
            PipelineStage.REVIEW if review_status == SessionStatus.REVIEW else PipelineStage.READY_TO_WRITE
        )
        terminal_preview_message = (
            "Preview requires review." if terminal_preview_stage == PipelineStage.REVIEW else "Preview ready to write."
        )
        self._emit_progress(
            progress_callback,
            working_session.session_id,
            terminal_preview_stage,
            100,
            terminal_preview_message,
        )

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

        log_event(
            self._logger,
            logging.INFO,
            "Preview build completed.",
            session_id=working_session.session_id,
            status=working_session.status.value,
            adapter_ids=adapter_ids,
        )

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
        progress_callback: ProgressCallback | None = None,
    ) -> ConversionExecution:
        log_event(
            self._logger,
            logging.INFO,
            "Starting output evaluation.",
            session_id=preview.session.session_id,
            artifact_count=len(output_artifacts),
        )
        validating_session = preview.session.transition(SessionStatus.VALIDATING)
        self._emit_progress(
            progress_callback,
            validating_session.session_id,
            PipelineStage.VALIDATING,
            70,
            "Validating generated outputs.",
        )
        validation_summary = self._validation_service.validate(validating_session, output_artifacts)
        review_outcome = self._validation_policy_service.assess(validating_session, validation_summary)
        final_status = SessionStatus.FAILED if review_outcome.blocks_completion else SessionStatus.COMPLETED
        final_session = validating_session.transition(final_status)
        provisional_provenance = self._provenance_service.build_record(
            final_session,
            input_artifacts=preview.provenance_record.input_artifacts,
            generated_artifacts=output_artifacts,
        )
        if preview.provenance_record.adapter_ids and provisional_provenance.adapter_ids != preview.provenance_record.adapter_ids:
            provisional_provenance = replace(
                provisional_provenance,
                adapter_ids=preview.provenance_record.adapter_ids,
            )
        report_artifact = self._write_validation_report(
            final_session,
            provisional_provenance,
            validation_summary,
            review_outcome,
        )
        final_artifacts = output_artifacts if report_artifact is None else output_artifacts + (report_artifact,)
        provenance_record = self._provenance_service.build_record(
            final_session,
            input_artifacts=preview.provenance_record.input_artifacts,
            generated_artifacts=final_artifacts,
        )
        if preview.provenance_record.adapter_ids and provenance_record.adapter_ids != preview.provenance_record.adapter_ids:
            provenance_record = replace(
                provenance_record,
                adapter_ids=preview.provenance_record.adapter_ids,
            )
        self._emit_progress(
            progress_callback,
            final_session.session_id,
            PipelineStage.FAILED if final_status == SessionStatus.FAILED else PipelineStage.COMPLETED,
            100,
            "Conversion failed during validation."
            if final_status == SessionStatus.FAILED
            else "Conversion completed successfully.",
        )
        log_event(
            self._logger,
            logging.INFO,
            "Output evaluation completed.",
            session_id=final_session.session_id,
            status=final_session.status.value,
            error_count=len(validation_summary.errors()),
            warning_count=len(validation_summary.warnings()),
            review_outcome=review_outcome.status,
        )

        return ConversionExecution(
            preview=preview,
            session=final_session,
            output_artifacts=final_artifacts,
            provenance_record=provenance_record,
            validation_summary=validation_summary,
            review_outcome=review_outcome,
        )

    def execute(
        self,
        preview: ConversionPreview,
        output_path: Path,
        progress_callback: ProgressCallback | None = None,
    ) -> ConversionExecution:
        log_event(
            self._logger,
            logging.INFO,
            "Starting conversion execution.",
            session_id=preview.session.session_id,
            output_path=str(output_path),
            pathway=preview.session.pathway.value,
        )
        if self._assembly_service is None:
            if self._supported_execution_service is None:
                raise AssemblyConfigurationError(
                    "ConversionPipelineService.execute requires a configured assembly service."
                )

        self._emit_progress(
            progress_callback,
            preview.session.session_id,
            PipelineStage.WRITING,
            20,
            "Writing NWB output.",
        )
        if (
            preview.session.pathway == ConversionPathway.SUPPORTED
            and self._supported_execution_service is not None
            and self._supported_execution_service.can_execute(preview)
        ):
            log_event(
                self._logger,
                logging.INFO,
                "Routing execution through direct NeuroConv supported path.",
                session_id=preview.session.session_id,
            )
            output_artifacts = self._supported_execution_service.write(preview, output_path)
        else:
            if self._assembly_service is None:
                raise AssemblyConfigurationError(
                    "ConversionPipelineService.execute requires a configured assembly service."
                )
            log_event(
                self._logger,
                logging.INFO,
                "Routing execution through repository assembly service.",
                session_id=preview.session.session_id,
            )
            output_artifacts = self._assembly_service.write(
                preview.session,
                preview.normalized_metadata,
                preview.mapping_plan,
                str(output_path),
            )
        self._emit_progress(
            progress_callback,
            preview.session.session_id,
            PipelineStage.WRITING,
            60,
            "Wrote NWB output artifacts.",
        )
        return self.evaluate_outputs(preview, output_artifacts, progress_callback=progress_callback)

    def _write_validation_report(
        self,
        session: ConversionSession,
        provenance_record: ProvenanceRecord,
        validation_summary: ValidationSummary,
        review_outcome: ValidationReviewOutcome,
    ) -> ProvenanceArtifact | None:
        if self._validation_report_service is None:
            return None
        return self._validation_report_service.write_report(
            session,
            provenance_record,
            validation_summary,
            review_outcome,
        )

    @staticmethod
    def _emit_progress(
        progress_callback: ProgressCallback | None,
        session_id: str,
        stage: PipelineStage,
        percent_complete: int,
        message: str,
        *,
        source_id: str | None = None,
    ) -> None:
        if progress_callback is None:
            return
        progress_callback(
            PipelineProgressEvent(
                session_id=session_id,
                stage=stage,
                percent_complete=percent_complete,
                message=message,
                source_id=source_id,
            )
        )
