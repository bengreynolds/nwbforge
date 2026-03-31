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

### `CompositeValidationService`

Location: `src/nwbforge/validation/services.py`

Responsibilities:
- compose multiple validation services into one validation pass
- preserve the separation between artifact policy, schema validation, and future best-practice inspection

## Current scope

The validation layer now covers:
- output artifact policy checks
- PyNWB schema validation for generated NWB files

That makes it useful now for:
- catching obvious output failures
- rejecting placeholder or unreadable `.nwb` files
- exercising the validation-service boundary with a real schema-aware validator
- supporting future orchestration and release workflows

## Design constraints

- artifact policy checks are separate from schema or best-practice validation
- the service returns `ValidationSummary`, not exceptions for routine validation failures
- schema validation is composed rather than embedded into the artifact-policy service
- NWB Inspector remains future work

## Immediate follow-on work

1. Add NWB Inspector integration.
2. Decide how blocking versus advisory findings should be surfaced in UI review flows.
3. Add machine-readable validation report artifacts alongside `ValidationSummary`.
