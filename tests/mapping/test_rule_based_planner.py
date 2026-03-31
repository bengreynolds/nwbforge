from nwbforge.domain.enums import (
    ConversionPathway,
    IssueSeverity,
    MappingAction,
    ReviewStatus,
    ValueOrigin,
)
from nwbforge.domain.models import (
    ConversionSession,
    NormalizedMetadataBundle,
    NormalizedSessionMetadata,
    NormalizedSubject,
    NormalizedValue,
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
