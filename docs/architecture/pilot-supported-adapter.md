# Pilot Supported Adapter Baseline

Last updated: 2026-04-01

## Purpose

This note captures the first concrete supported-path pilot adapter used to exercise the architecture end to end.

## Implemented adapter

### `SessionManifestAdapter`

Location: `src/nwbforge/adapters/supported/session_manifest.py`

Responsibilities:
- read a structured `session_manifest.json` source from either a file or directory input
- emit `ExtractionResult` records with stable field keys for the normalization layer
- flatten nested device records from manifest lists into stable extracted keys
- flatten nested acquisition-stream records from manifest lists into stable extracted keys
- act as the first adapter that can flow through inspection, normalization, and mapping in integration tests

## Scope and non-goals

This adapter is intentionally a repo-native pilot source. It is not a claim that a real departmental acquisition format is solved, and it does not replace the planned NeuroConv-backed supported-path work.

Its purpose is to:
- validate the adapter boundary
- prove the supported-path orchestration shape
- provide a stable fixture source while real format support is still being selected

## Current supported-path adapter set

### `SessionManifestAdapter`

Still used as the repo-native metadata and inline-stream fixture path for architecture validation.

### `NeuroConvTabularTimeIntervalsAdapter` family

Location: `src/nwbforge/adapters/supported/tabular/neuroconv.py`

Responsibilities:
- provide the shared family-level extraction path for NeuroConv tabular interval interfaces
- keep CSV and Excel interval routes on one semantic implementation path
- expose declarative route configs rather than growing separate route-specific modules when the semantics are identical

Current family routes:
- `NeuroConvCsvTimeIntervalsAdapter` using NeuroConv's documented `CsvTimeIntervalsInterface`
- `NeuroConvExcelTimeIntervalsAdapter` using NeuroConv's documented `ExcelTimeIntervalsInterface`

Current role:
- combine with the manifest-backed pilot metadata source in multi-source supported sessions
- drive normalized interval-table models, mapping-plan visibility, and NWB trial writing
- prove the family-module approach for supported routes that differ mostly by interface class and source sniffing

### `NeuroConvImageAdapter`

Location: `src/nwbforge/adapters/supported/neuroconv_images.py`

Responsibilities:
- inspect still-image file and folder sources through NeuroConv's documented `ImageInterface`
- provide the first non-tabular direct NeuroConv-supported route in the repository
- prove that supported-route execution can hand final writing to NeuroConv while reusing a base `NWBFile` built from normalized metadata

Current role:
- combine with the manifest-backed pilot metadata source in supported sessions
- write image data into NWB through NeuroConv's documented conversion API
- broaden the supported-path proof from trials-only inputs into a second modality family

### `NeuroConvAudioAdapter`

Location: `src/nwbforge/adapters/supported/neuroconv_audio.py`

Responsibilities:
- inspect audio file and directory sources through NeuroConv's documented `AudioInterface`
- prove a supported direct-conversion route that depends on a route-specific NWB extension package
- exercise supported-path writing into the NWB stimulus side through NeuroConv rather than local writer code

Current role:
- combine with the manifest-backed pilot metadata source in supported sessions
- write audio data into NWB through NeuroConv's documented conversion API
- broaden the supported-path proof from images and trials into a second non-tabular media route

### `NeuroConvFicTracAdapter`

Location: `src/nwbforge/adapters/supported/behavior/neuroconv.py`

Responsibilities:
- inspect FicTrac `.dat` sources through NeuroConv's documented `FicTracDataInterface`
- prove a real supported behavior route that writes directly into NWB behavior processing structures through NeuroConv
- surface route-level configuration inputs such as FicTrac radius and optional config-file location without rebuilding the conversion locally

Current role:
- combine with the manifest-backed pilot metadata source in supported sessions
- write FicTrac behavior data into NWB behavior processing modules through NeuroConv's documented conversion API
- broaden the supported-path proof into direct NeuroConv-backed behavior data beyond the repository's fallback behavior writer

### `NeuroConvDeepLabCutAdapter`

Location: `src/nwbforge/adapters/supported/behavior/neuroconv.py`

Responsibilities:
- inspect DeepLabCut `.csv` and `.h5` sources through NeuroConv's documented `DeepLabCutInterface`
- prove a real supported pose-estimation route that writes through the `ndx-pose` extension using NeuroConv rather than local NWB assembly
- surface route-level configuration inputs such as `subject_name` and optional DeepLabCut config-file location for later UI collection

Current role:
- combine with the manifest-backed pilot metadata source in supported sessions
- write pose-estimation data into NWB processing modules through NeuroConv's documented conversion API
- broaden the supported-path proof into a route that depends on a documented NWB extension package while preserving the repository's NeuroConv-first execution model

## Design constraints

- most supported adapters remain extraction-oriented, but direct NeuroConv routes now also own their final write path through documented NeuroConv APIs
- manifest structure stays intentionally simple and explicit
- pilot behavior should remain easy to replace once a real supported format is chosen
- route-specific interface parameters for supported NeuroConv behavior routes should be treated as UI/orchestration inputs rather than hard-coded conversion logic
- supported families should prefer category-first packaging; the current behavior and tabular routes now follow that structure

## Immediate follow-on work

1. Add another real NeuroConv-backed family from the approved route catalog or deepen the current behavior family.
2. Add the first real combined NeuroConv workflow adapter on top of the new workflow base.
3. Expand beyond the current behavior trace/position and trials assembly slices into additional modality-aware mappings.
