from nwbforge.domain.enums import ConversionPathway, IssueSeverity, ValidationReviewStatus
from nwbforge.domain.models import ConversionSession, ValidationIssue, ValidationSummary
from nwbforge.validation import DefaultValidationReviewPolicyService


def make_session() -> ConversionSession:
    return ConversionSession(session_id="sess-001", pathway=ConversionPathway.SUPPORTED)


def test_review_policy_marks_clean_validation_as_pass() -> None:
    outcome = DefaultValidationReviewPolicyService().assess(make_session(), ValidationSummary())

    assert outcome.status == ValidationReviewStatus.PASS
    assert outcome.blocks_completion is False
    assert outcome.requires_manual_review is False


def test_review_policy_marks_warnings_as_review() -> None:
    summary = ValidationSummary(
        issues=(
            ValidationIssue(
                code="warning-1",
                message="Example warning.",
                severity=IssueSeverity.WARNING,
                tool="nwbinspector",
            ),
        )
    )

    outcome = DefaultValidationReviewPolicyService().assess(make_session(), summary)

    assert outcome.status == ValidationReviewStatus.REVIEW
    assert outcome.blocks_completion is False
    assert outcome.requires_manual_review is True
    assert outcome.warning_count == 1


def test_review_policy_marks_errors_as_blocked() -> None:
    summary = ValidationSummary(
        issues=(
            ValidationIssue(
                code="error-1",
                message="Example error.",
                severity=IssueSeverity.ERROR,
                tool="pynwb",
            ),
        )
    )

    outcome = DefaultValidationReviewPolicyService().assess(make_session(), summary)

    assert outcome.status == ValidationReviewStatus.BLOCKED
    assert outcome.blocks_completion is True
    assert outcome.requires_manual_review is True
    assert outcome.error_count == 1
