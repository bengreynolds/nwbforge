# Pilot Supported Adapter Baseline

Last updated: 2026-03-31

## Purpose

This note captures the first concrete supported-path pilot adapter used to exercise the architecture end to end.

## Implemented adapter

### `SessionManifestAdapter`

Location: `src/nwbforge/adapters/supported/session_manifest.py`

Responsibilities:
- read a structured `session_manifest.json` source from either a file or directory input
- emit `ExtractionResult` records with stable field keys for the normalization layer
- act as the first adapter that can flow through inspection, normalization, and mapping in integration tests

## Scope and non-goals

This adapter is intentionally a repo-native pilot source. It is not a claim that a real departmental acquisition format is solved, and it does not replace the planned NeuroConv-backed supported-path work.

Its purpose is to:
- validate the adapter boundary
- prove the supported-path orchestration shape
- provide a stable fixture source while real format support is still being selected

## Design constraints

- adapter output is still extraction-only; no NWB writing happens here
- manifest structure stays intentionally simple and explicit
- pilot behavior should remain easy to replace once a real supported format is chosen

## Immediate follow-on work

1. Select the first real supported acquisition format for a NeuroConv-backed adapter spike.
2. Add a higher-level orchestration service that chains inspection, normalization, mapping, and validation explicitly.
3. Begin the first NWB assembly slice on top of the mapping plan.
