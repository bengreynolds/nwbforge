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

## End-user workflow

This application is intended for neuroscience researchers who are already comfortable with experimental data structure, acquisition modalities, and metadata interpretation. The UI uses NWB and NeuroConv terminology directly rather than hiding the scientific model behind generic file-import language.

Typical local-app flow:
1. Start a new session from the integrated desktop workspace.
2. Add one or more NeuroConv-supported sources, custom files/folders, or a mixture of both.
3. For supported sources, choose the project file, main file, or root dataset entry that represents the acquisition or processing package.
4. Review the detected dataset bundles, including any unambiguous combined supported workflows the app can recognize from the selected structured sources, then adjust source roles, metadata overrides, and mixed-source conflicts before preview or write.
5. Keep multiple created or opened sessions available in runtime tabs inside the Conversion workspace so you can switch between idle sessions without reopening them.
6. Use the guided conversion workspace messaging to confirm the current step, recommended next action, and what still blocks `Write NWB`.
7. Run preview/build, inspect warnings or blocking issues, then execute NWB conversion when the session is ready.

Mixed-source sessions are a first-class workflow. Route-backed proprietary sources provide structured context, while custom files and folders stay in the same session and are flagged for review when the app cannot confidently attach them to an existing dataset bundle.

## Contributing and license

- Contribution workflow, issue expectations, and maintainer review rules are documented in [CONTRIBUTING.md](CONTRIBUTING.md).
- The repository is licensed under the [MIT License](LICENSE).

## Current repository state

