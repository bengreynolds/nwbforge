# Decisions

This is the repository's canonical decision log. Historical decisions and reversals should be recorded here as the project evolves.

## 2026-03-31

### DEC-001: Treat supported, custom, and hybrid conversion pathways as first-class concepts
Status: Accepted

Reasoning:
- The workflow, risk profile, and review needs differ materially across these cases.
- A single undifferentiated `conversion` pipeline would hide critical complexity and make UX and validation weaker.

Consequences:
- Session orchestration must branch by pathway
- Reports should state the pathway explicitly
- Tests should cover each pathway separately

### DEC-002: Keep metadata normalization separate from source adapters and NWB assembly
Status: Accepted

Reasoning:
- Source naming and NWB semantics should not be coupled directly.
- A dedicated normalization layer improves reuse, traceability, and lab-profile support.

Consequences:
- Canonical internal models become a core design asset
- Source adapters remain focused on extraction
- NWB assembly can target normalized models instead of raw parser output

### DEC-003: Use NeuroConv first for supported ingestion, PyNWB for custom or hybrid assembly
Status: Accepted

Reasoning:
- Existing NWB ecosystem tooling should be reused wherever it already fits.
- Lower-level PyNWB control is still necessary for unsupported and hybrid cases.

Consequences:
- Supported-path adapters should evaluate NeuroConv before custom parsing is written
- The architecture must accommodate both direct and lower-level assembly paths

### DEC-004: Use `main` as the default integration branch and retire `master`
Status: Accepted

Reasoning:
- Repository conventions should be explicit from the start.
- The working branch model already centers development on `dev` with PR-based integration.

Consequences:
- `main` is the protected integration target
- `dev` remains the active working branch
- Documentation should not refer to `master`

### DEC-005: Start implementation by codifying canonical domain contracts
Status: Accepted

Reasoning:
- The architecture depends on stable boundaries between raw sources, normalized metadata, mapping plans, provenance, and validation.
- Defining these contracts first reduces downstream coupling when adapters and services are added.

Consequences:
- Initial implementation lives in `src/nwbforge/domain/`
- Early tests target immutable contract behavior rather than conversion logic
- Later orchestration, adapter, and NWB-writing layers should depend on these models instead of inventing parallel payload shapes

### DEC-006: Make adapters and orchestration services contract-first
Status: Accepted

Reasoning:
- Supported, custom, and hybrid workflows need a shared boundary between raw source inspection and downstream normalization.
- The registry and service interfaces should stabilize before concrete adapters or application services are added.

Consequences:
- Adapter output flows through `ExtractedField` and `ExtractionResult`
- Adapter discovery is centralized in `AdapterRegistry`
- Orchestration-facing services should implement explicit protocols rather than exchange untyped dictionaries

### DEC-007: Start concrete application services with inspection dispatch and provenance assembly
Status: Accepted

Reasoning:
- These services are deterministic and low-risk, but they exercise the new adapter and domain boundaries in a real way.
- They provide immediate orchestration value without forcing premature normalization or NWB-mapping logic.

Consequences:
- `RegistrySourceInspectionService` becomes the default path for adapter-backed source inspection
- `SessionProvenanceService` becomes the first concrete provenance builder
- Later services should follow the same narrow, contract-driven pattern

### DEC-008: Start normalization with a conservative alias-driven rule set
Status: Accepted

Reasoning:
- The project needs a concrete normalization layer, but broad ontology inference would be premature at this stage.
- A small declarative alias set gives us useful behavior while keeping assumptions reviewable and easy to change.

Consequences:
- `RuleBasedNormalizationService` is the current normalization baseline
- Unknown or conflicting fields are preserved and marked for review
- Lab-profile overrides and broader device/stream normalization remain future work

### DEC-009: Start mapping with an explicit reviewable plan, not direct NWB construction
Status: Accepted

Reasoning:
- The architecture depends on separating mapping intent from NWB assembly.
- Early mapping logic should make assumptions visible before any writer layer exists.

