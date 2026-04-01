# NWB Forge

NWB Forge is a planned UI-driven platform for converting heterogeneous lab acquisition data into understandable, validated NWB files. The project is aimed at department-wide use across labs that range from common supported acquisition systems to proprietary or highly custom pipelines.

The architecture is intentionally split into explicit layers:
- UI and workflow orchestration
- source adapters and plugins
- metadata normalization
- NWB mapping and assembly
- validation, provenance, and reporting
- release packaging and update workflows

The system is planned around three conversion pathways:
- Supported pathway: common formats handled primarily through existing NWB ecosystem tooling
- Custom mapping pathway: unsupported or weakly structured inputs that require explicit mapping
- Hybrid pathway: sessions that merge supported and custom inputs into one NWB output

## Current repository state

This repository is in early backend implementation. The current work has focused on making the architecture concrete in small, testable slices before any NWB-writing or UI-heavy work begins.

Key files:
- [planning.md](planning.md): living project plan and architecture document
- [AGENTS.md](AGENTS.md): persistent repository operating manual for human and agent contributors
- [decisions.md](decisions.md): canonical architectural and process decision history
- [environment.yml](environment.yml): dedicated Conda environment spec for current development and testing
- [docs/architecture/core-contracts.md](docs/architecture/core-contracts.md): current canonical model baseline
- [docs/architecture/adapter-contracts.md](docs/architecture/adapter-contracts.md): adapter and service-interface baseline
- [docs/architecture/application-services.md](docs/architecture/application-services.md): first concrete orchestration services
- [docs/architecture/orchestration-services.md](docs/architecture/orchestration-services.md): preview and execution orchestration flow
- [docs/architecture/normalization-services.md](docs/architecture/normalization-services.md): first normalization implementation
- [docs/architecture/mapping-services.md](docs/architecture/mapping-services.md): first mapping-planner implementation
- [docs/architecture/assembly-services.md](docs/architecture/assembly-services.md): first PyNWB-backed NWB writer
- [docs/architecture/validation-services.md](docs/architecture/validation-services.md): artifact, schema, and NWB Inspector validation baseline
- [docs/architecture/pilot-supported-adapter.md](docs/architecture/pilot-supported-adapter.md): first supported-path pilot adapter
- [docs/architecture/development-environment.md](docs/architecture/development-environment.md): current Conda-based dev/test policy
- [docs/architecture/package-management.md](docs/architecture/package-management.md): route-based package install planning for setup and future UI flows
- [docs/architecture/release-strategy.md](docs/architecture/release-strategy.md): PyInstaller-first release, installer, and updater planning
- [docs/research/nwb-ecosystem.md](docs/research/nwb-ecosystem.md): initial ecosystem research summary
- [docs/research/codex-collaboration.md](docs/research/codex-collaboration.md): repo-collaboration notes for long-lived agent workflows

## Recommended repository structure

```text
decisions.md
docs/
  architecture/
  research/
src/
  nwbforge/
tests/
```

Planned backend package layout is documented in [planning.md](planning.md).

## Implemented backend slices

- Canonical domain models for sessions, sources, normalized metadata, mapping plans, provenance, and validation summaries
- Adapter contracts and registry
- Concrete source-inspection and provenance services
- Conversion pipeline service for preview and output evaluation
- Rule-based normalization service
- Rule-based mapping planner
- PyNWB-backed assembly service for the initial supported-path subject/session metadata set
- Initial manifest-backed device support across extraction, normalization, mapping, and assembly
- Initial manifest-backed acquisition-stream support across extraction, normalization, mapping, and generic `TimeSeries` assembly
- Machine-readable JSON validation report artifacts emitted by the execution pipeline
- Explicit validation review outcomes that classify execution results as `pass`, `review`, or `blocked`
- Persisted review-decision artifacts that record approval, rejection, acknowledgements, and blocked overrides
- Resumable JSON session snapshots for the latest execution and review state
- Composite validation made up of artifact-policy checks, PyNWB schema validation, and NWB Inspector best-practice checks
- Supported-path pilot adapter for structured `session_manifest.json` sources
- Behavior-stream assembly into NWB `BehavioralTimeSeries` containers, with generic `TimeSeries` fallback for other modalities
- Behavior position assembly into NWB `Position`/`SpatialSeries` containers
- NeuroConv-backed CSV time-interval inspection through `CsvTimeIntervalsInterface`
- NeuroConv-backed Excel time-interval inspection through `ExcelTimeIntervalsInterface`
- Interval-table normalization, mapping, and NWB trial assembly
- Shared NeuroConv adapter framework for single-interface supported routes
- Category-first supported adapter packaging beginning with `supported/behavior/`
- Category-first supported adapter packaging now in place for `supported/behavior/` and `supported/tabular/`
- Family-module text/tabular supported-route implementation with declarative route configs for CSV and Excel
- NeuroConv-backed still-image route through `ImageInterface`
- NeuroConv-backed audio route through `AudioInterface`
- NeuroConv-backed FicTrac behavior route through `FicTracDataInterface`
- NeuroConv-backed DeepLabCut pose-estimation route through `DeepLabCutInterface`
- Dedicated NeuroConv workflow-adapter base for future combined gallery routes
- Direct NeuroConv supported-execution service that can write through NeuroConv while reusing a base `NWBFile` assembled from normalized metadata
- Shared runtime contracts for stage/progress/error reporting and threaded background execution
- Structured runtime logging across the core preview, execution, and supported-route handoff path
- Route-based package install planning with curated presets and persisted selection state
- Backend package-management service contracts for future setup and extension-install screens
- Backend package-install execution service with progress, logging, and failure wrapping
- Threaded runtime executor for package-install work
- Thin `PackageManagementController` binding for future setup and extension-install screens
- Toolkit-agnostic desktop UI models for shell state and package-installer screen state
- NeuroConv-first planning for real supported-path adapters, with direct PyNWB reserved for unsupported or unusually custom cases
- An explicit approved NeuroConv-first route catalog in [docs/research/neuroconv-supported-routes.md](docs/research/neuroconv-supported-routes.md)
- Explicit planning requirements for structured logging, background conversion execution, real progress/status events, and a future UI log viewer/status bar