This repository is now in a first-pass local desktop-app stage. The current work has moved beyond pure backend scaffolding: the repo has a real PySide6 shell, supported/custom/hybrid conversion flows, direct-ingest `New Session` behavior, explicit saved-project support, an integrated single-window workspace, and an internal-testing baseline. It is still not packaged or deployment-ready.

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
- [docs/architecture/nwb-viewer.md](docs/architecture/nwb-viewer.md): integrated read-only NWB viewer architecture
- [docs/architecture/custom-workflows.md](docs/architecture/custom-workflows.md): first real repo-owned custom-path workflow baseline
- [docs/architecture/hybrid-workflows.md](docs/architecture/hybrid-workflows.md): first real hybrid-path workflow baseline
- [docs/testing/internal-local-checklist.md](docs/testing/internal-local-checklist.md): current internal local-app smoke and manual testing baseline
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
- Resumable JSON session snapshots for the latest preview, execution, and review state, plus bounded snapshot history for explicit restore points
- Composite validation made up of artifact-policy checks, PyNWB schema validation, and NWB Inspector best-practice checks
- Supported-path pilot adapter for structured `session_manifest.json` sources
- Behavior-stream assembly into NWB `BehavioralTimeSeries` containers, with generic `TimeSeries` fallback for other modalities
- Behavior position assembly into NWB `Position`/`SpatialSeries` containers
- Custom/hybrid inline imaging and ecephys assembly through standard PyNWB `ImageSeries` and `ElectricalSeries` containers when normalized stream metadata is sufficient
- NeuroConv-backed CSV time-interval inspection through `CsvTimeIntervalsInterface`
- NeuroConv-backed Excel time-interval inspection through `ExcelTimeIntervalsInterface`
- Interval-table normalization, mapping, and NWB trial assembly
- Shared NeuroConv adapter framework for single-interface supported routes
- Category-first supported adapter packaging beginning with `supported/behavior/`
- Category-first supported adapter packaging now in place for `supported/behavior/`, `supported/tabular/`, `supported/media/`, `supported/imaging/`, and `supported/ecephys/`
- Family-module text/tabular supported-route implementation with declarative route configs for CSV and Excel
- NeuroConv-backed still-image route through `ImageInterface`
- NeuroConv-backed audio route through `AudioInterface`
- NeuroConv-backed FicTrac behavior route through `FicTracDataInterface`
- NeuroConv-backed DeepLabCut pose-estimation route through `DeepLabCutInterface`
- NeuroConv-backed SLEAP behavior route through `SLEAPInterface`
- NeuroConv-backed LightningPose behavior route through `LightningPoseDataInterface`
- NeuroConv-backed MedPC behavior/task route through `MedPCInterface`
- NeuroConv-backed AlphaOmega ecephys route through `AlphaOmegaRecordingInterface`
- NeuroConv-backed Axon / ABF ecephys route through `AxonRecordingInterface`
- NeuroConv-backed Axona ecephys route through `AxonaRecordingInterface`
- NeuroConv-backed Blackrock ecephys route through `BlackrockRecordingInterface`
- NeuroConv-backed Biocam ecephys route through `BiocamRecordingInterface`
- NeuroConv-backed Bruker TIFF single-plane and multi-plane imaging routes through `BrukerTiffSinglePlaneImagingInterface` and `BrukerTiffMultiPlaneImagingInterface`
- NeuroConv-backed Caiman segmentation route through `CaimanSegmentationInterface`
- NeuroConv-backed Blackrock sorting route through `BlackrockSortingInterface`
- NeuroConv-backed Cell Explorer sorting route through `CellExplorerSortingInterface`
- NeuroConv-backed CNMFE segmentation route through `CnmfeSegmentationInterface`
- NeuroConv-backed EDF ecephys route through `EDFRecordingInterface`
- NeuroConv-backed EXTRACT segmentation route through `ExtractSegmentationInterface`
- NeuroConv-backed external-video route through `ExternalVideoInterface`
- NeuroConv-backed Femtonics imaging route through `FemtonicsImagingInterface`
- NeuroConv-backed HDF5 imaging route through `Hdf5ImagingInterface`
- NeuroConv-backed Inscopix imaging route through `InscopixImagingInterface`
- NeuroConv-backed Inscopix segmentation route through `InscopixSegmentationInterface`
- NeuroConv-backed KiloSort sorting route through `KiloSortSortingInterface`
- NeuroConv-backed MCSRaw ecephys route through `MCSRawRecordingInterface`
- NeuroConv-backed MaxOne ecephys route through `MaxOneRecordingInterface`
- NeuroConv-backed MEArec ecephys route through `MEArecRecordingInterface`
- NeuroConv-backed Micro-Manager TIFF imaging route through `MicroManagerTiffImagingInterface`
- NeuroConv-backed Miniscope imaging route through `MiniscopeImagingInterface`
- NeuroConv-backed Neuralynx ecephys route through `NeuralynxRecordingInterface`
- NeuroConv-backed Neuralynx sorting route through `NeuralynxSortingInterface`
- NeuroConv-backed Neuralynx NVT behavior route through `NeuralynxNvtInterface`
- NeuroConv-backed NeuroScope ecephys route through `NeuroScopeRecordingInterface`
- NeuroConv-backed NeuroScope sorting route through `NeuroScopeSortingInterface`
- NeuroConv-backed OpenEphys Binary analog route through `OpenEphysBinaryAnalogInterface`
- NeuroConv-backed OpenEphys Binary ecephys route through `OpenEphysBinaryRecordingInterface`
- NeuroConv-backed OpenEphys Legacy ecephys route through `OpenEphysLegacyRecordingInterface`
- NeuroConv-backed Plexon ecephys route through `PlexonRecordingInterface`
- NeuroConv-backed Plexon sorting route through `PlexonSortingInterface`
- NeuroConv-backed Plexon2 ecephys route through `Plexon2RecordingInterface`
- NeuroConv-backed Phy sorting route through `PhySortingInterface`
- NeuroConv-backed Scanbox imaging route through `SbxImagingInterface`
- NeuroConv-backed ScanImage imaging route through `ScanImageImagingInterface`
- NeuroConv-backed ScanImage Legacy imaging route through `ScanImageLegacyImagingInterface`
- NeuroConv-backed Suite2p segmentation route through `Suite2pSegmentationInterface`
- NeuroConv-backed Spike2 ecephys route through `Spike2RecordingInterface`
- NeuroConv-backed SpikeGadgets ecephys route through `SpikeGadgetsRecordingInterface`
- NeuroConv-backed SpikeGLX ecephys route through `SpikeGLXRecordingInterface`
- NeuroConv-backed TDT fiber photometry route through `TDTFiberPhotometryInterface`
- NeuroConv-backed TDT ecephys route through `TdtRecordingInterface`
- NeuroConv-backed generic TIFF imaging route through `TiffImagingInterface`
- NeuroConv-backed Thor imaging route through `ThorImagingInterface`
- NeuroConv-backed Intan ecephys route through `IntanRecordingInterface`
- NeuroConv-backed WhiteMatter ecephys route through `WhiteMatterRecordingInterface`
- Dedicated NeuroConv workflow-adapter base plus first real combined-workflow inspection and direct supported-execution baselines for `SpikeGLX & Phy`, `TIFF & Suite2p`, and `OpenEphys Binary & DeepLabCut`
- Direct NeuroConv supported-execution service that can write through NeuroConv while reusing a base `NWBFile` assembled from normalized metadata
- Shared runtime contracts for stage/progress/error reporting and threaded background execution
- Structured runtime logging across the core preview, execution, and supported-route handoff path
- Route-based package install planning with curated presets and persisted selection state
- Route-availability gating so optional supported adapters are only registered when their curated route dependencies are installed
- Backend package-management service contracts for future setup and extension-install screens
- Backend package-install execution service with progress, logging, and failure wrapping
- Threaded runtime executor for package-install work
- Thin `PackageManagementController` binding for future setup and extension-install screens
- Toolkit-agnostic desktop UI models for shell state and package-installer screen state
- Toolkit-agnostic session-assembly screen model for structured source ingest into a draft conversion session, including proprietary NeuroConv-supported sources and custom files/folders
- Toolkit-agnostic conversion-session screen model over preview/execution runtime contracts
- Shared UI observability helpers for log-viewer entries and user-facing error translation
- First concrete PySide6 widget layer with a main window, File menu, status bar, log dock, package-install dialog, and conversion-session widget
- PySide6 `New Session` workspace tab for structured proprietary-plus-custom source ingest, pathway suggestion, source-role assignment, session-wide metadata overrides, and draft session creation
- Explicit direct-ingest project workflow with `Open Project...`, `Save Project`, `Save Project As...`, recent-project history, and project-aware draft recovery
- Explicit direct-ingest project lifecycle actions with `New Project` and confirmed `Delete Project...` behavior in the desktop shell
- Runtime conversion-session tabs so multiple created/opened sessions can stay available inside the main Conversion workspace and be closed individually
- Structured source-type selection in `New Session`, including a `Custom` option plus dynamically available installed NeuroConv route options, with per-path ingest intent persisted through draft state and saved projects
- First-pass route-specific entry validation for structured supported selections, so obviously wrong project/main-file or root-directory choices are rejected before they enter the direct-ingest workspace
- Follow-up direct-ingest hardening so supported entry validation now matches current Bruker, Thor, audio, image, TIFF, and video route semantics, optional adapter exports fail closed when package-gated symbols are absent, and shell/file logging paths tolerate re-entrant listener updates plus non-JSON context values
- Conservative custom-ingest filtering so obviously unsupported files are rejected before they enter the direct-ingest workspace, while route-backed selections keep explicit selected-package context for later validation and review
- Mixed-source grouping that treats selected structured sources as dataset anchors and only attaches nearby custom inputs when the context is narrow enough to stay reviewable
- Workflow-aware direct-ingest grouping that can collapse clean matched supported combinations such as `TIFF + Suite2p` into one reviewable dataset bundle while preserving conservative handling for ambiguous cases
- Structured-bundle member absorption so deterministic dependent files selected alongside a supported canonical entry remain inside that structured source bundle instead of appearing as separate draft sources
- Structured supported-source entry semantics in session assembly, including canonical entry-path kind, entry-role labeling, and persisted validation status for downstream grouping and review
- Direct-ingest group summaries now surface canonical structured-entry identity for supported-anchor bundles so proprietary-plus-custom groups read as dataset bundles instead of unlabeled file clusters
- Source-specific metadata overrides for selected direct-ingest sources, carried through inspection and normalization as user-supplied values
- First-class direct-ingest group summaries with pathway/composition review in the `New Session` workflow
- Dataset-level direct-ingest grouping actions for renaming detected groups, confirming detected bundles, splitting selected sources into individual groups, and creating/moving selected sources into named groups
- Richer direct-ingest group descriptors including dataset kind and anchor path, plus a confirmation gate for reviewable grouped bundles before session creation
- Direct-ingest group explanation in the `New Session` flow, including grouping reason, member summaries, and whole-group split actions
- Opt-in composite UI logging to both the in-app viewer and a JSON-lines file, plus shell-level warning dialogs for translated user-facing errors
- Persisted desktop settings with an integrated `Settings` workspace tab for verbose logging, file-log configuration, snapshot auto-recovery, and history-retention behavior
- Conversion-session review controls for validation outcomes, acknowledgements, and approve/reject submission
- `File -> Import Session JSON (Compatibility)...` support for manifest-backed desktop sessions when compatibility/testing import is needed
- Persisted last-opened session state plus an `Open Recent Imported Session` desktop menu
- Explicit `New Session` and `Reopen Last Imported Session` desktop actions
- Persisted last-used output directory with default NWB output-path suggestions for newly loaded sessions
- App-owned default output location under `.nwbforge/outputs/` when no prior export directory has been chosen
- Real `Choose Output...` desktop save dialog for NWB output selection
- Generated-artifact visibility in the conversion-session panel for NWB, validation-report, and review outputs
- Direct desktop actions to open generated artifacts and their folders from the conversion panel
- Dedicated desktop shortcuts for validation reports and review decisions
- Shell-level user-facing errors for missing or failed artifact-open actions
- A sectioned conversion-session desktop surface with clearer summary, execution, review, and artifact panes
- Run-overview and review-guidance summaries in the conversion panel so stage, output target, issue counts, artifact counts, and expected review actions are visible at a glance
- A tabbed conversion workspace for run overview, review work, metadata review, and artifacts
- Additional runtime session tabs inside the Conversion workspace so users can switch between loaded sessions without leaving the main Conversion surface
- Researcher-facing workflow messaging in the Conversion workspace that now surfaces the current step, recommended next action, and `ready to write` criteria
- Progressive disclosure in the Conversion workspace so advanced review tools plus history/diagnostics stay hidden by default until explicitly requested
- Actionable metadata-review controls that can promote a selected source value into a session-wide override and then require a preview rebuild
- Actionable metadata-review controls that can also apply and clear source-specific overrides before the next preview rebuild
- Manual metadata-review controls that can apply typed session overrides, use selected source values as source-specific overrides, and summarize pending versus resolved override state
- Filterable metadata-review controls with per-field resolution status/history and a clear-all-overrides action for one canonical field
- An integrated read-only NWB viewer tab that can inspect arbitrary `.nwb` files through a lazy PyNWB-backed tree/detail browser
- An optional `nwbwidgets + Panel` rich-preview layer for selected NWB viewer nodes, without making notebook/web tooling part of the base app path
- A shared Qt visual system with reusable header cards, metric cards, restrained color treatment, and cleaner dialog/workspace hierarchy across the local desktop app
- First-pass desktop hardening for smaller displays, including scrollable embedded panels, scrollable tab strips, collapsible split panes, and removal of forced tab jumps caused only by background state updates
- A repo-owned `custom_session.json` custom-path workflow that runs through normalization, reviewable mapping, direct PyNWB assembly, validation, provenance, and desktop execution
- A `hybrid_session.json` hybrid-path workflow that combines supported and custom inputs into one desktop conversion session
- Richer source/session detail presentation in the desktop conversion panel, including pathway, source count, and selected-source details
- Temporary `scripts/run_app.py` launcher for manual desktop testing during development, now wired through the real desktop service composition
- Desktop reopen flow that recovers the latest saved snapshot state for artifacts, validation, review status, and NWB output location
- Desktop history flow that lists saved snapshot versions in the conversion workspace and can restore an earlier saved state
- NeuroConv-first planning for real supported-path adapters, with direct PyNWB reserved for unsupported or unusually custom cases
- An explicit approved NeuroConv-first route catalog in [docs/research/neuroconv-supported-routes.md](docs/research/neuroconv-supported-routes.md)
- Explicit planning requirements for structured logging, background conversion execution, real progress/status events, and a future UI log viewer/status bar

