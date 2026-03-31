# Session Persistence Baseline

Last updated: 2026-03-31

## Purpose

This note captures the first resumable session-state persistence baseline for execution and review workflows.

## Implemented components

### `SessionSnapshot`

Location: `src/nwbforge/domain/models/persistence.py`

Responsibilities:
- represent the persistable state of a conversion session
- capture current session metadata, provenance, validation state, and latest review decision
- stay independent of storage details so later backends can reuse the same contract

### `JsonSessionSnapshotStore`

Location: `src/nwbforge/persistence/json_store.py`

Responsibilities:
- persist `SessionSnapshot` objects as JSON files
- load saved snapshots back into canonical domain models
- keep early persistence file-based while the project delays a database decision

### `SessionPersistenceService`

Location: `src/nwbforge/app/services/persistence.py`

Responsibilities:
- persist execution results into resumable snapshots
- persist review submissions into snapshots with the latest review state
- provide a single app-layer entry point above the raw snapshot store

## Current storage shape

- snapshot files live under a configurable base directory
- default path: `artifacts/session-state/<session_id>/session-state.json`
- stored state currently represents the latest known session snapshot, not a full revision history

## Design constraints

- persistence is currently JSON file based rather than SQLite or service-backed
- snapshots currently cover session, provenance, validation, and latest review state only
- preview-stage extraction, normalization, and mapping details are not yet persisted
- review history is currently represented as latest-state persistence plus separate review artifacts, not a timeline

## Immediate follow-on work

1. Add revision history or event-log semantics instead of only the latest snapshot.
2. Persist preview-stage state so partially completed sessions can resume before execution.
3. Evaluate when JSON snapshots should give way to SQLite or another structured local store.
