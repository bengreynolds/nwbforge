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
- expose explicit preview and execution result models

## Current flow

### Preview
- inspect all sources
- normalize metadata
- build the mapping plan
- derive input-artifact provenance
- move the session into `review` or `ready_to_write`

### Execution evaluation
- validate generated artifacts
- derive output-aware provenance
- move the session into `completed` or `failed`

## Design constraints

- orchestration coordinates existing layers; it does not replace them
- preview and execution are explicit stages rather than one opaque call
- no NWB writing happens here yet
- session transitions remain visible and testable

## Immediate follow-on work

1. Add a writer/assembly service and integrate it as the execution step between preview and validation.
2. Add richer session persistence so preview and execution state can be resumed.
3. Add higher-level workflow services for UI-driven review and approval checkpoints.
