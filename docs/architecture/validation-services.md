# Validation Service Baseline

Last updated: 2026-03-31

## Purpose

This note captures the first concrete validation-layer implementation.

## Implemented service

### `ArtifactValidationService`

Location: `src/nwbforge/validation/services.py`

Responsibilities:
- validate that output artifacts were actually produced
- require an NWB output by default
- flag missing files, empty files, and unexpected NWB artifact extensions
- warn when multiple NWB outputs exist and the canonical artifact is ambiguous

## Current scope

This service is intentionally a pre-integration baseline. It validates generated artifacts without requiring PyNWB or NWB Inspector in the runtime yet.

That makes it useful now for:
- catching obvious output failures
- exercising the validation-service boundary
- supporting future orchestration and release workflows

## Design constraints

- artifact policy checks are separate from schema or best-practice validation
- the service returns `ValidationSummary`, not exceptions for routine validation failures
- PyNWB and NWB Inspector integrations remain future work

## Immediate follow-on work

1. Add PyNWB schema validation integration.
2. Add NWB Inspector integration.
3. Combine artifact, schema, and best-practice checks into one higher-level validation orchestration flow.
