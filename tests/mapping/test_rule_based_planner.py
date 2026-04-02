from nwbforge.domain.enums import (
    ConversionPathway,
    IssueSeverity,
    MappingAction,
    ReviewStatus,
    ValueOrigin,
)
from nwbforge.domain.models import (
    AcquisitionStream,
    ConversionSession,
    NormalizedDevice,
    NormalizedMetadataBundle,
    NormalizedSessionMetadata,
    NormalizedSubject,
    NormalizedTimeIntervalTable,
    NormalizedValue,
    TimeIntervalRow,
)
from nwbforge.mapping import RuleBasedMappingPlanner


def make_session() -> ConversionSession:
    return ConversionSession(session_id="sess-001", pathway=ConversionPathway.SUPPORTED)


def test_rule_based_planner_maps_core_session_and_subject_fields() -> None:
    metadata = NormalizedMetadataBundle(
        subject=NormalizedSubject(
            subject_id=NormalizedValue("mouse-01", origin=ValueOrigin.ADAPTER_EXTRACTED),
            species=NormalizedValue("Mus musculus", origin=ValueOrigin.ADAPTER_EXTRACTED),
            sex=NormalizedValue("U", origin=ValueOrigin.ADAPTER_EXTRACTED),
            age=NormalizedValue("P90D", origin=ValueOrigin.ADAPTER_EXTRACTED),
            description=NormalizedValue("Test subject", origin=ValueOrigin.ADAPTER_EXTRACTED),
        ),
        session=NormalizedSessionMetadata(
            session_id=NormalizedValue("session-01", origin=ValueOrigin.ADAPTER_EXTRACTED),
            session_description=NormalizedValue(
                "Visual task recording", origin=ValueOrigin.USER_SUPPLIED
            ),
            experiment_description=NormalizedValue(
                "Visual stimulation task", origin=ValueOrigin.USER_SUPPLIED
            ),
            start_time=NormalizedValue(
                "2026-03-31T10:15:00-06:00", origin=ValueOrigin.ADAPTER_EXTRACTED
            ),
            experimenter=NormalizedValue("Researcher A", origin=ValueOrigin.USER_SUPPLIED),
            keywords=(
                NormalizedValue("vision", origin=ValueOrigin.ADAPTER_EXTRACTED),
                NormalizedValue("behavior", origin=ValueOrigin.ADAPTER_EXTRACTED),
            ),
        ),
        devices=(
            NormalizedDevice(
                device_id="camera-1",
                name=NormalizedValue("Camera One", origin=ValueOrigin.ADAPTER_EXTRACTED),
                description=NormalizedValue("Behavior camera", origin=ValueOrigin.ADAPTER_EXTRACTED),
                manufacturer=NormalizedValue("Acme Imaging", origin=ValueOrigin.ADAPTER_EXTRACTED),
            ),
        ),
        acquisition_streams=(
            AcquisitionStream(
                stream_id="lick-trace",
                name=NormalizedValue("Lick Trace", origin=ValueOrigin.ADAPTER_EXTRACTED),
                modality="behavior",
                source_ids=("source-1",),
                description=NormalizedValue("Example lick signal", origin=ValueOrigin.ADAPTER_EXTRACTED),
                metadata={
                    "data": NormalizedValue([0.1, 0.2, 0.3], origin=ValueOrigin.ADAPTER_EXTRACTED),
                    "unit": NormalizedValue("a.u.", origin=ValueOrigin.ADAPTER_EXTRACTED),
                    "rate": NormalizedValue(10.0, origin=ValueOrigin.ADAPTER_EXTRACTED),
                },
            ),
            AcquisitionStream(
                stream_id="animal-position",
                name=NormalizedValue("Animal Position", origin=ValueOrigin.ADAPTER_EXTRACTED),
                modality="behavior",
                source_ids=("source-1",),
                description=NormalizedValue("Tracked animal position", origin=ValueOrigin.ADAPTER_EXTRACTED),
                metadata={
                    "behavior_type": NormalizedValue("position", origin=ValueOrigin.ADAPTER_EXTRACTED),
                    "data": NormalizedValue(
                        [[0.0, 1.0], [1.5, 2.5], [3.0, 4.0]],
                        origin=ValueOrigin.ADAPTER_EXTRACTED,
                    ),
                    "unit": NormalizedValue("meters", origin=ValueOrigin.ADAPTER_EXTRACTED),
                    "reference_frame": NormalizedValue(
                        "origin at top-left corner of arena",
                        origin=ValueOrigin.ADAPTER_EXTRACTED,
                    ),
                    "rate": NormalizedValue(20.0, origin=ValueOrigin.ADAPTER_EXTRACTED),
                },
            ),
        ),
    )

    plan = RuleBasedMappingPlanner().plan(make_session(), metadata)

    target_paths = set(plan.target_paths())
    assert "NWBFile.session_description" in target_paths
    assert "NWBFile.experiment_description" in target_paths
    assert "NWBFile.session_start_time" in target_paths
    assert "NWBFile.identifier" in target_paths
    assert "Subject.subject_id" in target_paths
    assert "Subject.sex" in target_paths
    assert "Subject.age" in target_paths
    assert "Subject.description" in target_paths
    assert "Device[camera-1].name" in target_paths
    assert "BehavioralTimeSeries[behavior].TimeSeries[lick-trace].data" in target_paths
    assert "BehavioralTimeSeries[behavior].TimeSeries[lick-trace].unit" in target_paths
    assert "Position[position].SpatialSeries[animal-position].data" in target_paths
    assert "Position[position].SpatialSeries[animal-position].reference_frame" in target_paths
    assert any(decision.action == MappingAction.MERGE for decision in plan.decisions)