The manifest-backed supported-path pilot adapter remains a repo-native fixture source for architecture validation. In addition, the repo now includes a real NeuroConv-backed text/tabular family that carries CSV and Excel trial-style interval data into NWB trials through one shared family module plus route declarations, plus real NeuroConv-backed still-image, audio, FicTrac, and DeepLabCut routes through NeuroConv's documented interfaces.

Supported-path policy is now explicit: check the NeuroConv Conversion Gallery first, use a documented NeuroConv interface when one exists, and fall back to direct PyNWB only when NeuroConv does not support the format or the direct PyNWB path is clearly simpler and more maintainable. For direct NWB writing, official PyNWB docs remain the source of truth.

For real supported proprietary or acquisition-system formats, the intended execution model is to let the UI and orchestration layers parameterize documented NeuroConv conversion APIs directly. The repo now also supports a bridge mode where it assembles a base `NWBFile` from normalized metadata and then lets NeuroConv append the supported route content into that file. Repository-owned PyNWB assembly remains the fallback path for unsupported formats and the primary path for custom and hybrid conversion flows.

All current implementation slices are backed by tests and documented under `docs/architecture/`.

The current writer is still intentionally narrow overall, but it now carries the core subject/session fields, first-pass device metadata, and first modality-specific acquisition paths for behavior traces via NWB `BehavioralTimeSeries` and behavior position data via `Position`/`SpatialSeries`, with generic `TimeSeries` fallback retained for other modalities. The pipeline now emits a machine-readable JSON validation report artifact alongside the generated outputs, derives an explicit validation review outcome, supports persisted post-execution review decisions, and can persist the latest execution/review state as a resumable JSON session snapshot.

The current application state is still early and backend-heavy, but it is no longer UI-free. The supported route set now includes real NeuroConv-backed CSV, Excel, image, audio, FicTrac, and DeepLabCut conversions; a shared NeuroConv adapter framework exists for additional single-interface routes; supported-route packaging now uses category-first modules for both `supported/behavior/` and `supported/tabular/`; a dedicated workflow base exists for future combined NeuroConv pipelines; runtime contracts now exist for background execution, structured logging, and stage/progress/error reporting; developer setup now has a route-based package planning layer with `minimal`, `selected`, and `full` install modes; future setup/package-install UI work has backend `PackageManagementService`, `PackageInstallationService`, `ThreadedPackageInstallationExecutor`, and `PackageManagementController` boundaries to call; and the repo now includes toolkit-agnostic UI models under `src/nwbforge/ui/` for the desktop shell and package-installer screen. Concrete widget code, broader supported-format coverage, and the conversion-session UI are still ahead.

UI/runtime expectations are now explicit in the plan and partially implemented: long-running conversions can now run through a threaded executor with real stage/progress events, the core runtime path emits structured logs with stable context payloads, and the repo now has toolkit-agnostic shell/package screen models that can drive a future desktop toolkit. Concrete File-menu widgets, status-bar widgets, progress-bar widgets, log sinks, and an optional log viewer remain the next UI-facing layers to build.

## Local development

Current development and testing should use the dedicated `nwbforge-dev` Conda environment:

```text
powershell -ExecutionPolicy Bypass -File scripts/setup-conda-dev.ps1
powershell -ExecutionPolicy Bypass -File scripts/test-conda-dev.ps1
```

Example route-based setup flows:

```text
powershell -ExecutionPolicy Bypass -File scripts/setup-conda-dev.ps1 -InstallMode selected -Preset common
powershell -ExecutionPolicy Bypass -File scripts/setup-conda-dev.ps1 -InstallMode selected -Preset custom -Routes deeplabcut,scanimage -PersistSelection
powershell -ExecutionPolicy Bypass -File scripts/setup-conda-dev.ps1 -InstallMode full -PersistSelection
```

This environment is intended only for development. Release artifacts should package everything needed so that Conda or virtual environments are not required for end users.

## Release direction

Final application releases are planned around a Python-first desktop distribution model:
- package the app with PyInstaller first
- wrap the packaged build in native installers for Windows, macOS, and Linux
- provide an in-app updater that checks GitHub Releases and downloads the correct platform artifact

This keeps the runtime self-contained for lab users while preserving the Python/scientific-stack architecture.

## Initial next steps

1. Persist preview-stage workflow state and add revision history beyond the current latest-snapshot baseline.
2. Expand assembly coverage beyond the current behavior trace/position baseline into richer modality-specific and multimodal content.
3. Add the next real NeuroConv-backed supported adapter family from the approved route catalog, likely continuing the behavior family or moving into the first combined workflow route.
4. Build the first conversion-session UI model on top of the existing pipeline/runtime contracts.
