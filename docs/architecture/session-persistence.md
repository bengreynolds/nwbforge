# Session Persistence Baseline

Last updated: 2026-04-03

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
- retain a bounded version history while preserving a stable latest-snapshot path
- keep early persistence file-based while the project delays a database decision

### `SessionPersistenceService`

Location: `src/nwbforge/app/services/persistence.py`

Responsibilities:
- persist preview results into resumable snapshots before any NWB file is written
- persist execution results into resumable snapshots
- persist review submissions into snapshots with the latest review state
- expose snapshot history listing and point-in-time restore support to the desktop UI
- provide a single app-layer entry point above the raw snapshot store

### Desktop integration

Location: `src/nwbforge/app/desktop.py` and `src/nwbforge/ui/conversion_session.py`

Responsibilities:
- provision a real snapshot store under the desktop app-state directory
- persist latest preview state automatically when a preview completes successfully
- persist latest execution state automatically when execution completes successfully
- persist latest review state automatically when a review decision is submitted successfully
- restore the latest saved snapshot when a session is reopened through the real desktop path
- expose versioned snapshot history in the conversion workspace and allow explicit restore of an older saved state
- make latest-state auto-recovery and snapshot-history retention configurable through desktop settings
- surface persistence failures back into the desktop workflow as user-facing errors instead of failing silently

## Current storage shape

- snapshot files live under a configurable base directory
- desktop default path: `.nwbforge/session-state/<session_id>/session-state.json`
- versioned history lives under `.nwbforge/session-state/<session_id>/history/<snapshot_id>.json`
- test and service callers may still choose a different base directory explicitly
- stored state now includes both the latest known session snapshot and a bounded revision history

## Current recovery behavior

- reopening a session through the real desktop path now loads the latest saved snapshot automatically when one exists
- the desktop settings model can disable latest-state auto-recovery when manual testers want a clean reopen path
- recovered desktop state currently includes:
  - latest session status
  - recovered generated artifacts
  - recovered validation issues and acknowledgement state
  - recovered review outcome/status text
  - best-effort recovery of the last known NWB output path from provenance
- the conversion workspace now also shows saved snapshot history and can restore one earlier snapshot version on demand
- recovery restores the latest or selected saved state for inspection and continuation, but does not reconstruct a full in-memory `ConversionPreview`, `ConversionExecution`, or review-submission object

## Design constraints

- persistence is currently JSON file based rather than SQLite or service-backed
- snapshots currently cover session, provenance, validation, and latest review state only
- preview-stage snapshot persistence is now implemented, but preview-state detail is still limited to the session plus provenance snapshot rather than a richer persisted preview model
- review history is currently represented as versioned latest-state snapshots plus separate review artifacts, not a semantically richer review timeline
- snapshot retention is bounded by settings, but there is not yet a richer diff/comparison view across saved versions

## Immediate follow-on work

1. Decide how much preview-stage detail should be persisted beyond the current session-plus-provenance snapshot.
2. Add richer comparison/reporting UX across saved versions instead of only restore/list behavior.
3. Evaluate when JSON snapshots should give way to SQLite or another structured local store.