The manifest-backed supported-path pilot adapter remains a repo-native fixture source for architecture validation. In addition, the repo now includes a real NeuroConv-backed text/tabular family that carries CSV and Excel trial-style interval data into NWB trials through one shared family module plus route declarations, plus real NeuroConv-backed still-image, audio, FicTrac, and DeepLabCut routes through NeuroConv's documented interfaces.

Supported-path policy is now explicit: check the NeuroConv Conversion Gallery first, use a documented NeuroConv interface when one exists, and fall back to direct PyNWB only when NeuroConv does not support the format or the direct PyNWB path is clearly simpler and more maintainable. For direct NWB writing, official PyNWB docs remain the source of truth.

For real supported proprietary or acquisition-system formats, the intended execution model is to let the UI and orchestration layers parameterize documented NeuroConv conversion APIs directly. The repo now also supports a bridge mode where it assembles a base `NWBFile` from normalized metadata and then lets NeuroConv append the supported route content into that file. Repository-owned PyNWB assembly remains the fallback path for unsupported formats and the primary path for custom and hybrid conversion flows.

The current desktop app can open checked-in `session_manifest.json`, `custom_session.json`, and `hybrid_session.json` files for internal testing, but that is not the intended long-term primary ingest model. The target product flow is `New Conversion Session`, then structured source selection, inspection, grouping, supported/custom/hybrid classification, and explicit metadata override/review before preview or write. Users can now mix route-backed NeuroConv sources and custom files/folders inside the same session-assembly workspace, and selected supported packages now validate the chosen project/main file or root directory as the canonical structured entry before it is admitted to the draft workspace, while app-owned project files remain reopen/recovery state rather than the scientific source of truth.

