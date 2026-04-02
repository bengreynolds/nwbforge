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
- [docs/architecture/ui-screen-models.md](docs/architecture/ui-screen-models.md): toolkit-agnostic shell and screen-model baseline
- [docs/architecture/ui-runtime-observability.md](docs/architecture/ui-runtime-observability.md): runtime progress/log/error contracts for the desktop shell
- [docs/architecture/ui-widgets.md](docs/architecture/ui-widgets.md): first concrete PySide6 widget baseline
- [docs/architecture/custom-workflows.md](docs/architecture/custom-workflows.md): first real repo-owned custom-path workflow baseline
- [docs/architecture/hybrid-workflows.md](docs/architecture/hybrid-workflows.md): first real hybrid-path workflow baseline
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
- Resumable JSON session snapshots for the latest preview, execution, and review state
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
- Toolkit-agnostic session-assembly screen model for direct file/folder ingest into a draft conversion session
- Toolkit-agnostic conversion-session screen model over preview/execution runtime contracts
- Shared UI observability helpers for log-viewer entries and user-facing error translation
- First concrete PySide6 widget layer with a main window, File menu, status bar, log dock, package-install dialog, and conversion-session widget
- PySide6 `New Session` dialog for direct file/folder ingest, pathway suggestion, and draft session creation
- Opt-in composite UI logging to both the in-app viewer and a JSON-lines file, plus shell-level warning dialogs for translated user-facing errors
- Persisted desktop settings with a real `File -> Settings` dialog for verbose logging and file-log configuration
- Conversion-session review controls for validation outcomes, acknowledgements, and approve/reject submission
- `File -> Open Session...` support for manifest-backed desktop sessions
- Persisted last-opened session state plus an `Open Recent` desktop menu
- Explicit `New Session` and `Reopen Last Session` desktop actions
- Persisted last-used output directory with default NWB output-path suggestions for newly loaded sessions
- App-owned default output location under `.nwbforge/outputs/` when no prior export directory has been chosen
- Real `Choose Output...` desktop save dialog for NWB output selection
- Generated-artifact visibility in the conversion-session panel for NWB, validation-report, and review outputs
- Direct desktop actions to open generated artifacts and their folders from the conversion panel
- Dedicated desktop shortcuts for validation reports and review decisions
- Shell-level user-facing errors for missing or failed artifact-open actions
- A sectioned conversion-session desktop surface with clearer summary, execution, review, and artifact panes
- Run-overview and review-guidance summaries in the conversion panel so stage, output target, issue counts, artifact counts, and expected review actions are visible at a glance
- A tabbed conversion workspace for run overview, review work, and artifacts
- A repo-owned `custom_session.json` custom-path workflow that runs through normalization, reviewable mapping, direct PyNWB assembly, validation, provenance, and desktop execution
- A `hybrid_session.json` hybrid-path workflow that combines supported and custom inputs into one desktop conversion session
- Richer source/session detail presentation in the desktop conversion panel, including pathway, source count, and selected-source details
- Temporary `scripts/run_app.py` launcher for manual desktop testing during development, now wired through the real desktop service composition
- Desktop reopen flow that recovers the latest saved snapshot state for artifacts, validation, review status, and NWB output location
- NeuroConv-first planning for real supported-path adapters, with direct PyNWB reserved for unsupported or unusually custom cases
- An explicit approved NeuroConv-first route catalog in [docs/research/neuroconv-supported-routes.md](docs/research/neuroconv-supported-routes.md)
- Explicit planning requirements for structured logging, background conversion execution, real progress/status events, and a future UI log viewer/status bar

The manifest-backed supported-path pilot adapter remains a repo-native fixture source for architecture validation. In addition, the repo now includes a real NeuroConv-backed text/tabular family that carries CSV and Excel trial-style interval data into NWB trials through one shared family module plus route declarations, plus real NeuroConv-backed still-image, audio, FicTrac, and DeepLabCut routes through NeuroConv's documented interfaces.

Supported-path policy is now explicit: check the NeuroConv Conversion Gallery first, use a documented NeuroConv interface when one exists, and fall back to direct PyNWB only when NeuroConv does not support the format or the direct PyNWB path is clearly simpler and more maintainable. For direct NWB writing, official PyNWB docs remain the source of truth.

For real supported proprietary or acquisition-system formats, the intended execution model is to let the UI and orchestration layers parameterize documented NeuroConv conversion APIs directly. The repo now also supports a bridge mode where it assembles a base `NWBFile` from normalized metadata and then lets NeuroConv append the supported route content into that file. Repository-owned PyNWB assembly remains the fallback path for unsupported formats and the primary path for custom and hybrid conversion flows.

The current desktop app can open checked-in `session_manifest.json`, `custom_session.json`, and `hybrid_session.json` files for internal testing, but that is not the intended long-term primary ingest model. The target product flow is `New Conversion Session`, then direct file/folder ingestion, inspection, grouping, supported/custom/hybrid classification, and explicit metadata override/review before preview or write. App-owned session/project files may remain useful later for reopen/recovery or explicit `Save Project` behavior, but they are not meant to be the required hand-authored starting point for users.

All current implementation slices are backed by tests and documented under `docs/architecture/`.

