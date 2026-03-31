# Core Contract Baseline

Last updated: 2026-03-31

## Purpose

This note describes the first implementation slice under Phase 2. The goal is to define stable canonical contracts before adding adapters, orchestration services, or NWB-writing code.

## Implemented contract groups

### Session contracts
- `ConversionSession`
- `SourceReference`

These represent the workflow container and the raw inputs attached to it. They deliberately avoid parser-specific logic.

### Normalization contracts
- `NormalizedValue`
- `NormalizedSubject`
- `NormalizedSessionMetadata`
- `NormalizedDevice`
- `AcquisitionStream`
- `NormalizedMetadataBundle`

These provide the canonical metadata layer described in [planning.md](../../planning.md). Each normalized value carries origin and review status so ambiguity survives into later mapping and review stages.

### Mapping contracts
- `MappingDecision`
- `MappingPlan`

These capture how normalized concepts are intended to populate NWB structures, including which decisions still require manual review.

### Provenance and validation contracts
- `ProvenanceArtifact`
- `ProvenanceRecord`
- `ValidationIssue`
- `ValidationSummary`

These make provenance and validation explicit domain concepts rather than ad hoc report payloads.

## Design constraints

- Domain models are independent of UI, adapters, and PyNWB
- Source parsing details do not appear in normalization or mapping models
- Review state remains visible on values and mapping decisions
- The models are intentionally small and immutable to make later orchestration safer

## Immediate follow-on work

1. Add adapter registry contracts and extracted-record models.
2. Add service interfaces for normalization, mapping planning, and validation execution.
3. Add session persistence models once workflow state storage is chosen.
