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

Implemented adapters now include:
- `SessionManifestAdapter` for the repo-native fixture path
- `NeuroConvCsvTimeIntervalsAdapter` for real NeuroConv-backed CSV interval sources

Near-term framework direction:
- a shared NeuroConv interface-adapter base for single-source `DataInterface` routes
- shared source-configuration parsing and extraction helpers reused across supported routes
- a later workflow-adapter layer for multi-interface NeuroConv gallery workflows

Implemented framework pieces:
- `NeuroConvInterfaceAdapter` for common source-config parsing, interface construction, and `ExtractionResult` assembly
- `NeuroConvSourceConfig` for parsed NeuroConv-specific source settings
- shared extraction helpers for flattened mapping and dataframe-backed field emission
- the CSV intervals adapter now uses this framework as the first proof case

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
- Supported-path adapters should prefer NeuroConv interfaces when documented support exists
- Custom supported-path adapter work should start only after checking the NeuroConv Conversion Gallery for an existing route

## Immediate follow-on work

1. Add another real NeuroConv-backed supported adapter behind the registry.
2. Add lab-profile contracts and normalization rule interfaces.
3. Keep supported-path adapters extraction-only and route broader source semantics through normalization rather than ad hoc writer logic.