All current implementation slices are backed by tests and documented under `docs/architecture/`.

The current writer is still intentionally narrow overall, but it now carries the core subject/session fields, first-pass device metadata, and first modality-specific acquisition paths for behavior traces via NWB `BehavioralTimeSeries`, behavior position data via `Position`/`SpatialSeries`, inline imaging via `ImageSeries`, and inline ecephys via `ElectricalSeries`, with generic `TimeSeries` fallback retained where no stronger standard container is warranted. The pipeline now emits a machine-readable JSON validation report artifact alongside the generated outputs, derives an explicit validation review outcome, supports persisted post-execution review decisions, and the real desktop workflow now persists the latest preview, execution, and review state as resumable JSON session snapshots with bounded version history.

The current application state has now reached the first-pass internal-testing milestone and internal testing is underway. The supported route set includes real NeuroConv-backed CSV, Excel, image, audio, videos, FicTrac, DeepLabCut, SLEAP, LightningPose, MedPC, AlphaOmega, Axon / ABF, Axona, Biocam, Blackrock recording and sorting, Bruker TIFF, Caiman segmentation, Cell Explorer sorting, CNMFE segmentation, EDF, EXTRACT segmentation, Femtonics, HDF5 imaging, Inscopix imaging and segmentation, KiloSort sorting, MCSRaw, MaxOne, MEArec, Micro-Manager TIFF, Miniscope, Neuralynx recording and sorting, Neuralynx NVT, NeuroScope recording and sorting, OpenEphys Binary, OpenEphys Binary Analog, OpenEphys Legacy, Plexon recording and sorting, Plexon2, Phy sorting, Scanbox, ScanImage, ScanImage Legacy, Spike2, SpikeGadgets, SpikeGLX, Suite2p segmentation, TDT, TDT Fiber Photometry, generic TIFF, Thor, Intan, and WhiteMatter conversions; the supported layer now also includes first real combined-workflow inspection and direct supported-execution baselines for `SpikeGLX & Phy`, `TIFF & Suite2p`, and `OpenEphys Binary & DeepLabCut`; a shared NeuroConv adapter framework exists for additional single-interface routes; supported-route packaging uses category-first modules for `supported/behavior/`, `supported/tabular/`, `supported/media/`, `supported/imaging/`, `supported/ecephys/`, `supported/sorting/`, `supported/segmentation/`, `supported/fiber_photometry/`, and `supported/workflows/`; the repo includes a real repo-owned custom-path workflow through `custom_session.json`; and it now also includes a real hybrid-path workflow through `hybrid_session.json`, which combines supported and custom inputs into one desktop conversion session without bypassing the shared adapter/normalization/mapping/provenance model. Runtime contracts exist for background execution, structured logging, stage/progress/error reporting, and workspace-visible progress-history diagnostics; developer setup has a route-based package planning layer with `minimal`, `selected`, and `full` install modes; future setup/package-install UI work has backend `PackageManagementService`, `PackageInstallationService`, `ThreadedPackageInstallationExecutor`, and `PackageManagementController` boundaries to call; the repo now also uses the route package catalog as a dependency gate for optional supported adapters, so package-installed routes become part of the active desktop registry only when their curated dependencies are present in the current environment; the repo includes toolkit-agnostic UI models under `src/nwbforge/ui/`; and it includes a concrete PySide6 widget baseline under `src/nwbforge/ui/qt/` for one integrated shell workspace with a real `New Session` assembly tab, explicit project save/open flows, integrated settings and package-management tabs, an integrated read-only NWB viewer tab, an optional `nwbwidgets + Panel` rich-preview path for selected viewer nodes, and a conversion workspace with sectioned summary/execution/review/artifact areas, richer source details, run-overview metrics, review-guidance summaries, validation/review controls, generated-artifact visibility, direct artifact-open actions, dedicated validation/review report shortcuts, a real `Choose Output...` save dialog, docked log viewer, shell-level warning dialogs, opt-in composite file-plus-viewer logging, a tabbed workspace for run overview, review work, metadata review, artifacts, snapshot history, and runtime diagnostics, actionable metadata-review controls, filterable pending/resolved conflict views, per-field resolution-status/history detail, configurable latest-snapshot auto-recovery, configurable recent-item and snapshot-history retention, explicit snapshot-history restore actions, and latest-state recovery when reopening persisted sessions. A real desktop bootstrap/composition module exists under `src/nwbforge/app/desktop.py`, the desktop shell can import `session_manifest.json`, `custom_session.json`, and `hybrid_session.json` files from `File -> Import Session JSON (Compatibility)...` when compatibility/testing support is needed, start direct-ingest draft assembly from `New Session`, edit source roles, apply session-wide and source-specific metadata overrides before preview/build, merge those overrides at the correct inspection/normalization boundaries, use first-pass source-role precedence during canonical conflict handling, use heuristic dataset-group suggestions during session assembly, surface first-class group summaries in the `New Session` workspace, show dataset kind, anchor-path, grouping reason, and member context for each detected bundle, require confirmation for reviewable grouped bundles before session creation, rename detected groups or create/move selected sources into named groups, split selected sources or a whole selected group back into smaller bundles, detect simple same-stem metadata sidecars during direct ingest, save and reopen explicit direct-ingest projects, order preview provenance inputs by source role, reopen in-progress `New Session` drafts instead of resetting them, persist imported-session and project history through recent menus, recover or explicitly restore saved session snapshots, expose pending mixed-source metadata conflicts in a dedicated post-preview metadata-review tab, apply manual session overrides or promote selected source values into session-wide or source-specific overrides from that review workspace, clear all overrides for one canonical field, default new output paths from the last used output directory, open arbitrary `.nwb` files through the integrated viewer tab, optionally open selected viewer nodes through `nwbwidgets + Panel`, open generated `.nwb` artifacts into that same viewer tab, and start the temporary `scripts/run_app.py` launcher in direct-ingest mode by default unless an explicit `--session`, `--project`, or `--view-nwb` path is supplied. Structured logging now extends beyond the runtime core into review submission, session persistence, direct-ingest state, and core desktop shell file/artifact/project actions, and UI-visible log entries now preserve original event timestamps while the in-app log viewer appends incrementally instead of fully redrawing. The repo now also has `scripts/run_internal_smoke.py` for repeatable supported/custom/hybrid/project smoke testing in the dedicated Conda environment. Release engineering and broader supported-route expansion remain post-first-pass work.

