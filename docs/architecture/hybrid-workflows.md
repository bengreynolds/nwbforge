# Hybrid Workflow Baseline

Last updated: 2026-04-01

## Purpose

This note captures the first real hybrid-path workflow in the desktop application. The goal is to prove that one session can combine a supported source and a custom source, move through the shared normalization/mapping/review model, and still produce one validated NWB output with explicit provenance.

## Baseline source

Current hybrid desktop descriptor:
- `hybrid_session.json`

Location in code:
- `src/nwbforge/app/desktop.py`
  - `load_hybrid_session(...)`
  - `load_desktop_session(...)`

## Why the descriptor lives in desktop bootstrap, not the adapter layer

`hybrid_session.json` is not a raw scientific source format. It is a desktop session descriptor that tells the app which real sources should be loaded into one hybrid session.

That means:
- the descriptor belongs in desktop/session loading
- the real source adapters still do the inspection work
- hybrid composition remains a workflow concern over shared contracts, not a special parser that bypasses the adapter layer

## Current descriptor shape

The current descriptor expects:
- `session_id`
- optional `title`
- optional `notes`
- `sources`: a list of source entries

Each source entry can currently provide:
- `source_id`
- `location`
- `label`
- `role`
- `media_type`
- `adapter_hint`

Locations are resolved relative to the descriptor file.

## Current baseline workflow

The first hybrid path combines:
1. a supported `session_manifest.json` source
2. a custom `custom_session.json` supplemental source

Current flow:
1. desktop shell loads `hybrid_session.json`
2. desktop loader creates one `ConversionSession(pathway=HYBRID, ...)`
3. manifest and custom sources are inspected by their existing adapters
4. normalization merges canonical metadata plus supplemental custom data
5. mapping surfaces unresolved custom semantics for review
6. repository-owned `PyNWBAssemblyService` writes one NWB file
7. validation, provenance, report artifacts, and review proceed through the existing pipeline

## Why this is the right first hybrid slice

- it proves hybrid behavior without inventing a new adapter type
- it keeps supported and custom concerns separated at the source layer
- it exercises source merging through existing normalization and mapping contracts
- it gives the desktop UI a real multi-source workflow before broader route expansion

## Current limitations

- the current hybrid descriptor is desktop-focused and not yet a persisted general project/session format
- the first hybrid slice uses repository-owned PyNWB assembly, not a supported-route direct NeuroConv execution merge
- only one representative supported-plus-custom hybrid combination is implemented so far

## Immediate follow-on work

1. Expand hybrid workflow presentation in the desktop UI so multi-source provenance and review status are even more visible.
2. Decide whether the current descriptor should evolve into a broader persisted desktop project/session format.
3. Add richer hybrid combinations once first-pass internal testing identifies the highest-value real lab scenarios.
