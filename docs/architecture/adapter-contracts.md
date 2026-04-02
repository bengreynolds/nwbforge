# Adapter and Service Contract Baseline

Last updated: 2026-04-02

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
- `NeuroConvFicTracAdapter` for real NeuroConv-backed FicTrac behavior sources
- `NeuroConvDeepLabCutAdapter` for real NeuroConv-backed DeepLabCut pose-estimation sources
- `NeuroConvSLEAPAdapter` for real NeuroConv-backed SLEAP pose-estimation sources
- `NeuroConvLightningPoseAdapter` for real NeuroConv-backed LightningPose pose-estimation sources
- `NeuroConvMedPCAdapter` for real NeuroConv-backed MedPC task/event sources
- `NeuroConvAlphaOmegaAdapter` for real NeuroConv-backed AlphaOmega ecephys sources
- `NeuroConvAxonAdapter` for real NeuroConv-backed Axon/ABF ecephys sources
- `NeuroConvAxonaAdapter` for real NeuroConv-backed Axona ecephys sources
- `NeuroConvBlackrockAdapter` for real NeuroConv-backed Blackrock ecephys sources
- `NeuroConvBiocamAdapter` for real NeuroConv-backed Biocam ecephys sources
- `NeuroConvBrukerTiffSinglePlaneAdapter` and `NeuroConvBrukerTiffMultiPlaneAdapter` for real NeuroConv-backed Bruker TIFF imaging sources
- `NeuroConvEdfAdapter` for real NeuroConv-backed EDF ecephys sources
- `NeuroConvFemtonicsAdapter` for real NeuroConv-backed Femtonics imaging sources
- `NeuroConvVideoAdapter` for real NeuroConv-backed external video sources
- `NeuroConvHdf5ImagingAdapter` for real NeuroConv-backed HDF5 imaging sources
- `NeuroConvInscopixAdapter` for real NeuroConv-backed Inscopix imaging sources
- `NeuroConvMCSRawAdapter` for real NeuroConv-backed MCSRaw ecephys sources
- `NeuroConvMicroManagerTiffAdapter` for real NeuroConv-backed Micro-Manager TIFF imaging sources
- `NeuroConvMiniscopeAdapter` for real NeuroConv-backed Miniscope imaging sources
- `NeuroConvNeuralynxAdapter` for real NeuroConv-backed Neuralynx ecephys sources
- `NeuroConvNeuralynxNvtAdapter` for real NeuroConv-backed Neuralynx NVT behavior sources
- `NeuroConvNeuroScopeAdapter` for real NeuroConv-backed NeuroScope ecephys sources
- `NeuroConvOpenEphysBinaryAnalogAdapter` for real NeuroConv-backed OpenEphys Binary analog sources
- `NeuroConvOpenEphysBinaryAdapter` for real NeuroConv-backed OpenEphys Binary ecephys sources
- `NeuroConvOpenEphysLegacyAdapter` for real NeuroConv-backed OpenEphys Legacy ecephys sources
- `NeuroConvPlexonAdapter` for real NeuroConv-backed Plexon ecephys sources
- `NeuroConvScanImageAdapter` for real NeuroConv-backed ScanImage imaging sources
- `NeuroConvScanImageLegacyAdapter` for real NeuroConv-backed ScanImage legacy imaging sources
- `NeuroConvSpikeGadgetsAdapter` for real NeuroConv-backed SpikeGadgets ecephys sources
- `NeuroConvSpikeGLXAdapter` for real NeuroConv-backed SpikeGLX ecephys sources
- `NeuroConvTdtAdapter` for real NeuroConv-backed TDT ecephys sources
- `NeuroConvThorAdapter` for real NeuroConv-backed Thor imaging sources
- `NeuroConvIntanAdapter` for real NeuroConv-backed Intan ecephys sources
- `NeuroConvWhiteMatterAdapter` for real NeuroConv-backed WhiteMatter ecephys sources

Current package direction:
- category-first supported packages should hold family modules and route declarations
- the first concrete example is `src/nwbforge/adapters/supported/behavior/`
- the text/tabular family now also follows this shape under `src/nwbforge/adapters/supported/tabular/`
- public exports from `nwbforge.adapters` and `nwbforge.adapters.supported` should stay stable while internal layout evolves

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
- the CSV and Excel interval adapters plus the still-image, audio, FicTrac, and DeepLabCut adapters now use this framework as proof cases
- the SLEAP, LightningPose, MedPC, AlphaOmega, Axon/ABF, Axona, Biocam, Blackrock, Bruker TIFF, EDF, Femtonics, Video, HDF5 imaging, Inscopix, MCSRaw, Micro-Manager TIFF, Miniscope, Neuralynx, Neuralynx NVT, NeuroScope, OpenEphys Binary, OpenEphys Binary Analog, OpenEphys Legacy, Plexon, ScanImage, ScanImage Legacy, SpikeGadgets, SpikeGLX, TDT, Thor, Intan, and WhiteMatter adapters now also use this framework as availability-gated proof cases for broader supported-route scaling
- the current tabular family implementation now lives in `src/nwbforge/adapters/supported/tabular/neuroconv.py`

Preferred tightening direction:
- fewer route-specific modules when a route differs only by interface metadata and light sniffing behavior
- more family modules with route config declarations
- distinct workflow adapters for combined NeuroConv gallery routes
- stricter criteria for when a route truly needs its own module
- category-first package structure before software-first file naming when organizing supported routes

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
- Supported behavior and media routes may write directly into their documented NWB processing or stimulus targets through NeuroConv, with the repository providing orchestration, metadata overrides, and validation around that write path
- Optional supported routes should only be registered into the active desktop adapter registry when the curated route dependencies for that route are installed in the current environment
- One curated install gate may legitimately enable more than one adapter when they share the same software stack, such as Bruker TIFF single-plane versus multi-plane, Neuralynx recording versus NVT tracking, or OpenEphys Binary recording versus analog streams

## Immediate follow-on work

1. Add the first real workflow-backed NeuroConv combined route once a concrete gallery workflow is selected.
2. Add another family-level real NeuroConv-backed supported adapter behind the registry.
3. Add lab-profile contracts and normalization rule interfaces.
4. Keep supported-path adapters extraction-only and route broader source semantics through normalization rather than ad hoc writer logic.
