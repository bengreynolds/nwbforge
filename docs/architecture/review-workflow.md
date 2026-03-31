# Review Workflow Baseline

Last updated: 2026-03-31

## Purpose

This note captures the first persisted review and approval workflow layered on top of execution-time validation outcomes.

## Implemented services

### `ExecutionReviewService`

Location: `src/nwbforge/app/services/review.py`

Responsibilities:
- accept explicit post-execution approval or rejection decisions
- require acknowledgement of all current validation issues before approving a review-required execution
- require an explicit override plus rationale before approving a blocked execution
- persist the resulting review decision as an artifact

### `JsonExecutionReviewArtifactService`

Location: `src/nwbforge/validation/reviews.py`

Responsibilities:
- write review decisions as machine-readable JSON artifacts
- capture reviewer identity, decision, acknowledged issue refs, and override usage
- keep persisted review state separate from both raw validation and session storage

## Current workflow

1. Run preview and execution through the existing pipeline.
2. Inspect the execution's derived validation review outcome.
3. Submit an explicit `approved` or `rejected` review decision.
4. Persist a `review_decision` artifact alongside generated outputs.

## Design constraints

- review persistence is currently artifact-based, not database-backed
- issue acknowledgement currently keys off validation issue refs derived from `code` and optional `location`
- blocked approvals require an explicit override and rationale
- execution review does not yet mutate broader session lifecycle state beyond persisted artifacts

## Immediate follow-on work

1. Persist review history and repeated review actions rather than only the latest submission artifact.
2. Connect approval decisions to resumable session state and future UI workflows.
3. Add richer review payloads such as reviewer notes on mapping assumptions and manual scientific checks.