The current planning docs now also include an explicit critical-review audit of the remaining plan-code gaps for internal testing, focused mainly on ingest grouping beyond the current dataset-group action baseline, source-role semantics beyond the current precedence/provenance baseline, conflict resolution beyond the new session-wide metadata-review actions, and remaining structured-logging gaps outside the newly expanded shell/review/persistence coverage.

UI/runtime expectations are now explicit in the plan and partially implemented: long-running conversions can now run through a threaded executor with real stage/progress events, the core runtime path emits structured logs with stable context payloads, the repo has toolkit-agnostic shell/package/conversion/settings screen models plus a shared UI log-sink/error-presentation layer, and the PySide6 widget layer now renders a real File menu, status bar, progress bar, optional log viewer, settings dialog, package-install dialog, conversion-session panel, shell-level warning dialogs, an opt-in composite viewer-plus-file logging path, and a shared polished desktop visual system. Broader desktop-screen coverage, deeper dataset modeling, and app-level log-retention/configuration remain next.

For manual UI testing during development:

```text
conda run -n nwbforge-dev python scripts/run_app.py
conda run -n nwbforge-dev python scripts/run_app.py --session path\\to\\session_manifest.json
conda run -n nwbforge-dev python scripts/run_app.py --session path\\to\\custom_session.json
conda run -n nwbforge-dev python scripts/run_app.py --session path\\to\\hybrid_session.json
conda run -n nwbforge-dev python scripts/run_app.py --project path\\to\\saved-project.nwbforge-project.json
conda run -n nwbforge-dev python scripts/run_app.py --view-nwb path\\to\\file.nwb
```

