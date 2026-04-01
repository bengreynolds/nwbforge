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
- Shared runtime contracts for stage/progress/error reporting and threaded background execution
- NeuroConv-first planning for real supported-path adapters, with direct PyNWB reserved for unsupported or unusually custom cases
- An explicit approved NeuroConv-first route catalog in [docs/research/neuroconv-supported-routes.md](docs/research/neuroconv-supported-routes.md)
- Explicit planning requirements for structured logging, background conversion execution, real progress/status events, and a future UI log viewer/status bar

The manifest-backed supported-path pilot adapter remains a repo-native fixture source for architecture validation. In addition, the repo now includes real NeuroConv-backed CSV and Excel time-interval routes that carry trial-style interval data into NWB trials.

Supported-path policy is now explicit: check the NeuroConv Conversion Gallery first, use a documented NeuroConv interface when one exists, and fall back to direct PyNWB only when NeuroConv does not support the format or the direct PyNWB path is clearly simpler and more maintainable. For direct NWB writing, official PyNWB docs remain the source of truth.

All current implementation slices are backed by tests and documented under `docs/architecture/`.

The current writer is still intentionally narrow overall, but it now carries the core subject/session fields, first-pass device metadata, and first modality-specific acquisition paths for behavior traces via NWB `BehavioralTimeSeries` and behavior position data via `Position`/`SpatialSeries`, with generic `TimeSeries` fallback retained for other modalities. The pipeline now emits a machine-readable JSON validation report artifact alongside the generated outputs, derives an explicit validation review outcome, supports persisted post-execution review decisions, and can persist the latest execution/review state as a resumable JSON session snapshot.

The current application state is still backend-first: there is no user-facing desktop UI yet, and there is still no claim of broad production acquisition-format coverage. The supported text/tabular family now has real NeuroConv-backed CSV and Excel routes, a shared NeuroConv adapter framework exists for additional single-interface routes, and runtime contracts now exist for background execution plus stage/progress/error reporting, but broader supported-format coverage is still ahead.

UI/runtime expectations are now explicit in the plan and partially implemented: long-running conversions can now run through a threaded executor with real stage/progress events, while structured logging, a File menu, status bar, progress bar, and optional log viewer remain the next UI-facing layers to build.

## Local development

Current development and testing should use the dedicated `nwbforge-dev` Conda environment:

```text
powershell -ExecutionPolicy Bypass -File scripts/setup-conda-dev.ps1
powershell -ExecutionPolicy Bypass -File scripts/test-conda-dev.ps1
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
3. Add the next real NeuroConv-backed supported adapter from the approved route catalog, starting with the behavior-pose family.
4. Instrument actionable runtime paths with structured logging on top of the new runtime contracts.
