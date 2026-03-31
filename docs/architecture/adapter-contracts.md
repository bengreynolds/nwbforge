# Adapter and Service Contract Baseline

Last updated: 2026-03-31

## Purpose

This note captures the second implementation slice in Phase 2: the contracts between source adapters, the orchestration layer, and canonical domain models.

## Implemented pieces

### Extraction models
- `ExtractedField`
- `ExtractionResult`

These represent adapter output before normalization. They are intentionally source-adjacent but still independent of UI and PyNWB.

### Adapter contracts
- `AdapterCapabilities`
- `SourceAdapter`
- `AdapterRegistry`

This keeps adapter discovery and compatibility checks explicit. Real supported and custom adapters can now be added without changing orchestration-facing expectations.

### Service protocols
- `SourceInspectionService`
- `NormalizationService`
- `MappingPlanner`
- `ValidationService`
- `ProvenanceService`

These protocols define what higher-level services must do without choosing concrete implementations yet.

## Design constraints

- Adapters only inspect and extract; they do not write NWB
- Registry logic remains small and deterministic
- Service protocols depend on canonical domain models, not raw dict payloads
- Extraction remains separate from normalization so source-specific naming does not leak downstream

## Immediate follow-on work

1. Add concrete application services that consume these protocols.
2. Add lab-profile contracts and normalization rule interfaces.
3. Choose the first supported-path pilot adapter and implement it behind the registry.