Consequences:
- `RuleBasedMappingPlanner` emits `MappingDecision` and `ReviewIssue` records only
- Required-field gaps surface as blocking issues in the plan
- Identifier generation remains an explicit reviewable transform until assembly policy is settled

### DEC-010: Make `planning.md`, `AGENTS.md`, and `decisions.md` the continuously maintained core docs
Status: Accepted

Reasoning:
- Long-lived agent collaboration depends on a small set of canonical documents that are always current.
- Repository guidance needs one clear decision source instead of split, drifting references.

Consequences:
- `planning.md`, `AGENTS.md`, and `decisions.md` are mandatory maintenance targets
- `docs/decision-log.md` remains a compatibility path only
- Future architectural and process decisions should be recorded in `decisions.md`

### DEC-011: Treat release engineering as a first-class architecture concern
Status: Accepted

Reasoning:
- The product is intended for department-wide, non-technical users and must ship as a production-grade desktop application.
- Installer, updater, and rollback behavior materially affect architecture, packaging, and user trust.

Consequences:
- Release and update design must be specified in planning before implementation
- Cross-platform installers, update behavior, and versioning become core architecture concerns
- Future UI and distribution choices must be evaluated against installer and updater requirements

### DEC-012: Start validation with artifact-policy checks before toolchain integration
Status: Accepted

Reasoning:
- The system needs a concrete validation layer now, but PyNWB and NWB Inspector should be added deliberately rather than as an incidental dependency spike.
- Artifact-level checks provide immediate value and exercise the validation boundary cleanly.

Consequences:
- `ArtifactValidationService` is the current validation baseline
- Missing, empty, or ambiguous output artifacts can be surfaced before schema validation is integrated
- PyNWB and NWB Inspector remain the next validation-expansion steps

### DEC-013: Use a repo-native manifest adapter as the first supported-path pilot
Status: Accepted

Reasoning:
- The project needs an end-to-end supported-path slice now, but no real departmental source format has been selected and scoped yet.
- A small structured manifest source lets the architecture be exercised honestly without pretending a real acquisition format is already supported.

Consequences:
- `SessionManifestAdapter` is the first supported-path pilot adapter
- Integration tests can now cover inspection through mapping with a deterministic source fixture
- The manifest path remains the metadata and inline-stream fixture route even after real NeuroConv-backed routes are added

### DEC-014: Represent preview and execution as separate orchestration stages
Status: Accepted

Reasoning:
- The product must preserve transparency around what can be reviewed before writing outputs and what happens after outputs exist.
- A single opaque run call would hide important checkpoints needed for UI-driven workflows and future approval gates.

Consequences:
- `ConversionPipelineService` exposes `build_preview` and `evaluate_outputs` separately
- Preview and execution results are explicit application-layer models
- Future writer integration should fit between preview generation and output evaluation

### DEC-015: Introduce PyNWB as the first real NWB writer dependency
Status: Accepted

Reasoning:
- The project needs a real NWB-writing path to validate the architecture end to end.
- A thin PyNWB-backed writer provides a truthful implementation step without overcommitting on broader format support.

Consequences:
- `pynwb` is now a declared project dependency
- `PyNWBAssemblyService` becomes the current writer baseline
- Assembly remains intentionally narrow until richer supported formats and validation integrations are added

### DEC-016: Use a dedicated Conda environment for development, but never require it at release time
Status: Accepted

Reasoning:
- The project needs an isolated local runtime now without interfering with existing Python installations.
- End users of the released product should not be asked to manage Conda or virtual environments.

Consequences:
- Current installs and tests should use the dedicated `nwbforge-dev` Conda environment
- Development helpers should disable user-site package leakage
- Release packaging must remain fully self-contained

### DEC-017: Layer PyNWB schema validation on top of artifact-policy checks
Status: Accepted

Reasoning:
- A generated `.nwb` file should be checked for schema validity before the project adds broader best-practice inspection.
- Artifact existence checks and schema validation solve different problems and should remain composable.

