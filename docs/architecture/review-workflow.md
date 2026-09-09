# Review Workflow Baseline

Purpose: preserve explicit approval, rejection, and acknowledgement state for executed conversions.

Current baseline:
- `ExecutionReviewService` records review decisions
- `JsonExecutionReviewArtifactService` persists those decisions as machine-readable artifacts
- Warning and blocked cases require explicit user action

Constraints:
- Review state should remain separate from validation output
- The workflow must stay auditable
- Uncertain or blocked cases should remain visible rather than being normalized away

Next step:
- Expand review policy only when the current artifact model no longer covers the workflow
