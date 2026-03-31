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

This is enough to prove a real NWB file can be written from the current preview pipeline without claiming the broader conversion problem is solved.

This is enough to prove a real NWB file can be written from the current preview pipeline without claiming the broader conversion problem is solved. It also brings the manifest-backed supported-path pilot to the point where writer-generated files can satisfy the current validation stack when the source provides the needed subject metadata.

## Design constraints

- writer logic consumes normalized metadata and mapping intent, not raw source fields
- identifier policy is currently conservative and derived from normalized session id or the conversion session id
- the writer emits a minimal file and does not yet assemble devices, acquisitions, or multimodal content

## Immediate follow-on work

1. Expand assembly coverage to devices, acquisitions, and richer metadata.
2. Add device and acquisition assembly without collapsing raw-source concerns into the writer.
3. Refine identifier and metadata policy as real supported formats are integrated.