The current writer is still intentionally narrow overall, but it now carries the core subject/session fields, first-pass device metadata, and first modality-specific acquisition paths for behavior traces via NWB `BehavioralTimeSeries` and behavior position data via `Position`/`SpatialSeries`, with generic `TimeSeries` fallback retained for other modalities. The pipeline now emits a machine-readable JSON validation report artifact alongside the generated outputs, derives an explicit validation review outcome, supports persisted post-execution review decisions, and the real desktop workflow now persists the latest preview, execution, and review state as a resumable JSON session snapshot.

The current application state has now reached the first-pass internal-testing milestone. The supported route set includes real NeuroConv-backed CSV, Excel, image, audio, FicTrac, and DeepLabCut conversions; a shared NeuroConv adapter framework exists for additional single-interface routes; supported-route packaging uses category-first modules for both `supported/behavior/` and `supported/tabular/`; a dedicated workflow base exists for future combined NeuroConv pipelines; the repo includes a real repo-owned custom-path workflow through `custom_session.json`; and it now also includes a real hybrid-path workflow through `hybrid_session.json`, which combines supported and custom inputs into one desktop conversion session without bypassing the shared adapter/normalization/mapping/provenance model. Runtime contracts exist for background execution, structured logging, and stage/progress/error reporting; developer setup has a route-based package planning layer with `minimal`, `selected`, and `full` install modes; future setup/package-install UI work has backend `PackageManagementService`, `PackageInstallationService`, `ThreadedPackageInstallationExecutor`, and `PackageManagementController` boundaries to call; the repo includes toolkit-agnostic UI models under `src/nwbforge/ui/`; and it includes a concrete PySide6 widget baseline under `src/nwbforge/ui/qt/` for the shell, a real `New Session` assembly dialog, settings dialog, package-install dialog, and a conversion workspace with sectioned summary/execution/review/artifact areas, richer source details, run-overview metrics, review-guidance summaries, validation/review controls, generated-artifact visibility, direct artifact-open actions, dedicated validation/review report shortcuts, a real `Choose Output...` save dialog, docked log viewer, shell-level warning dialogs, opt-in composite file-plus-viewer logging, a tabbed workspace for run overview, review work, and artifacts, and latest-state recovery when reopening persisted sessions. A real desktop bootstrap/composition module exists under `src/nwbforge/app/desktop.py`, the desktop shell can open `session_manifest.json`, `custom_session.json`, and `hybrid_session.json` sessions from `File -> Open Session...`, start direct-ingest draft assembly from `New Session`, reopen saved startup state with `Reopen Last Session`, persist session history through `Open Recent`, recover the latest saved session snapshot on reopen, default new output paths from the last used output directory, and the temporary `scripts/run_app.py` launcher prefers the last-opened session when no explicit path is provided. The repo is now ready for internal first-pass testing in the dedicated Conda environment. Release engineering and broader supported-route expansion remain post-first-pass work.

UI/runtime expectations are now explicit in the plan and partially implemented: long-running conversions can now run through a threaded executor with real stage/progress events, the core runtime path emits structured logs with stable context payloads, the repo has toolkit-agnostic shell/package/conversion/settings screen models plus a shared UI log-sink/error-presentation layer, and the PySide6 widget layer now renders a real File menu, status bar, progress bar, optional log viewer, settings dialog, package-install dialog, conversion-session panel, shell-level warning dialogs, and an opt-in composite viewer-plus-file logging path. Broader desktop-screen coverage, richer dialog treatment, and app-level log-retention/configuration remain next.

For manual UI testing during development:

```text
conda run -n nwbforge-dev python scripts/run_app.py
conda run -n nwbforge-dev python scripts/run_app.py --session path\\to\\session_manifest.json
conda run -n nwbforge-dev python scripts/run_app.py --session path\\to\\custom_session.json
conda run -n nwbforge-dev python scripts/run_app.py --session path\\to\\hybrid_session.json
```

Checked-in example sessions are available under:
- `examples/sessions/supported/session_manifest.json`
- `examples/sessions/custom/custom_session.json`
- `examples/sessions/hybrid/hybrid_session.json`

Example launch commands:

```text
conda run -n nwbforge-dev python scripts/run_app.py --session examples\sessions\supported\session_manifest.json
conda run -n nwbforge-dev python scripts/run_app.py --session examples\sessions\custom\custom_session.json
conda run -n nwbforge-dev python scripts/run_app.py --session examples\sessions\hybrid\hybrid_session.json
```

The temporary launcher is a development aid only. It now boots the real desktop service composition and loads either a user-provided supported/custom/hybrid testing fixture or a generated demo manifest, without changing the long-term packaging plan. Those JSON session files are current bootstrap and internal-testing inputs, not the intended long-term primary ingest UX.

If no output directory has been chosen yet, the desktop shell now defaults NWB writes into `.nwbforge/outputs/` instead of the repository root.

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

## Next steps

1. Begin structured internal testing in the dedicated Conda environment.
2. Capture internal-testing findings and convert them into prioritized UI, workflow, and operational fixes.
3. Expand the new direct-ingest `New Session` workflow with richer grouping, source-role editing, and metadata overrides.
4. Harden operational concerns such as richer review history, multi-snapshot recovery flows, and report visibility on top of the current latest-state persistence baseline.
5. Start release engineering only after the first-pass testing round confirms the product direction.
