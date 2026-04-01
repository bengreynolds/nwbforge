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
- `SourceWorkflowAdapter`
- `AdapterRegistry`

This keeps adapter discovery and compatibility checks explicit. Real supported and custom adapters can now be added without changing orchestration-facing expectations.

Implemented adapters now include:
- `SessionManifestAdapter` for the repo-native fixture path
- `NeuroConvCsvTimeIntervalsAdapter` for real NeuroConv-backed CSV interval sources
- `NeuroConvExcelTimeIntervalsAdapter` for real NeuroConv-backed Excel interval sources
- `NeuroConvImageAdapter` for real NeuroConv-backed still-image sources
- `NeuroConvAudioAdapter` for real NeuroConv-backed audio sources

Near-term framework direction:
- a shared NeuroConv interface-adapter base for single-source `DataInterface` routes
- shared source-configuration parsing and extraction helpers reused across supported routes
- family registries and route-configuration declarations when multiple supported entries share the same semantic path
- a later workflow-adapter layer for multi-interface NeuroConv gallery workflows

Implemented framework pieces:
- `NeuroConvInterfaceAdapter` for common source-config parsing, interface construction, and `ExtractionResult` assembly
- `NeuroConvDirectConversionAdapter` for supported routes that should hand final writing to NeuroConv directly
- `NeuroConvWorkflowAdapter` for future combined NeuroConv gallery workflows and multi-source matching
- `NeuroConvWorkflowRouteConfig` and `WorkflowSourceRequirement` for declarative workflow route matching
- `NeuroConvSourceConfig` for parsed NeuroConv-specific source settings
- metadata merge helpers for NeuroConv interface metadata plus repository overrides
- shared extraction helpers for flattened mapping and dataframe-backed field emission
- `NeuroConvTabularTimeIntervalsAdapter` for the shared CSV/Excel text-tabular route family
- the CSV and Excel interval adapters plus the still-image and audio adapters now use this framework as proof cases

Preferred tightening direction:
- fewer route-specific modules when a route differs only by interface metadata and light sniffing behavior
- more family modules with route config declarations
- distinct workflow adapters for combined NeuroConv gallery routes
- stricter criteria for when a route truly needs its own module

### Service protocols
- `SourceInspectionService`
- `NormalizationService`
- `MappingPlanner`
- `ValidationService`
- `ProvenanceService`

These protocols define what higher-level services must do without choosing concrete implementations yet.

## Design constraints

- Most adapters remain inspection/extraction-only; direct-conversion supported adapters are the exception and delegate final writing to documented NeuroConv APIs
- Registry logic remains small and deterministic
- Service protocols depend on canonical domain models, not raw dict payloads
- Extraction remains separate from normalization so source-specific naming does not leak downstream
- Supported-path adapters should prefer NeuroConv interfaces when documented support exists
- Custom supported-path adapter work should start only after checking the NeuroConv Conversion Gallery for an existing route

## Immediate follow-on work

1. Add the first real workflow-backed NeuroConv combined route once a concrete gallery workflow is selected.
2. Add another family-level real NeuroConv-backed supported adapter behind the registry.
3. Add lab-profile contracts and normalization rule interfaces.
4. Keep supported-path adapters extraction-only and route broader source semantics through normalization rather than ad hoc writer logic.
