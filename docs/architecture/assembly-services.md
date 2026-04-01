# Assembly Service Baseline

Last updated: 2026-03-31

## Purpose

This note captures the first concrete NWB assembly and writer implementation.

## Implemented service

### `PyNWBAssemblyService`

Location: `src/nwbforge/mapping/assemblers.py`

Responsibilities:
- build a minimal `NWBFile` from normalized metadata and the current mapping plan
- write the resulting file via `NWBHDF5IO`
- emit a generated `ProvenanceArtifact` for the output NWB file
- fit directly into the execution path of `ConversionPipelineService`
- provide a reusable base-`NWBFile` builder for direct NeuroConv-supported execution paths

## Current scope

The first writer intentionally covers a narrow, high-confidence subset:
- session description
- experiment description
- identifier
- session start time
- session id
- experimenter
- lab
- institution
- keywords
- subject id, species, sex, age, date of birth, description, genotype, strain
- devices with name, description, and manufacturer
- behavior acquisition streams written into `BehavioralTimeSeries`
- behavior position streams written into `Position` containers with `SpatialSeries`
- generic acquisition `TimeSeries` fallback for non-behavior inline stream data, units, and timing metadata
- trial interval tables written into NWB trials

This is enough to prove a real NWB file can be written from the current preview pipeline without claiming the broader conversion problem is solved. It also brings the manifest-backed supported-path pilot to the point where writer-generated files can satisfy the current validation stack when the source provides the needed subject metadata, device records, and inline stream data.

## Design constraints

- writer logic consumes normalized metadata and mapping intent, not raw source fields
- identifier policy is currently conservative and derived from normalized session id or the conversion session id
- the writer emits a minimal file and only supports behavior traces, behavior position data, plus generic inline fallback, not broader modality coverage yet
- interval-table support is currently limited to NWB trials, with stop times inferred from the next interval start when needed
- device manufacturer is currently written through PyNWB's deprecated `manufacturer` argument as a temporary bridge pending a fuller `DeviceModel` design
- acquisition streams currently require inline `data`, `unit`, and either `rate` or `timestamps`
- direct writer code should follow official PyNWB APIs and prefer built-in container classes over custom HDF5-level logic
- `pynwb.file` objects such as `NWBFile` and `Subject` remain the default path for file-level metadata
- supported NeuroConv routes can now reuse `build_nwbfile(...)` to create the base file that NeuroConv appends to, instead of bypassing the repository's normalized metadata pipeline

## Immediate follow-on work

1. Expand assembly coverage from the current behavior trace/position baseline to additional modality-specific acquisition content.
2. Expand interval-table support beyond NWB trials when a supported route requires epochs or custom `TimeIntervals`.
3. Replace temporary device manufacturer bridging with a deliberate `DeviceModel` strategy.
