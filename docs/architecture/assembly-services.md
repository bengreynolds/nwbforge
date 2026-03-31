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

This is enough to prove a real NWB file can be written from the current preview pipeline without claiming the broader conversion problem is solved. It also brings the manifest-backed supported-path pilot to the point where writer-generated files can satisfy the current validation stack when the source provides the needed subject metadata and device records.

## Design constraints

- writer logic consumes normalized metadata and mapping intent, not raw source fields
- identifier policy is currently conservative and derived from normalized session id or the conversion session id
- the writer emits a minimal file and does not yet assemble acquisition streams or multimodal content
- device manufacturer is currently written through PyNWB's deprecated `manufacturer` argument as a temporary bridge pending a fuller `DeviceModel` design

## Immediate follow-on work

1. Expand assembly coverage to acquisition streams and richer modality content.
2. Replace temporary device manufacturer bridging with a deliberate `DeviceModel` strategy.
3. Refine identifier and metadata policy as real supported formats are integrated.
