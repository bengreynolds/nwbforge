# Orchestration Service Baseline

Last updated: 2026-03-31

## Purpose

This note captures the first high-level application orchestration service that chains the existing backend slices together.

## Implemented service

### `ConversionPipelineService`

Location: `src/nwbforge/app/services/pipeline.py`

Responsibilities:
- inspect all sources attached to a session
- normalize extracted metadata
- build a mapping plan
- assemble a provenance record for preview
- evaluate generated artifacts with the validation service
- derive an explicit validation review outcome for workflow consumers
- emit a machine-readable validation report artifact during execution evaluation
- expose explicit preview and execution result models
- provide an execution result that downstream review workflows can persist explicitly

## Current flow

### Preview
- inspect all sources
- normalize metadata
- build the mapping plan
- derive input-artifact provenance
- move the session into `review` or `ready_to_write`

### Execution evaluation
- validate generated artifacts
- derive `pass`, `review`, or `blocked` outcome from the validation summary
- write a validation report artifact
- derive output-aware provenance
- move the session into `completed` or `failed`

## Design constraints

- orchestration coordinates existing layers; it does not replace them
- preview and execution are explicit stages rather than one opaque call
- validation policy is integrated as a separate service rather than being embedded in validators or the UI
- report generation is integrated as a separate service rather than being embedded in validation
- session transitions remain visible and testable

## Immediate follow-on work

1. Add richer session persistence so preview and execution state can be resumed.
2. Add higher-level workflow services for UI-driven review and approval checkpoints.
3. Integrate explicit review submissions into resumable session lifecycle state once persistence contracts are settled.
4. Connect persisted review decisions to future UI approval and override workflows.