Consequences:
- Validation now combines `ArtifactValidationService` with `PyNWBSchemaValidationService`
- Placeholder or unreadable `.nwb` files now fail validation even if they exist on disk
- NWB Inspector remains a separate follow-on integration rather than being folded into schema validation

### DEC-018: Use a PyInstaller-first release pipeline wrapped by native installers
Status: Accepted

Reasoning:
- The product is a desktop-oriented Python application with a likely scientific Python stack.
- End users in research labs should not be required to install Python, Conda, or manage environments manually.
- A PyInstaller-first payload preserves a Python-centric architecture while still allowing native installer and updater workflows.

Consequences:
- Final releases must package the app with PyInstaller before any installer wrapping step
- Windows, macOS, and Linux distributions must wrap the PyInstaller build in native installers or installable packages
- The in-app updater should resolve and download release assets from GitHub Releases
- Release engineering must account for scientific Python packaging risks such as compiled dependencies, larger bundles, and platform-specific signing behavior

### DEC-019: Keep NWB Inspector best-practice checks separate from PyNWB schema validation
Status: Accepted

Reasoning:
- PyNWB schema validation and NWB Inspector answer different questions and should remain independently composable.
- The current writer needs visibility into best-practice-critical gaps without hiding them behind schema-only success.

Consequences:
- Validation now composes `ArtifactValidationService`, `PyNWBSchemaValidationService`, and `NWBInspectorValidationService`
- `NWBInspectorValidationService` runs with `skip_validate=True` to avoid duplicating PyNWB schema checks
- Writer-generated NWB files can now fail execution on NWB Inspector critical findings even when schema validation passes

### DEC-020: Expand the initial writer path with richer subject and session metadata before devices or acquisitions
Status: Accepted

Reasoning:
- The next concrete value after validation integration was to close best-practice-critical gaps in the existing writer path, not jump immediately into devices or multimodal assembly.
- The manifest-backed supported pilot can now be exercised more honestly when source metadata includes experiment description and key subject fields.

Consequences:
- Canonical normalization now includes `session.experiment_description`, `subject.description`, and `subject.date_of_birth`
- The mapping planner and PyNWB writer now carry those fields through to NWB objects
- The next assembly expansion should move to devices, acquisition streams, and richer modality content rather than revisiting these core subject/session fields first

### DEC-021: Add device support to the manifest-backed supported path before acquisition streams
Status: Accepted

Reasoning:
- Devices are already first-class canonical models in the architecture and were the next narrow assembly slice after richer subject/session metadata.
- This expands the supported-path pilot meaningfully without yet taking on timeseries or multimodal stream assembly complexity.

Consequences:
- `SessionManifestAdapter` now flattens list-of-dict device records into stable extracted fields
- Rule-based normalization, mapping, and assembly now carry device metadata through to `NWBFile.create_device`
- Device manufacturer is currently written through PyNWB's deprecated `manufacturer` argument as a temporary bridge pending a fuller `DeviceModel` design

### DEC-022: Add a generic inline TimeSeries acquisition path before modality-specific stream types
Status: Accepted

Reasoning:
- The next narrow assembly slice after devices was to prove acquisition content can move end to end through the architecture without yet committing to modality-specific NWB containers.
- A generic `TimeSeries` writer path is sufficient for the repo-native manifest pilot and keeps the scope reviewable.

Consequences:
- Manifest acquisition stream records now normalize into `AcquisitionStream` objects and map into explicit `TimeSeries[...]` decisions
- The current writer supports inline acquisition `data`, `unit`, and either `rate` or `timestamps`
- Richer modality-specific container choices remain a follow-on design step rather than being guessed at in the pilot path

### DEC-023: Emit machine-readable validation reports as separate pipeline artifacts
Status: Accepted

Reasoning:
- The current validation stack is useful, but downstream UI and review workflows need a stable artifact rather than only in-memory summaries.
- Report generation should remain separate from validators so validation and reporting can evolve independently.