def test_rule_based_planner_emits_blocking_issues_for_missing_required_fields() -> None:
    metadata = NormalizedMetadataBundle(
        session=NormalizedSessionMetadata(),
    )

    plan = RuleBasedMappingPlanner().plan(make_session(), metadata)

    blocking_codes = {issue.code for issue in plan.blocking_issues()}
    assert blocking_codes == {"missing-session-description", "missing-session-start-time"}
    assert any(issue.code == "missing-session-id" for issue in plan.issues)


def test_rule_based_planner_marks_reviewable_values_and_unmapped_metadata() -> None:
    metadata = NormalizedMetadataBundle(
        session=NormalizedSessionMetadata(
            session_id=NormalizedValue(
                "session-01",
                origin=ValueOrigin.ADAPTER_EXTRACTED,
                review_status=ReviewStatus.NEEDS_REVIEW,
            ),
            session_description=NormalizedValue(
                "Visual task recording", origin=ValueOrigin.USER_SUPPLIED
            ),
            start_time=NormalizedValue(
                "2026-03-31T10:15:00-06:00", origin=ValueOrigin.ADAPTER_EXTRACTED
            ),
        ),
        additional_metadata={
            "operator_note": NormalizedValue(
                "check sync",
                origin=ValueOrigin.ADAPTER_EXTRACTED,
                review_status=ReviewStatus.NEEDS_REVIEW,
                source_ids=("source-1",),
            )
        },
    )

    plan = RuleBasedMappingPlanner().plan(make_session(), metadata)

    identifier_decision = next(
        decision for decision in plan.decisions if decision.target_path == "NWBFile.identifier"
    )
    unmapped_decision = next(
        decision for decision in plan.decisions if decision.source_key == "operator_note"
    )

    assert identifier_decision.review_status == ReviewStatus.NEEDS_REVIEW
    assert unmapped_decision.target_path is None
    assert any(issue.severity == IssueSeverity.WARNING for issue in plan.issues)
    assert plan.extension_recommendations == (
        "Review whether 'operator_note' belongs in existing NWB fields, lab metadata, or an extension.",
    )


def test_rule_based_planner_maps_time_interval_rows() -> None:
    metadata = NormalizedMetadataBundle(
        session=NormalizedSessionMetadata(
            session_description=NormalizedValue("Visual task recording", origin=ValueOrigin.USER_SUPPLIED),
            start_time=NormalizedValue("2026-03-31T10:15:00-06:00", origin=ValueOrigin.ADAPTER_EXTRACTED),
        ),
        time_interval_tables=(
            NormalizedTimeIntervalTable(
                table_id="trials",
                table_name=NormalizedValue("trials", origin=ValueOrigin.ADAPTER_EXTRACTED),
                table_description=NormalizedValue(
                    "Experimental trials",
                    origin=ValueOrigin.ADAPTER_EXTRACTED,
                ),
                rows=(
                    TimeIntervalRow(
                        row_id="0",
                        source_ids=("source-2",),
                        start_time=NormalizedValue(0.5, origin=ValueOrigin.ADAPTER_EXTRACTED),
                        metadata={
                            "condition": NormalizedValue("left", origin=ValueOrigin.ADAPTER_EXTRACTED),
                        },
                    ),
                    TimeIntervalRow(
                        row_id="1",
                        source_ids=("source-2",),
                        start_time=NormalizedValue(1.2, origin=ValueOrigin.ADAPTER_EXTRACTED),
                        stop_time=NormalizedValue(1.8, origin=ValueOrigin.ADAPTER_EXTRACTED),
                        metadata={
                            "correct": NormalizedValue(False, origin=ValueOrigin.ADAPTER_EXTRACTED),
                        },
                    ),
                ),
            ),
        ),
    )

    plan = RuleBasedMappingPlanner().plan(make_session(), metadata)

    target_paths = set(plan.target_paths())
    assert "TimeIntervals[trials].table_name" in target_paths
    assert "TimeIntervals[trials].rows[0].start_time" in target_paths
    assert "TimeIntervals[trials].rows[0].condition" in target_paths
    assert "TimeIntervals[trials].rows[1].stop_time" in target_paths
    assert "TimeIntervals[trials].rows[1].correct" in target_paths
    assert any(issue.code == "missing-interval-stop-time" for issue in plan.issues)
