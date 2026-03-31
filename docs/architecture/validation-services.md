# Validation Service Baseline

Last updated: 2026-03-31

## Purpose

This note captures the current validation-layer implementation baseline.

## Implemented services

### `ArtifactValidationService`

Location: `src/nwbforge/validation/services.py`

Responsibilities:
- validate that output artifacts were actually produced
- require an NWB output by default
- flag missing files, empty files, and unexpected NWB artifact extensions
- warn when multiple NWB outputs exist and the canonical artifact is ambiguous

### `PyNWBSchemaValidationService`

Location: `src/nwbforge/validation/services.py`

Responsibilities:
- run PyNWB schema validation against readable `.nwb` artifacts
- convert PyNWB-reported schema problems into repository-level `ValidationIssue` records
- convert unreadable or malformed `.nwb` files into stable validation errors rather than raw exceptions

### `NWBInspectorValidationService`

Location: `src/nwbforge/validation/services.py`

Responsibilities:
- run NWB Inspector best-practice checks against readable `.nwb` artifacts
- convert `InspectorMessage` output into repository-level `ValidationIssue` records
- preserve PyNWB/schema separation by calling NWB Inspector with `skip_validate=True`
- map NWB Inspector critical findings to blocking validation errors and lower-importance findings to warnings

### `CompositeValidationService`

Location: `src/nwbforge/validation/services.py`

Responsibilities:
- compose multiple validation services into one validation pass
- preserve the separation between artifact policy, schema validation, and future best-practice inspection

### `JsonValidationReportService`

Location: `src/nwbforge/validation/reports.py`

Responsibilities:
- serialize validation results and provenance context into a machine-readable JSON artifact
- include the explicit review outcome derived from repository validation policy
- write the report as a separate generated artifact rather than folding it into validation logic
- provide a stable artifact for UI review, automation, or future distribution workflows

### `DefaultValidationReviewPolicyService`

Location: `src/nwbforge/validation/policies.py`

Responsibilities:
- convert raw validation summaries into explicit workflow-facing review outcomes
- distinguish between `pass`, `review`, and `blocked` states
- keep blocking-versus-advisory policy separate from both validators and report serialization

## Current scope

The validation layer now covers:
- output artifact policy checks
- PyNWB schema validation for generated NWB files
- NWB Inspector best-practice validation for generated NWB files
- explicit review-outcome derivation for UI and workflow consumers
- machine-readable validation report emission

That makes it useful now for:
- catching obvious output failures
- rejecting placeholder or unreadable `.nwb` files
- exercising the validation-service boundary with a real schema-aware validator
- surfacing best-practice-critical metadata gaps in generated files
- exposing a stable workflow-facing validation outcome without re-implementing policy in the UI
- persisting validation results as reviewable JSON artifacts
- supporting persisted approval/rejection artifacts layered on top of the validation outcome
- supporting future orchestration and release workflows

## Design constraints

- artifact policy checks are separate from schema or best-practice validation
- the service returns `ValidationSummary`, not exceptions for routine validation failures
- schema validation is composed rather than embedded into the artifact-policy service
- NWB Inspector remains separate from schema validation instead of being folded into it
- writer execution can now fail on best-practice-critical findings even when schema validation passes
- review policy is separate from validators so severity thresholds and approval rules can evolve without changing validation implementations
- report generation remains separate from validation so reporting shape can evolve without changing validators

## Immediate follow-on work

1. Persist review acknowledgements and approval decisions instead of only deriving them in-memory during execution.
2. Add richer report contents such as mapping summaries and explicit manual-review sections.
3. Expand modality-specific writing so report artifacts describe more than the current generic stream baseline.