Consequences:
- The pipeline now writes a JSON validation report artifact after validation completes
- Validation report generation is modeled as a separate service instead of being embedded inside validation services
- Generated outputs now include both primary conversion artifacts and a machine-readable review/report artifact

### DEC-024: Derive an explicit validation review outcome from raw validation summaries
Status: Accepted

Reasoning:
- UI and workflow layers should not have to reverse-engineer repository policy from raw error and warning lists.
- The project needs a stable place to encode the distinction between passing, review-required, and blocked validation states before approval workflows are added.

Consequences:
- Validation policy is now modeled as a separate service from validators and report generation
- Pipeline execution now carries a review outcome in addition to the raw `ValidationSummary`
- Machine-readable validation reports now include explicit review-outcome fields for downstream UI and automation use

### DEC-025: Persist post-execution review decisions as separate artifacts before broader session persistence exists
Status: Accepted

Reasoning:
- The project needs an auditable approval workflow now, but full resumable session persistence is still undecided.
- Persisting review decisions as explicit artifacts provides traceability without forcing a storage-engine decision too early.

Consequences:
- Review approval and rejection now flow through a dedicated application service and artifact writer
- Warning-only executions require explicit acknowledgement before approval
- Blocked executions require an explicit override and rationale before approval can be persisted
- Review history is still file-artifact based and remains a future persistence concern

### DEC-026: Start resumable session persistence with JSON snapshots before choosing a richer local store
Status: Accepted

Reasoning:
- The product now has enough execution and review state that reconstructing it from separate artifacts alone is too indirect for UI workflows.
- A file-backed snapshot store provides resumability without prematurely locking the project into SQLite or service-backed persistence.

Consequences:
- Session persistence now has an explicit domain contract and app-layer service
- The current persistence backend stores the latest session snapshot as JSON under a configurable base directory
- Preview-stage state and full revision history remain future work rather than being improvised into the first snapshot format

### DEC-027: Add behavior-specific acquisition containers before broader modality coverage
Status: Accepted

Reasoning:
- The manifest-backed pilot already includes behavior streams, so behavior is the narrowest truthful modality-specific step beyond flat `TimeSeries`.
- `BehavioralTimeSeries` improves output semantics without forcing premature commitments on ecephys, ophys, or multimodal merge structure.

Consequences:
- Behavior streams now write into `BehavioralTimeSeries` acquisition containers
- The mapping planner now emits behavior-specific acquisition target paths for those streams
- Non-behavior streams still use the generic `TimeSeries` fallback until additional modality policies are introduced

### DEC-028: Split behavior acquisition assembly into trace and position subtypes
Status: Accepted

Reasoning:
- Behavior data is not a single container shape, and position data has a clearer NWB-native representation than a generic trace.
- Adding `Position` and `SpatialSeries` is a natural extension of the current behavior baseline without forcing a larger modality refactor.

Consequences:
- Behavior streams with `behavior_type=position` now write into `Position` containers with `SpatialSeries`
- Behavior streams without that subtype remain in `BehavioralTimeSeries`
- The manifest-backed pilot now exercises two distinct behavior assembly paths instead of one generic behavior path

### DEC-029: Make NeuroConv the required first-stop dependency for supported-path conversion work
Status: Accepted

Reasoning:
- NeuroConv is specifically designed to convert many supported neurophysiology formats into NWB and documents supported routes through the Conversion Gallery.
- The repository should not default to manual PyNWB conversion work when a documented NeuroConv interface already exists.
- PyNWB should remain the documented fallback and custom/hybrid assembly layer, not the first choice for every supported format.

Consequences:
- Future supported-path implementation must check NeuroConv support before manual converter design
- `neuroconv` became the declared dependency when the first real supported-path adapter slice landed
- Direct PyNWB construction remains the fallback for unsupported or unusually custom cases
- PyNWB documentation is the required source of truth for low-level NWB API usage and container placement

### DEC-030: Maintain an explicit approved NeuroConv route catalog in the repository
Status: Accepted