Optional rich viewer packages:

```text
pip install -e .[viewer_rich]
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

The temporary launcher is a development aid only. It now boots the real desktop service composition directly into the integrated `New Session` ingest workspace unless a user-provided supported/custom/hybrid testing fixture is supplied with `--session`. Those JSON session files are current bootstrap and internal-testing inputs, not the intended long-term primary ingest UX.

If no output directory has been chosen yet, the desktop shell now defaults NWB writes into `.nwbforge/outputs/` instead of the repository root.

## Local development

Current development and testing should use the dedicated `nwbforge-dev` Conda environment:

```text
powershell -ExecutionPolicy Bypass -File scripts/setup-conda-dev.ps1
powershell -ExecutionPolicy Bypass -File scripts/test-conda-dev.ps1
```

The checked-in Conda spec now also supports a direct reproducible local install path, including the editable repo install plus the current broad local route-support profile:

```text
conda env update -n nwbforge-dev -f environment.yml
```

Example route-based setup flows:

```text
powershell -ExecutionPolicy Bypass -File scripts/setup-conda-dev.ps1 -InstallMode selected -Preset common
powershell -ExecutionPolicy Bypass -File scripts/setup-conda-dev.ps1 -InstallMode selected -Preset custom -Routes deeplabcut,scanimage -PersistSelection
powershell -ExecutionPolicy Bypass -File scripts/setup-conda-dev.ps1 -InstallMode selected -Preset custom -Routes lightningpose,videos,hdf5 -PersistSelection
powershell -ExecutionPolicy Bypass -File scripts/setup-conda-dev.ps1 -InstallMode selected -Preset custom -Routes micromanager,miniscope,thor -PersistSelection
powershell -ExecutionPolicy Bypass -File scripts/setup-conda-dev.ps1 -InstallMode selected -Preset custom -Routes brukertiff,femtonics,inscopix,scanimage,scanimage_legacy -PersistSelection
powershell -ExecutionPolicy Bypass -File scripts/setup-conda-dev.ps1 -InstallMode selected -Preset custom -Routes medpc,intan -PersistSelection
powershell -ExecutionPolicy Bypass -File scripts/setup-conda-dev.ps1 -InstallMode selected -Preset custom -Routes biocam,mcsraw,neuroscope,neuralynx,openephys_binary -PersistSelection
powershell -ExecutionPolicy Bypass -File scripts/setup-conda-dev.ps1 -InstallMode selected -Preset custom -Routes axon,edf,spikegadgets,openephys_binary,spikeglx -PersistSelection
powershell -ExecutionPolicy Bypass -File scripts/setup-conda-dev.ps1 -InstallMode selected -Preset custom -Routes alphaomega,axona,blackrock,neuralynx,openephys_legacy,plexon,tdt,whitematter -PersistSelection
powershell -ExecutionPolicy Bypass -File scripts/setup-conda-dev.ps1 -InstallMode selected -Preset custom -Routes caiman,cnmfe,extract,suite2p,tdt_fiber_photometry -PersistSelection
powershell -ExecutionPolicy Bypass -File scripts/setup-conda-dev.ps1 -InstallMode selected -Preset custom -Routes cellexplorer,kilosort,phy -PersistSelection
powershell -ExecutionPolicy Bypass -File scripts/setup-conda-dev.ps1 -InstallMode selected -Preset custom -Routes maxone,mearec,plexon2,scanbox,tiff -PersistSelection
powershell -ExecutionPolicy Bypass -File scripts/setup-conda-dev.ps1 -InstallMode selected -Preset custom -Routes sleap,scanimage -PersistSelection
powershell -ExecutionPolicy Bypass -File scripts/setup-conda-dev.ps1 -InstallMode full -PersistSelection
```

`Spike2` is implemented in code and remains package-gated, but the current Python 3.11 development environment does not satisfy NeuroConv's `sonpy` dependency requirement, so it is not part of the default broad local route profile above.

Some sorting routes are intentionally conservative in the current app:
- `Plexon` sorting and `Neuralynx` sorting are hint-driven because their sources overlap directly with the corresponding recording routes
- `KiloSort` and `Phy` are split by folder markers so the app does not let both auto-claim the same sorting folder

Some segmentation and photometry routes are intentionally conservative in the current app:
- `Caiman`, `CNMFE`, and `EXTRACT` prefer explicit hints, distinctive filenames, or required config rather than claiming arbitrary HDF5 or MATLAB files
- `TDT Fiber Photometry` is hint-driven because the same TDT block folder shape can also represent TDT recording sessions

This environment is intended only for development. Release artifacts should package everything needed so that Conda or virtual environments are not required for end users.

For the current internal-testing baseline:

```text
conda run -n nwbforge-dev python scripts/run_internal_smoke.py
```

## Release direction

Final application releases are planned around a Python-first desktop distribution model:
- package the app with PyInstaller first
- wrap the packaged build in native installers for Windows, macOS, and Linux
- provide an in-app updater that checks GitHub Releases and downloads the correct platform artifact

This keeps the runtime self-contained for lab users while preserving the Python/scientific-stack architecture.

## Next steps

1. Continue structured internal testing in the dedicated Conda environment against real representative datasets.
2. Capture internal-testing findings and convert them into prioritized UI, workflow, performance, and operational fixes.
3. Expand the new structured-source `New Session` workflow from the current route-aware source selector, custom-ingest filtering, heuristic grouping, group summaries, group-kind/anchor descriptors, grouping-reason/member summaries, confirmation gate, current group actions, simple sidecar association, explicit project baseline, and current session/source override model into richer dataset/session modeling, stricter route-entry validation, and field-by-field conflict resolution.
4. Deepen diagnostics and recovery beyond the current snapshot history plus runtime-diagnostics baseline, especially comparison/report UX and richer issue triage bundles.
5. Start release engineering only after the local app is stable enough for a broader user decision/change phase.
