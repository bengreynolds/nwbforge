# Session Persistence Baseline

Last updated: 2026-04-01

## Purpose

This note captures the current resumable session-state persistence baseline for desktop preview, execution, and review workflows.

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
- persist preview results into resumable snapshots before any NWB file is written
- persist execution results into resumable snapshots
- persist review submissions into snapshots with the latest review state
- provide a single app-layer entry point above the raw snapshot store

### Desktop integration

Location: `src/nwbforge/app/desktop.py` and `src/nwbforge/ui/conversion_session.py`

Responsibilities:
- provision a real snapshot store under the desktop app-state directory
- persist latest preview state automatically when a preview completes successfully
- persist latest execution state automatically when execution completes successfully
- persist latest review state automatically when a review decision is submitted successfully
- surface persistence failures back into the desktop workflow as user-facing errors instead of failing silently

## Current storage shape

- snapshot files live under a configurable base directory
- desktop default path: `.nwbforge/session-state/<session_id>/session-state.json`
- test and service callers may still choose a different base directory explicitly
- stored state currently represents the latest known session snapshot, not a full revision history

## Design constraints

- persistence is currently JSON file based rather than SQLite or service-backed
- snapshots currently cover session, provenance, validation, and latest review state only
- preview-stage snapshot persistence is now implemented, but preview-state detail is still limited to the session plus provenance snapshot rather than a richer persisted preview model
- review history is currently represented as latest-state persistence plus separate review artifacts, not a timeline

## Immediate follow-on work

1. Add revision history or event-log semantics instead of only the latest snapshot.
2. Decide how much preview-stage detail should be persisted beyond the current session-plus-provenance snapshot.
3. Evaluate when JSON snapshots should give way to SQLite or another structured local store.
