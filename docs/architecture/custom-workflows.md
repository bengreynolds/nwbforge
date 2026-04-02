# Custom Workflow Baseline

Last updated: 2026-04-01

## Purpose

This note captures the first real repo-owned custom-path workflow in the desktop application. The goal of this slice is not to solve arbitrary unsupported lab formats; it is to prove that the product can ingest a non-NeuroConv, lab-defined source, normalize it conservatively, surface uncertain semantics for review, and still write a valid NWB file through the existing PyNWB path.

Important scope note:
- `custom_session.json` is the current bootstrap fixture for this workflow, not the intended long-term primary end-user ingest format
- the long-term custom-path UX should start from real custom files, sidecars, folders, and manual metadata entry/override, with any app-owned JSON used only for saved state or compatibility

## Baseline source

Current custom source:
- `custom_session.json`

Location in code:
- `src/nwbforge/adapters/custom/json_session.py`

Desktop loader entry points:
- `src/nwbforge/app/desktop.py`
  - `load_custom_session(...)`
  - `load_desktop_session(...)`

## Current custom source shape

The adapter currently expects a lab-defined JSON document with blocks such as:
- `recording_context`
- `animal_profile`
- `equipment`
- `signal_sets`
- `annotations`
- `analysis_context`

This shape is intentionally non-canonical. The adapter extracts enough structure to feed the existing normalization layer, while preserving clearly custom concepts as reviewable metadata instead of forcing them into standard NWB fields.

## Mapping strategy

The current workflow uses three levels of handling:

1. Canonical alias mapping
- keys like `recording_context.recording_id`, `recording_context.summary`, `recording_context.started_at`, and `animal_profile.identifier` are normalized into the existing session/subject model through alias rules

2. Structured acquisition/device projection
- `equipment` records are projected into `devices.*`
- `signal_sets` records are projected into `acquisition_streams.*`
- this lets the current writer reuse the same device and acquisition assembly path as the manifest-backed pilot

3. Explicit review for unresolved metadata
- fields like `annotations.operator_note` and `analysis_context.sync_method` remain unmatched
- the normalization layer marks them `needs_review`
- the mapping layer emits `DESCRIBE` decisions and review issues instead of silently dropping them or pretending they are standard NWB semantics

## Execution path

This is a true custom-path workflow, so execution does not go through direct NeuroConv route execution.

Current flow:
1. desktop shell loads `custom_session.json`
2. `CustomJsonSessionAdapter` inspects the source
3. normalization aliases non-canonical keys into canonical internal metadata
4. mapping produces reviewable NWB decisions plus explicit warnings for unresolved metadata
5. repository-owned `PyNWBAssemblyService` writes the NWB file
6. validation, provenance, report artifacts, and review state proceed through the existing pipeline

## Why this is the right first custom slice

- it proves the product is not limited to NeuroConv-supported routes
- it keeps custom parsing separate from NWB writing
- it exercises the existing review model instead of bypassing it
- it keeps the custom workflow narrow and explicit before broader hybrid work begins

## Current limitations

- the custom source format is repo-defined and JSON-based, not yet tied to a real departmental lab dataset or the intended direct-ingest UX
- no custom extension / NDX path is implemented yet
- custom metadata inside acquisition or device records still needs broader review-first handling in later slices if more lab-specific fields become important

## Immediate follow-on work

1. Replace JSON-first custom-session startup with direct file/folder ingestion plus metadata override for at least one real custom dataset shape.
2. Expand review/report presentation so custom-path assumptions are even more visible in the desktop UI.
3. Decide when custom concepts should remain descriptive metadata versus become an NWB extension.
