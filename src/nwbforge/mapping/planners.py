"""Concrete mapping planners for normalized metadata."""

from __future__ import annotations

from nwbforge.domain.contracts import MappingPlanner
from nwbforge.domain.enums import IssueSeverity, MappingAction, ReviewStatus
from nwbforge.domain.models import (
    ConversionSession,
    MappingDecision,
    MappingPlan,
    NormalizedMetadataBundle,
    NormalizedValue,
    ReviewIssue,
)


class RuleBasedMappingPlanner(MappingPlanner):
    """Build a conservative first-pass NWB mapping plan from normalized metadata."""

    def plan(
        self,
        session: ConversionSession,
        metadata: NormalizedMetadataBundle,
    ) -> MappingPlan:
        decisions: list[MappingDecision] = []
        issues: list[ReviewIssue] = []
        extension_recommendations: list[str] = []

        self._map_session(metadata, decisions, issues)
        self._map_subject(metadata, decisions)
        self._map_devices(metadata, decisions)
        self._map_acquisition_streams(metadata, decisions, issues)
        self._map_additional_metadata(metadata, decisions, issues, extension_recommendations)

        summary_notes = (
            f"Generated {len(decisions)} mapping decisions for session '{session.session_id}'.",
        )
        return MappingPlan(
            pathway=session.pathway,
            decisions=tuple(decisions),
            issues=tuple(issues),
            summary_notes=summary_notes,
            extension_recommendations=tuple(extension_recommendations),
        )

    def _map_session(
        self,
        metadata: NormalizedMetadataBundle,
        decisions: list[MappingDecision],
        issues: list[ReviewIssue],
    ) -> None:
        session = metadata.session

        self._require_and_map(
            source_key="session.session_description",
            value=session.session_description,
            target_path="NWBFile.session_description",
            rationale="Direct mapping for the NWB session description.",
            decisions=decisions,
            issues=issues,
            missing_code="missing-session-description",
            missing_message="A session description is required before NWB export.",
        )
        self._require_and_map(
            source_key="session.start_time",
            value=session.start_time,
            target_path="NWBFile.session_start_time",
            rationale="Direct mapping for the NWB session start time.",
            decisions=decisions,
            issues=issues,
            missing_code="missing-session-start-time",
            missing_message="A session start time is required before NWB export.",
        )

        if session.session_id is not None:
            decisions.append(
                self._decision(
                    source_key="session.session_id",
                    value=session.session_id,
                    target_path="NWBFile.session_id",
                    action=MappingAction.DIRECT,
                    rationale="Preserve the normalized session id as NWB session_id when available.",
                )
            )
            decisions.append(
                self._decision(
                    source_key="session.session_id",
                    value=session.session_id,
                    target_path="NWBFile.identifier",
                    action=MappingAction.TRANSFORM,
                    rationale="Use the normalized session id as an input to NWB identifier generation.",
                    review_status=ReviewStatus.NEEDS_REVIEW,
                    notes=("Identifier generation policy is not finalized yet.",),
                )
            )
        else:
            issues.append(
                ReviewIssue(
                    code="missing-session-id",
                    message="No normalized session id is available for identifier seeding.",
                    severity=IssueSeverity.WARNING,
                    field="session.session_id",
                )
            )

        self._optional_map(
            "session.experiment_description",
            session.experiment_description,
            "NWBFile.experiment_description",
            "Direct mapping for experiment description metadata.",
            decisions,
        )
        self._optional_map(
            "session.experimenter",
            session.experimenter,
            "NWBFile.experimenter",
            "Direct mapping for experimenter metadata.",
            decisions,
        )
        self._optional_map(
            "session.institution",
            session.institution,
            "NWBFile.institution",
            "Direct mapping for institution metadata.",
            decisions,
        )
        self._optional_map(
            "session.lab",
            session.lab,
            "NWBFile.lab",
            "Direct mapping for lab metadata.",
            decisions,
        )

        if session.keywords:
            decisions.append(
                MappingDecision(
                    source_key="session.keywords",
                    target_path="NWBFile.keywords",
                    action=MappingAction.MERGE,
                    rationale="Merge normalized keywords into the NWB keyword list.",
                    review_status=self._aggregate_review_status(session.keywords),
                    source_ids=self._aggregate_source_ids(session.keywords),
                )
            )

    def _map_subject(
        self,
        metadata: NormalizedMetadataBundle,
        decisions: list[MappingDecision],
    ) -> None:
        subject = metadata.subject
        subject_mappings = (
            ("subject.subject_id", subject.subject_id, "Subject.subject_id"),
            ("subject.species", subject.species, "Subject.species"),
            ("subject.sex", subject.sex, "Subject.sex"),
            ("subject.age", subject.age, "Subject.age"),
            ("subject.date_of_birth", subject.date_of_birth, "Subject.date_of_birth"),
            ("subject.description", subject.description, "Subject.description"),
            ("subject.genotype", subject.genotype, "Subject.genotype"),
            ("subject.strain", subject.strain, "Subject.strain"),
        )
        for source_key, value, target_path in subject_mappings:
            self._optional_map(
                source_key,
                value,
                target_path,
                "Direct mapping for normalized subject metadata.",
                decisions,
            )

    def _map_additional_metadata(
        self,
        metadata: NormalizedMetadataBundle,
        decisions: list[MappingDecision],
        issues: list[ReviewIssue],
        extension_recommendations: list[str],
    ) -> None:
        for key, value in sorted(metadata.additional_metadata.items()):
            decisions.append(
                self._decision(
                    source_key=key,
                    value=value,
                    target_path=None,
                    action=MappingAction.DESCRIBE,
                    rationale="Preserve unmatched normalized metadata for manual mapping review.",
                    review_status=ReviewStatus.NEEDS_REVIEW,
                )
            )
            issues.append(
                ReviewIssue(
                    code="unmapped-normalized-metadata",
                    message=f"Normalized field '{key}' needs manual mapping review.",
                    severity=IssueSeverity.WARNING,
                    field=key,
                    source_ids=value.source_ids,
                )
            )
            extension_recommendations.append(
                f"Review whether '{key}' belongs in existing NWB fields, lab metadata, or an extension."
            )

    def _map_devices(
        self,
        metadata: NormalizedMetadataBundle,
        decisions: list[MappingDecision],
    ) -> None:
        for device in metadata.devices:
            self._optional_map(
                f"devices.{device.device_id}.name",
                device.name,
                f"Device[{device.device_id}].name",
                "Direct mapping for normalized device name.",
                decisions,
            )
            self._optional_map(
                f"devices.{device.device_id}.description",
                device.description,
                f"Device[{device.device_id}].description",
                "Direct mapping for normalized device description.",
                decisions,
            )
            self._optional_map(
                f"devices.{device.device_id}.manufacturer",
                device.manufacturer,
                f"Device[{device.device_id}].manufacturer",
                "Direct mapping for normalized device manufacturer.",
                decisions,
            )

    def _map_acquisition_streams(
        self,
        metadata: NormalizedMetadataBundle,
        decisions: list[MappingDecision],
        issues: list[ReviewIssue],
    ) -> None:
        for stream in metadata.acquisition_streams:
            stream_prefix = f"acquisition_streams.{stream.stream_id}"
            target_prefix = self._stream_target_prefix(stream)
            decisions.append(
                self._decision(
                    source_key=f"{stream_prefix}.name",
                    value=stream.name,
                    target_path=f"{target_prefix}.name",
                    action=MappingAction.DIRECT,
                    rationale="Direct mapping for normalized acquisition stream name.",
                )
            )
            if stream.description is not None:
                decisions.append(
                    self._decision(
                        source_key=f"{stream_prefix}.description",
                        value=stream.description,
                        target_path=f"{target_prefix}.description",
                        action=MappingAction.DIRECT,
                        rationale="Direct mapping for normalized acquisition stream description.",
                    )
                )
            if stream.modality:
                decisions.append(
                    MappingDecision(
                        source_key=f"{stream_prefix}.modality",
                        target_path=f"{target_prefix}.modality",
                        action=MappingAction.DIRECT,
                        rationale="Preserve normalized stream modality in the acquisition mapping context.",
                        source_ids=stream.source_ids,
                    )
                )
            else:
                issues.append(
                    ReviewIssue(
                        code="missing-stream-modality",
                        message=f"Acquisition stream '{stream.stream_id}' is missing modality context.",
                        severity=IssueSeverity.WARNING,
                        field=f"{stream_prefix}.modality",
                        source_ids=stream.source_ids,
                    )
                )

            self._require_stream_metadata(
                stream=stream,
                metadata_key="data",
                target_path=f"{target_prefix}.data",
                message="Acquisition streams require inline data for the current pilot writer.",
                decisions=decisions,
                issues=issues,
            )
            self._require_stream_metadata(
                stream=stream,
                metadata_key="unit",
                target_path=f"{target_prefix}.unit",
                message="Acquisition streams require a unit for the current pilot writer.",
                decisions=decisions,
                issues=issues,
            )

            has_rate = "rate" in stream.metadata
            has_timestamps = "timestamps" in stream.metadata
            if has_rate:
                self._optional_map(
                    f"{stream_prefix}.rate",
                    stream.metadata["rate"],
                    f"{target_prefix}.rate",
                    "Direct mapping for acquisition stream sample rate.",
                    decisions,
                )
            if has_timestamps:
                self._optional_map(
                    f"{stream_prefix}.timestamps",
                    stream.metadata["timestamps"],
                    f"{target_prefix}.timestamps",
                    "Direct mapping for acquisition stream timestamps.",
                    decisions,
                )
            if not has_rate and not has_timestamps:
                issues.append(
                    ReviewIssue(
                        code="missing-stream-timing",
                        message=(
                            f"Acquisition stream '{stream.stream_id}' requires either rate or timestamps "
                            "for the current pilot writer."
                        ),
                        severity=IssueSeverity.ERROR,
                        field=f"{stream_prefix}.rate",
                        source_ids=stream.source_ids,
                )
            )

    @staticmethod
    def _stream_target_prefix(stream) -> str:
        modality = (stream.modality or "").strip().lower()
        if modality == "behavior":
            return f"BehavioralTimeSeries[behavior].TimeSeries[{stream.stream_id}]"
        return f"TimeSeries[{stream.stream_id}]"

    def _require_stream_metadata(
        self,
        *,
        stream,
        metadata_key: str,
        target_path: str,
        message: str,
        decisions: list[MappingDecision],
        issues: list[ReviewIssue],
    ) -> None:
        value = stream.metadata.get(metadata_key)
        if value is None:
            issues.append(
                ReviewIssue(
                    code=f"missing-stream-{metadata_key}",
                    message=f"Acquisition stream '{stream.stream_id}' {message}",
                    severity=IssueSeverity.ERROR,
                    field=f"acquisition_streams.{stream.stream_id}.{metadata_key}",
                    source_ids=stream.source_ids,
                )
            )
            return
        decisions.append(
            self._decision(
                source_key=f"acquisition_streams.{stream.stream_id}.{metadata_key}",
                value=value,
                target_path=target_path,
                action=MappingAction.DIRECT,
                rationale=f"Direct mapping for acquisition stream {metadata_key}.",
            )
        )

    def _require_and_map(
        self,
        source_key: str,
        value: NormalizedValue[object] | None,
        target_path: str,
        rationale: str,
        decisions: list[MappingDecision],
        issues: list[ReviewIssue],
        missing_code: str,
        missing_message: str,
    ) -> None:
        if value is None:
            issues.append(
                ReviewIssue(
                    code=missing_code,
                    message=missing_message,
                    severity=IssueSeverity.ERROR,
                    field=source_key,
                )
            )
            return
        decisions.append(
            self._decision(
                source_key=source_key,
                value=value,
                target_path=target_path,
                action=MappingAction.DIRECT,
                rationale=rationale,
            )
        )

    def _optional_map(
        self,
        source_key: str,
        value: NormalizedValue[object] | None,
        target_path: str,
        rationale: str,
        decisions: list[MappingDecision],
    ) -> None:
        if value is None:
            return
        decisions.append(
            self._decision(
                source_key=source_key,
                value=value,
                target_path=target_path,
                action=MappingAction.DIRECT,
                rationale=rationale,
            )
        )

    @staticmethod
    def _decision(
        source_key: str,
        value: NormalizedValue[object],
        target_path: str | None,
        action: MappingAction,
        rationale: str,
        review_status: ReviewStatus | None = None,
        notes: tuple[str, ...] = (),
    ) -> MappingDecision:
        return MappingDecision(
            source_key=source_key,
            target_path=target_path,
            action=action,
            rationale=rationale,
            review_status=review_status or value.review_status,
            source_ids=value.source_ids,
            notes=value.notes + notes,
        )

    @staticmethod
    def _aggregate_review_status(values: tuple[NormalizedValue[object], ...]) -> ReviewStatus:
        if any(value.needs_review for value in values):
            return ReviewStatus.NEEDS_REVIEW
        return ReviewStatus.NOT_REVIEWED

    @staticmethod
    def _aggregate_source_ids(values: tuple[NormalizedValue[object], ...]) -> tuple[str, ...]:
        source_ids: list[str] = []
        for value in values:
            for source_id in value.source_ids:
                if source_id not in source_ids:
                    source_ids.append(source_id)
        return tuple(source_ids)