Reasoning:
- The project now has a concrete set of NeuroConv-supported formats and workflows that should default future implementation choices.
- Encoding that list in one canonical repository note is more reliable than re-deciding support assumptions ad hoc in each implementation task.

Consequences:
- The route catalog lives in `docs/research/neuroconv-supported-routes.md`
- When an input mentions a listed software package or workflow, NeuroConv should be investigated first and used whenever feasible
- Format-specific caveats still need to be checked against the exact NeuroConv gallery page before implementation

### DEC-031: Use NeuroConv CSV time intervals as the first real supported-path implementation
Status: Accepted

Reasoning:
- The project needed one truthful supported-path implementation that uses NeuroConv directly without pulling in a larger binary acquisition stack too early.
- NeuroConv's documented `CsvTimeIntervalsInterface` provides a stable, low-friction route for interval and trial data and fits the current architecture cleanly as a first real supported adapter.
- CSV interval data also forces the architecture to handle NWB trials and `TimeIntervals`, which broadens the writer beyond acquisition traces without requiring premature ecephys or ophys design commitments.

Consequences:
- `neuroconv` is now a declared dependency
- `NeuroConvCsvTimeIntervalsAdapter` is the first real NeuroConv-backed supported adapter in the repo
- The canonical normalization, mapping, and assembly layers now include interval-table and trial-row support targeting NWB trials
- The next supported-path increment should add another real NeuroConv route rather than revisiting whether NeuroConv belongs in the stack

### DEC-032: Build a shared NeuroConv interface-adapter framework before scaling the approved route catalog
Status: Accepted

Reasoning:
- The approved NeuroConv route catalog is too large and heterogeneous to implement as unrelated one-off adapter classes.
- NeuroConv's `DataInterface` pattern is the natural unit for single-source supported routes, while combined gallery workflows need a separate orchestration-aware layer.
- A shared framework reduces repeated source-config parsing, interface setup, extraction helpers, and test shape across the supported catalog.

Consequences:
- New single-interface NeuroConv routes should inherit from a shared framework rather than duplicating wrapper logic
- The current CSV intervals adapter should be refactored onto that framework as the first proof case
- Combined gallery workflows will need a distinct workflow-adapter layer instead of being forced into single-source adapter abstractions

### DEC-033: Treat logging, progress, and background execution as first-class application contracts
Status: Accepted

Reasoning:
- The product is intended to become a desktop application for non-technical lab users, so responsiveness and runtime transparency are part of the core user experience rather than optional polish.
- Structured logging, stage/status reporting, and user-facing error propagation need to be designed into the application boundary before the UI shell is built.
- If these concerns are left implicit, the likely result is thread-blocking conversions, print-based diagnostics, weak progress reporting, and inconsistent UI error behavior.

Consequences:
- actionable runtime paths should use structured logging rather than print statements
- long-running conversion work must run through background execution infrastructure
- progress reporting must emit real stage and percentage updates that the UI can bind to status and progress components
- the desktop shell should include a File menu, status bar, progress bar, and optional log viewer on top of explicit runtime contracts

### DEC-034: Share one NeuroConv tabular-interval adapter path across CSV and Excel
Status: Accepted

Reasoning:
- CSV and Excel time-interval routes in NeuroConv target the same NWB trials/TimeIntervals semantics and should not diverge into duplicate adapter logic.
- A shared tabular-interval adapter layer keeps extraction rules, warning behavior, and downstream normalization contracts aligned across the text/tabular family.

Consequences:
- CSV and Excel now share `NeuroConvTabularTimeIntervalsAdapter`
- warning and extraction behavior for missing `stop_time` is now family-level rather than CSV-specific
- additional text/tabular interval routes should reuse the same family contract when their NWB target is equivalent

### DEC-035: Prefer family modules and route declarations over one-file-per-route wrappers when semantics are shared
Status: Accepted

Reasoning:
- A large supported-route catalog will become noisy and harder to maintain if every entry becomes a dedicated module even when the route differences are mostly declarative.
- The architecture should encode semantic differences, not turn interface names alone into a module explosion.
- Combined NeuroConv workflows are architecturally different from single-interface routes and should have their own layer rather than being jammed into the same shape.

Consequences:
- supported routes that mainly differ by interface class, suffixes, or light source sniffing should prefer family registries and config declarations
- only routes with materially different extraction, normalization, mapping, or workflow behavior should grow dedicated modules
- the current text/tabular family should migrate away from separate route-specific modules

### DEC-036: Make combined NeuroConv workflows a first-class adapter layer
Status: Accepted

Reasoning:
- Combined gallery routes such as `SpikeGLX & Phy` or `Tiff & Suite2p` are structurally different from single-interface sources and should not be forced through single-source adapter contracts.
- The repository needs a clear place to encode multi-source matching and future combined-workflow extraction behavior before those routes are implemented.

Consequences:
- workflow routes should implement a dedicated multi-source contract rather than masquerading as ordinary source adapters
- the NeuroConv framework now includes declarative workflow source requirements and a base workflow adapter
- future combined supported routes should land on the workflow layer instead of inventing ad hoc orchestration-only matching logic

### DEC-037: Use direct NeuroConv execution as the primary write path for supported acquisition routes
Status: Accepted

Reasoning:
- For formats that NeuroConv already supports, the simplest and most maintainable implementation is to orchestrate NeuroConv's documented conversion APIs rather than rebuilding those conversions in repository-owned PyNWB code.
- The UI should collect metadata, user choices, and overrides, then pass them into NeuroConv rather than duplicating proven interface-level logic for supported systems.
- Repository-owned PyNWB assembly is still necessary, but it should be focused on fallback, custom, and hybrid paths instead of replacing supported NeuroConv execution.

Consequences:
- supported proprietary and acquisition-system routes should prefer direct NeuroConv execution over custom writer implementations
- adapter and orchestration work for supported routes should focus on route detection, parameter collection, metadata overrides, and workflow handoff into NeuroConv
- repository-owned PyNWB assembly remains the primary path for custom and hybrid workflows and the fallback when NeuroConv does not cover the route cleanly

### DEC-038: Build a base `NWBFile` in PyNWB, then let NeuroConv append supported route content
Status: Accepted

Reasoning:
- Supported sessions may still include normalized metadata and repo-owned assembled content that should not be discarded when the primary modality is written by NeuroConv.
- NeuroConv's documented conversion APIs accept an `nwbfile` argument, which provides a clean bridge between the repository's canonical metadata pipeline and NeuroConv's supported writer logic.
- This is simpler and more maintainable than trying to reimplement supported modality writing locally or splitting supported sessions into disjoint outputs.

Consequences:
- the supported execution path now builds a base `NWBFile` through `PyNWBAssemblyService.build_nwbfile`
- direct NeuroConv routes can append their supported modality into that base file
- `PyNWBAssemblyService` remains useful for supported routes even when NeuroConv owns the final modality write path

### DEC-039: Start structured logging at the runtime boundary before UI implementation
Status: Accepted

Reasoning:
- The repository now has enough asynchronous execution and multi-path conversion behavior that failures and stage transitions need stable log context, not ad hoc message strings.
- Logging should start at the runtime boundary where preview, execution, and direct NeuroConv handoff occur, because those are the paths the future UI log viewer and support workflows will depend on first.

Consequences:
- `ConversionPipelineService`, `NeuroConvSupportedExecutionService`, and `ThreadedConversionExecutor` now emit structured log records with stable context payloads
- runtime observability can expand incrementally from the current core services into persistence, review, and plugin paths
- log viewer and verbose-mode UI work can build on an existing structured logging baseline rather than inventing one later

### DEC-040: Let supported behavior routes keep NeuroConv-owned processing semantics instead of remapping them locally
Status: Accepted

Reasoning:
- Behavior routes such as FicTrac and DeepLabCut already have documented NeuroConv interfaces that write richer NWB behavior-processing structures than the repository's current fallback writer path.
- Rebuilding those route-specific conversions locally would add complexity while producing a weaker result than the documented NeuroConv API.
- The repository's value for these supported routes is orchestration, metadata collection, validation, and multi-source session composition, not replacing NeuroConv's behavior writers.

Consequences:
- Supported behavior routes should prefer direct NeuroConv execution into processing modules when NeuroConv documents the route.
- The future UI should expose route-specific inputs such as subject identity, optional config files, and similar interface parameters for supported behavior routes.
- Repository-owned PyNWB behavior assembly remains the fallback and hybrid path, not the preferred implementation for supported NeuroConv behavior interfaces.

### DEC-041: Group supported adapters by category before software name when semantics are shared
Status: Accepted

Reasoning:
- A flat `supported/` package with one file per software route drifts toward module sprawl and hides the more important semantic grouping by category.
- Supported-route maintenance is easier when behavior, tabular, imaging, ecephys, and workflow families each have a clear package boundary.
- Category-first packaging still allows route-specific declarations, but it prevents file layout from becoming the de facto architecture.

Consequences:
- supported behavior routes now live under `src/nwbforge/adapters/supported/behavior/`
- future supported families should prefer category packages plus family modules before introducing software-named top-level files
- public adapter exports can remain stable while internal package layout continues migrating toward category-first structure

### DEC-042: Treat bounded parallel Codex subagents as a development workflow rule, not an app runtime feature
Status: Accepted

Reasoning:
- The request for parallel agents refers to Codex subagents used during repository development, not to the end-user desktop application.
- Encoding this as application runtime behavior would mix development tooling concerns into the product architecture without improving the shipped app.
- A bounded repository workflow rule is enough: parallelize only independent work, cap concurrency, and merge results deterministically.

Consequences:
- repository guidance should cap parallel Codex subagents at 3 concurrent workers
- subagent tasks should have isolated ownership and non-overlapping write scopes
- failed or ambiguous subagent results should fall back to sequential local resolution
- application runtime code should not be described or implemented as “agent orchestration” for this requirement

### DEC-043: Use route-name package catalogs and install presets for setup and future UI package management
Status: Accepted

Reasoning:
- NeuroConv support often depends on route-specific extras or companion packages, so all-or-nothing setup is inefficient for development and too opaque for future UI package installation.
- User-facing selection should be framed around route names such as `DeepLabCut` or `ScanImage`, not raw requirement strings.
- The same curated route catalog should drive developer bootstrap and future UI package installation so install terminology and behavior do not drift.

Consequences:
- dependency groups should be organized around route-name install targets and presets
- the dedicated Conda setup flow should support `minimal`, `selected`, and `full` install modes
- package selection should persist outside tracked source files so repeated setup can reuse the last choice
- future UI package management should use the same route catalog for initial setup and `File -> Install Extensions / Packages`

### DEC-044: Put future UI package-install flows behind backend package-management services
Status: Accepted

Reasoning:
- The future UI should not need to understand planner internals, preset expansion rules, or persisted selection storage details.
- Setup scripts and UI flows should share one backend service boundary for route listing, install preview, and compatibility validation.
- Separating the service layer now keeps future UI package-management work thin and reduces the risk of duplicating install logic across scripts and screens.

Consequences:
- the route-based package layer now includes explicit service-facing request, preview, and compatibility models
- future setup and extension-install screens should call backend package-management services rather than planner helpers directly
- setup scripts remain an execution path, not the source of truth for package-management logic

### DEC-045: Keep package-install execution behind a backend service with explicit progress and failure contracts
Status: Accepted

Reasoning:
- Future setup and `File -> Install Extensions / Packages` screens need more than planning; they need a backend execution path that can surface progress, structured logs, and user-facing failures.
- UI code should not own subprocess command construction, logging context, or install-failure translation.
- A dedicated execution service keeps the install workflow testable and aligned with the repository's existing runtime-contract approach.

Consequences:
- package-install execution now has explicit progress-event, result, and runtime-error models
- future UI screens should call a backend install-execution service rather than invoking setup scripts directly
- structured logging and failure wrapping are now part of the package-install backend contract
