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

### DEC-046: Use the same background-execution pattern for package installs as for conversions
Status: Accepted

Reasoning:
- Package installation is also long-running work that should not block the future desktop UI.
- The repository already has a threaded runtime-execution pattern for conversions, and package installs should follow the same model instead of inventing a second asynchronous strategy.
- Reusing the background-execution pattern keeps UI integration simpler and aligns progress/error handling across conversion and install flows.

Consequences:
- package installs now have a threaded runtime executor alongside the conversion executor
- future setup and `File -> Install Extensions / Packages` screens should run installs through the package runtime executor, not directly on the UI thread
- queued, progress, completion, and failure behaviors for installs now follow the same general runtime pattern as conversion work

### DEC-047: Put a thin controller layer in front of package-management services for future UI screens
Status: Accepted

Reasoning:
- The desktop UI should not own wiring between install planning, saved-selection loading, and background install execution.
- A thin controller boundary keeps UI code small while preserving the existing backend separation between planning, execution, and runtime threading.
- This provides a concrete first pattern for UI-facing screen logic without forcing widget code into the repository yet.

Consequences:
- package-management UI work should call `PackageManagementController` instead of directly composing package services and executors in screen code
- controller logic should stay thin and defer business rules to the existing package services
- future setup and `File -> Install Extensions / Packages` screens now have one small backend entry point for route listing, preview, selection loading, and install submission

### DEC-048: Apply category-first packaging to the supported tabular family
Status: Accepted

Reasoning:
- The category-first structure already established for supported behavior routes should also apply to the text/tabular family so the internal adapter layout stays semantically organized.
- Leaving tabular routes in a top-level software-oriented module would keep the repo in a half-migrated state and weaken the family-module direction.
- CSV and Excel interval routes share one semantic implementation path, so the family belongs under a category package rather than a standalone top-level module.

Consequences:
- the shared CSV/Excel interval family now lives under `src/nwbforge/adapters/supported/tabular/`
- future supported families should continue to migrate toward category-first packages before adding more top-level route files
- public exports stay stable while the internal supported-adapter layout becomes more consistent

### DEC-049: Start desktop UI development with toolkit-agnostic shell and screen models
Status: Accepted

Reasoning:
- The repository now has enough backend runtime and package-management contracts that UI development can begin without waiting for a final widget toolkit decision.
- Jumping straight into widget code would mix view concerns with still-settling shell and workflow behavior.
- A small UI-model layer lets the team validate menu, status, progress, and setup-flow behavior while keeping the backend/UI boundary explicit.

Consequences:
- `src/nwbforge/ui/` is now the home for toolkit-agnostic shell and screen models
- the first UI implementation slice focuses on `DesktopShellModel` and `PackageInstallerScreenModel` rather than concrete widgets
- future widget code should bind to these models instead of duplicating package planning, install execution, or runtime-state logic in views

### DEC-050: Put conversion-session UI behavior behind a screen model over runtime contracts
Status: Accepted

Reasoning:
- The conversion workflow already has explicit background-execution and progress/error contracts, so the UI should consume those directly rather than inventing a parallel session-state mechanism.
- A dedicated conversion-session screen model keeps preview/execution state transitions testable before any widget toolkit is chosen.
- This keeps the desktop shell thin and preserves the backend rule that conversion logic emits runtime events but does not manipulate UI components.

Consequences:
- `ConversionSessionScreenModel` is now the UI-facing boundary for one loaded conversion session
- future widgets should bind to screen state that already carries session, preview, execution, progress, and user-facing error state
- later UI work can focus on presentation, log sinks, and interaction design instead of reconstructing preview/execution lifecycle rules

### DEC-051: Centralize UI log capture and error translation behind shared observability helpers
Status: Accepted

Reasoning:
- The UI layer now has multiple screen models, and each one formatting exceptions or managing log-viewer state independently would drift quickly.
- Standard logging should remain the backend source of truth, but the UI still needs a shared bridge into viewer-friendly log entries.
- A single error presenter keeps user-facing messages consistent across conversion and package-install flows while preserving detailed context separately.

Consequences:
- `InMemoryUiLogSink` and `UiLogHandler` are now the first shared UI log-viewer bridge
- `DefaultUiErrorPresenter` is now the default translator for `PipelineRuntimeError`, `PackageInstallRuntimeError`, and common validation failures
- shell and screen models should consume shared observability helpers rather than formatting logs or exceptions ad hoc

### DEC-052: Use PySide6 for the first concrete desktop widget layer
Status: Accepted

Reasoning:
- The project needs a real cross-platform desktop widget layer now, and Qt for Python is a mature fit for the planned main-window, dock, dialog, and status-bar patterns.
- The repository already has toolkit-agnostic UI models, so the first widget slice should focus on binding those models into a real shell rather than reopening the toolkit decision.
- Keeping the first widget pass narrow reduces churn while still proving that the current UI-model contracts support real desktop components.

Consequences:
- `PySide6` becomes a core project dependency for the desktop application layer
- concrete widget code should live under `src/nwbforge/ui/qt/`
- the first widget slice should cover the main window, log dock, package-install dialog, and conversion-session panel before broader visual expansion

### DEC-053: Keep the first Qt widget slice thin and bind it directly to existing UI models
Status: Accepted

Reasoning:
- The repository already has stable shell, package, conversion-session, and observability models, so the first widget layer should prove those contracts rather than introduce a second UI-state system.
- A narrow `QMainWindow` plus dialog/dock/panel baseline is enough to validate menu wiring, background progress display, log-viewer integration, and package-install interactions.
- Headless widget tests are sufficient for this phase and avoid adding a heavier GUI-testing dependency before the basic desktop surface settles.

Consequences:
- widget code under `src/nwbforge/ui/qt/` should bind directly to `DesktopShellModel`, `PackageInstallerScreenModel`, `ConversionSessionScreenModel`, and shared UI observability helpers
- the first Qt surface remains intentionally narrow: main window, status bar, File menu, log dock, package-install dialog, and conversion-session widget
- widget tests should run with an offscreen Qt platform and exercise model binding instead of pixel-level UI behavior

### DEC-054: Mirror desktop logs through a composite sink and surface shell errors centrally
Status: Accepted

Reasoning:
- The in-app log viewer should not be the only durable record of desktop runtime activity; a file-backed sink is needed without duplicating logging logic in widgets.
- Package-install and conversion screens already translate backend failures into shared `UserFacingError` payloads, so the shell should own the actual dialog presentation rather than each widget inventing its own popup policy.
- Keeping both behaviors at the shell/observability boundary preserves the model-first UI design and avoids leaking file I/O or dialog policy into backend services.

Consequences:
- the desktop shell may use a `CompositeUiLogSink` to mirror entries to both the in-memory viewer sink and a file-backed JSON-lines sink
- widget code should rely on `DesktopShellState.last_user_error` for centralized user-error presentation rather than opening ad hoc dialogs from package or conversion widgets
- the first durable desktop log artifact format is JSON-lines and should remain easy to inspect during development and support workflows

### DEC-055: Put desktop settings behind a persisted service and a dedicated settings screen model
Status: Accepted

Reasoning:
- The `File -> Settings` menu item should no longer be a placeholder now that logging verbosity and file-log behavior are real user-facing runtime concerns.
- Settings persistence should not live in widget code; a small service boundary keeps file format and defaults stable while allowing future UI/toolkit changes.
- The settings dialog should follow the same model-first UI pattern as package-management and conversion-session work so runtime reconfiguration stays testable outside widgets.

Consequences:
- desktop settings now persist through `UiSettingsService`
- the first persisted settings surface is intentionally narrow: verbose logging, file logging enabled, and file log path
- Qt settings widgets should bind to `SettingsScreenModel`, and runtime shell updates should react to applied settings rather than reading dialog controls directly

### DEC-056: Keep conversion review controls inside the conversion-session screen and use a temporary launcher for manual UI testing
Status: Accepted

Reasoning:
- Validation outcome and review approval are part of the same user workflow as preview and execution, so splitting them into a separate top-level screen this early would add navigation complexity without improving architecture.
- The repository needs a practical manual-testing entry point now, but that should not force premature decisions about packaged app startup or installer behavior.
- A temporary Python launcher is sufficient for development validation as long as it is explicitly treated as a dev-only testing aid rather than a release mechanism.

Consequences:
- `ConversionSessionScreenModel` and the Qt conversion-session widget now own the first review/approval interaction surface
- `scripts/run_app.py` is a development/testing launcher only and does not alter the long-term release or packaging plan
- future packaged desktop startup can replace the temporary launcher without discarding the current screen-model and widget work

### DEC-057: Add a real desktop composition module for manual testing before packaged startup exists
Status: Accepted

Reasoning:
- The repository needed to move beyond a fake widget/demo shell so the current desktop UI could exercise the real manifest-backed pipeline, review flow, package-management services, and runtime executors together.
- Packaged desktop startup and installer behavior are still future release concerns, but manual testing is more useful when it runs through the same service composition the eventual app will use.
- A dedicated composition module keeps the temporary launcher thin and prevents `scripts/run_app.py` from becoming an ad hoc application-service layer.

Consequences:
- `src/nwbforge/app/desktop.py` is now the real desktop bootstrap/composition entry point for development-time manual testing
- `scripts/run_app.py` now loads a real manifest-backed conversion session and uses the actual desktop service stack instead of fake conversion behavior
- future packaged entry points should build on the same composition module rather than bypassing it

### DEC-058: Let the desktop shell load manifest-backed sessions and expose generated artifacts directly in the conversion screen
Status: Accepted

Reasoning:
- The desktop application needed one more step toward real usability: loading sessions from disk should not depend solely on launcher startup behavior.
- Generated NWB, validation-report, and review artifacts are already part of execution provenance, so hiding them from the desktop surface would weaken reviewability and make manual testing less realistic.
- This can be added without introducing a second controller layer by keeping shell-level file selection thin and leaving session/execution state projection in the existing screen model.

Consequences:
- the Qt shell now includes `File -> Open Session...` for manifest-backed desktop sessions
- `ConversionSessionScreenModel` now projects generated provenance artifacts into UI state
- the conversion-session widget now displays generated artifacts alongside validation and review state

### DEC-059: Reuse desktop settings persistence for recent-session history and startup session selection
Status: Accepted

Reasoning:
- Desktop session history is application state, but it is lightweight and user-specific enough to live with existing UI settings rather than requiring a separate persistence service at this stage.
- The shell needed both a recent-session menu and a stable way to reopen the last manifest-backed session when the temporary launcher starts without explicit input.
- Reusing `UiSettingsService` keeps the persistence path small and avoids introducing another JSON file or controller layer before broader shell navigation is designed.

Consequences:
- `UiSettings` now persists `last_open_session_path` and a bounded recent-session list
- the shell's `Open Recent` menu is rebuilt from settings-backed recent-session state
- the temporary desktop launcher now prefers an explicit manifest path first, then the last-opened session, then the generated demo manifest

### DEC-060: Make generated artifacts directly actionable from the conversion-session panel
Status: Accepted

Reasoning:
- The desktop surface already exposes generated artifacts, but manual review is still clumsy if users cannot open validation-report or review files from the UI.
- Adding direct artifact/file-folder actions is a small desktop affordance that materially improves testability without changing the underlying provenance model.
- This belongs in the conversion-session widget because it is a view concern over already-projected artifact state, not a new backend service.

Consequences:
- the Qt conversion-session widget now exposes actions to open the selected generated artifact or its containing folder
- validation reports and later review artifacts become immediately reachable from the desktop UI
- the artifact-open behavior stays generic and works across artifact types carried in execution provenance

### DEC-061: Add explicit desktop session lifecycle actions before broader multi-session navigation exists
Status: Accepted

Reasoning:
- The shell had reached the point where replacing the current session only through `Open Session...` was weaker than a standard desktop workflow.
- Users need an explicit way to clear the current screen state and an equally explicit way to reopen the last manifest-backed session without re-browsing for it.
- This can remain a thin shell concern while the app still operates on one loaded session at a time.

Consequences:
- the File menu now includes `New Session` and `Reopen Last Session`
- `ConversionSessionScreenModel` now supports explicit session clearing
- session lifecycle is now more app-like without introducing tabbed or multi-session navigation yet

### DEC-062: Persist the last-used NWB output directory in desktop settings
Status: Accepted

Reasoning:
- The desktop shell needed to move beyond a blank output-path field for every newly loaded session.
- Output-directory preference is user-specific shell state and fits naturally alongside the existing recent-session and logging settings.
- Persisting only the directory keeps the setting stable while allowing each new session to derive a sensible file name from its session id.

Consequences:
- `UiSettings` now persists `last_output_directory`
- newly loaded manifest-backed sessions receive a default output path based on the last used directory and current session id
- the shell records output-directory changes through the existing settings path instead of introducing another persistence channel

### DEC-063: Add dedicated desktop shortcuts for validation and review artifacts
Status: Accepted

Reasoning:
- Generic artifact browsing is useful, but the most important review-facing outputs are the validation report and the review decision record.
- Giving those two artifact types explicit affordances reduces friction during manual testing and makes the review workflow clearer.
- The shortcuts should remain view-level helpers over the same projected artifact state rather than becoming a special backend artifact API.

Consequences:
- the conversion-session widget now exposes dedicated actions for validation-report and review-decision artifacts
- the generic artifact list remains available for all artifact types
- artifact navigation stays provenance-driven and does not depend on bespoke report-location logic in services

### DEC-064: Let the Qt shell own NWB output-path selection dialogs
Status: Accepted

Reasoning:
- The desktop flow had reached the point where manual output-path typing was weaker than a standard save dialog.
- Choosing an output path is a widget concern, but the dialog still needs shell-level knowledge of the persisted last-used output directory.
- Keeping the dialog in the Qt shell avoids leaking `QFileDialog` concerns into toolkit-agnostic models while preserving the current model-first conversion workflow.

Consequences:
- `ConversionSessionWidget` now delegates output-path selection to a shell-provided callback
- `MainWindow` owns the `QFileDialog.getSaveFileName` path chooser and seeds it from the current output path or persisted last-used output directory
- the conversion-session panel now supports both direct path editing and dialog-based output-path selection

### DEC-065: Structure the conversion panel as explicit workflow sections instead of one stacked form
Status: Accepted

Reasoning:
- The conversion panel had accumulated enough controls that a single vertical stack was starting to read like an internal tool rather than a usable desktop workflow.
- Session summary, execution state, validation/review actions, and generated artifacts are distinct user tasks and should be visually separated accordingly.
- This improves the current desktop surface without changing the underlying screen-model or runtime contracts.

Consequences:
- `ConversionSessionWidget` now uses dedicated section containers for session summary, execution status, validation/review, and generated artifacts
- widget tests now treat those section boundaries as part of the expected desktop structure
- future desktop UI work should preserve or improve this sectioned workflow layout instead of collapsing it back into one stacked column

### DEC-066: Add explicit run-overview and review-guidance summaries to the conversion panel
Status: Accepted

Reasoning:
- Section boundaries alone were not enough; users still had to infer session readiness by reading raw labels, issue lists, and artifact tables.
- The desktop panel needs a small amount of intentional summary state so users can answer basic workflow questions quickly: what stage is the session in, what output is targeted, how many issues exist, how many artifacts were generated, and what review action is expected.
- This is still a view-level improvement and does not require new backend contracts.

Consequences:
- the execution section now includes explicit stage, output-target, validation-count, and artifact-count summaries
- the review section now includes review-guidance and acknowledgement-summary text above the detailed issue checklist
- future UI work should preserve this summary-first approach before adding richer desktop navigation or visual styling

### DEC-067: Define first-pass completion around desktop product coherence, custom/hybrid workflows, and operational readiness
Status: Accepted

Reasoning:
- The project had drifted toward measuring progress primarily through supported-route growth and long-term release planning.
- For the first serious internal testing round, the more important question is whether the application behaves like a coherent desktop product across supported, custom, and hybrid workflows.
- Broad NeuroConv route coverage and formal release engineering are still required later, but they are not the right gate for first-pass readiness.

Consequences:
- first-pass completion is now gated primarily by desktop UI coherence, representative custom/hybrid workflow coverage, and operational readiness for internal testing
- supported-format growth is now a first-pass enabler only when it unblocks representative testing coverage
- release engineering remains planned and mandatory later, but it no longer blocks the first-pass internal-testing milestone

### DEC-068: Use a tabbed workspace on the right side of the conversion panel
Status: Accepted

Reasoning:
- The right side of the conversion surface had become dense enough that static stacked sections were still doing too much at once.
- Run overview, review work, and generated artifacts are distinct tasks that benefit from desktop-style workspace navigation.
- Tabs improve focus without introducing a new controller or changing the underlying session/review contracts.

Consequences:
- `ConversionSessionWidget` now exposes explicit workspace tabs for run overview, review work, and artifacts
- the widget now selects the most relevant tab based on current execution state, validation issues, and generated artifacts
- future desktop UI work should continue using clearer workspace navigation patterns when they reduce visual overload

### DEC-069: Use a repo-owned `custom_session.json` source as the first real custom-path workflow
Status: Accepted

Reasoning:
- The first-pass milestone needed a real custom-path workflow before hybrid work begins.
- A repo-owned custom source is the fastest safe way to prove the custom-path architecture without pretending that all unsupported lab formats are solved.
- The adapter should map only the metadata that is genuinely understood and leave lab-specific concepts visible as reviewable metadata.

Consequences:
- the desktop app can now load `custom_session.json` sources through the real service stack
- custom-path sessions now run through normalization, mapping, repository-owned PyNWB assembly, validation, provenance, and review
- unresolved custom semantics remain visible as review issues and `DESCRIBE` mapping decisions instead of being silently coerced into standard NWB fields

### DEC-070: Show explicit source details in the left side of the conversion workspace
Status: Accepted

Reasoning:
- The session/source side of the conversion panel was still too thin for the desktop surface to feel product-like.
- Supported, custom, and later hybrid workflows need stronger source context than a label list alone.
- Pathway, source count, and selected-source details improve orientation without requiring a larger navigation refactor.

Consequences:
- the conversion workspace now shows pathway and source-count summaries in the session area
- the selected source now exposes location, role, adapter, and media context directly in the UI
- future hybrid work can build on the same source-detail area instead of inventing a second source-inspection surface

### DEC-071: Represent the first hybrid workflow with a desktop session descriptor instead of a special adapter
Status: Accepted

Reasoning:
- The first hybrid workflow needed to combine existing supported and custom sources without breaking the layered architecture.
- A hybrid descriptor is a workflow/bootstrap concern, not a scientific source format in its own right.
- Keeping hybrid composition in desktop/session loading allows the existing per-source adapters, normalization, mapping, provenance, and validation contracts to do the real work.

Consequences:
- the desktop app can now load `hybrid_session.json` sources that compose multiple real inputs into one `HYBRID` session
- hybrid workflow composition stays outside the adapter layer
- the first hybrid baseline combines supported and custom sources while preserving visible provenance and validation

### DEC-072: Declare the first-pass milestone complete once supported, custom, and hybrid desktop workflows are all testable
Status: Accepted

Reasoning:
- The first-pass gate was explicitly defined around a coherent desktop product plus representative supported/custom/hybrid workflows.
- After the hybrid workflow landed, the repository satisfied the documented completion gate more accurately than it fit the earlier “entering first-pass milestone” label.
- Marking the milestone complete creates a clean handoff into internal testing without pretending that release engineering or broad route expansion are finished.

Consequences:
- `planning.md` now reports the repository as `first pass complete / ready for internal testing`
- the next phase is structured internal testing and issue triage, not additional gate-defining feature work
- release engineering and broader supported-route growth remain post-first-pass priorities


### DEC-074: Auto-recover the latest saved session snapshot when reopening a desktop session
Status: Accepted

Reasoning:
- Automatic persistence is only partially useful for internal testing if reopening a session still drops the user back into a blank desktop state.
- The current latest-snapshot store already contains enough information to restore artifacts, validation issues, review status, and a best-effort output path without reconstructing a full execution object.
- This gives the desktop workflow a practical recovery baseline while keeping the implementation smaller than a full timeline or snapshot-browser feature.

Consequences:
- `ConversionSessionScreenModel.load_session(...)` now restores the latest saved snapshot when one exists
- reopened desktop sessions now surface recovered artifact, validation, review, and output-path state directly in the conversion workspace
- recovery remains latest-state only; richer history and multi-snapshot navigation are still follow-on work

### DEC-075: Use an app-owned default output directory instead of the repository root
Status: Accepted

Reasoning:
- Manual desktop testing showed that falling back to `Path.cwd()` for NWB output writes dirtied the repository root with generated `.nwb` and validation-report files.
- The app already has an app-state area under `.nwbforge/`, which is a more appropriate default location for generated outputs before a user chooses a custom export directory.
- This keeps internal testing cleaner without changing the persisted last-output-directory behavior once users intentionally choose an output location.

Consequences:
- the desktop shell now defaults new NWB outputs into `.nwbforge/outputs/` when no previous output directory has been recorded
- validation reports now follow those outputs into the app-owned directory instead of landing in the repository root by default
- checked-in example session metadata should prefer cleaner happy-path values where practical so first-run testing is less noisy

### DEC-076: Route artifact-open failures through shell-level user-facing errors
Status: Accepted

Reasoning:
- Manual testing showed that stale or unsupported artifact paths currently fall through to raw Qt shell errors, which is too low-level for desktop users.
- The shell already owns user-facing error dialogs and status-bar error state, so artifact-open failures should use the same path instead of being handled ad hoc in widgets.
- Existence checks are cheap and prevent noisy failed shell launches for deleted files or outdated recovered snapshots.

Consequences:
- artifact open and reveal actions now validate path existence before calling `QDesktopServices`
- failed artifact opens now surface shell-level user-facing errors instead of only console noise
- the conversion widget remains thin by delegating artifact-open behavior to shell callbacks

### DEC-077: Make real file and folder ingestion the primary desktop entry model, not hand-authored session JSON
Status: Accepted

Reasoning:
- The current `session_manifest.json`, `custom_session.json`, and `hybrid_session.json` loaders are useful for internal testing and bootstrapping, but they are not the right primary UX for a lab-facing desktop application.
- Requiring users to hand-author NWB Forge-specific JSON duplicates source truth, hides the real ingestion problem, and makes the app feel like a developer harness rather than a finished product.
- The product still needs some form of persisted internal state for reopen, recovery, and likely future `Save Project` behavior, so app-owned session/project files should be demoted rather than eliminated.

Consequences:
- the intended primary desktop entry flow is `New Conversion Session` followed by additive real file and folder ingestion
- the app should inspect inputs, suggest grouping, classify source contributions as supported/custom/hybrid, and surface metadata overrides before preview/build
- the current JSON-backed session loaders remain valid as testing fixtures, bootstrap helpers, and future saved-state compatibility paths, but not as the desired primary user-authored input format
- future UI and workflow planning should prefer direct input ingestion plus optional saved project state over expanding JSON-first entry behavior

### DEC-078: Start direct-ingest UX with a dedicated session-assembly service and `New Session` dialog
Status: Accepted

Reasoning:
- The product needed to stop treating `New Session` as a shell reset and start using it as the first real direct-ingest workflow entry point.
- Adapter matching, pathway suggestion, and draft session creation are application concerns and should not be embedded directly in the Qt layer.
- A narrow first slice that supports additive path selection, pathway suggestion, and draft session creation is enough to move the app off JSON-first startup without pretending that grouping and metadata override are already solved.

Consequences:
- direct-ingest workflow logic now lives in `SessionAssemblyService` and `SessionAssemblyScreenModel`
- the Qt shell now routes `New Session` into `SessionAssemblyDialog`
- `Open Session...` remains for testing fixtures and saved-state compatibility, but `New Session` is now the intended start of the primary workflow
- richer grouping, source-role editing, and metadata override remain explicit follow-on work rather than being implied by the first direct-ingest slice

### DEC-079: Keep first-pass direct-ingest overrides session-wide and persist in-progress drafts
Status: Accepted

Reasoning:
- The new desktop ingest path needed to move beyond path selection into real user-controlled behavior before preview/build, but a full source-specific metadata editing model would add more complexity than the current product milestone needs.
- Session-wide overrides for core canonical fields provide a simple first pass that works across supported, custom, and hybrid sessions without inventing source-specific conflict semantics too early.
- `New Session` should behave like a real workspace entry point, not a modal that discards in-progress work every time it is reopened.

Consequences:
- the direct-ingest workflow now supports source-role assignment for `primary`, `supplemental`, and `metadata` contributions
- assembled `ConversionSession` objects now carry session-wide metadata overrides into preview/build, where they are applied through a session-level normalization merge
- direct-ingest draft state now persists under app state and reopens when `New Session` is shown again
- source-specific metadata disagreement handling and explicit saved-project semantics remain follow-on work

### DEC-080: Maintain an explicit plan-code deviation audit during internal testing
Status: Accepted

Reasoning:
- The repository is now mature enough that product-shaping shortcuts can be mistaken for settled architecture if they are not called out directly.
- Internal testing should validate the real product direction, not only the current implementation artifacts.
- Startup flow, ingest grouping, metadata-override scope, source-role semantics, category-first package layout, and logging coverage are all areas where the current code still contains deliberate interim behavior.

Consequences:
- `planning.md` must keep an explicit critical-review section for current plan-code deviations during the internal-testing phase
- agent summaries should distinguish implemented behavior from target product behavior when they differ materially
- architectural shortcuts that affect user-facing workflow should trigger a decision checkpoint before more dependent features are built on top of them

### DEC-073: Persist latest preview, execution, and review state automatically in the real desktop workflow
Status: Accepted

Reasoning:
- The first-pass gate was complete, but the desktop path still treated preview persistence as a planned follow-on rather than real operational behavior.
- Internal testing will be more credible if the app preserves latest-state progress before execution, not only after execution or review.
- The current JSON latest-snapshot store is sufficient for this milestone without committing yet to a richer event log or database-backed history model.

Consequences:
- `SessionPersistenceService` now persists preview snapshots in addition to execution and review snapshots
- the real desktop composition now provisions a snapshot store under `.nwbforge/session-state/`
- `ConversionSessionScreenModel` now persists successful preview, execution, and review outcomes automatically and surfaces persistence failures as user-facing errors
- the next persistence milestone is richer history/recovery semantics, not basic preview-state coverage

### DEC-081: Start the manual desktop launcher in direct-ingest `New Session` mode by default
Status: Accepted

Reasoning:
- The intended product entry flow is direct file and folder ingestion, not automatic reopening of a JSON-backed bootstrap session.
- Continuing to auto-load a session in the default launcher path made the internal-testing application feel session-file-driven even after `New Session` became the preferred workflow.
- Explicit `--session` loading is still useful for fixtures, compatibility testing, and reopen behavior.

Consequences:
- `scripts/run_app.py` now opens the real desktop shell in `New Session` mode when no explicit session path is provided
- supported/custom/hybrid JSON sessions remain loadable through `--session` and `File -> Open Session...`
- startup behavior now better matches the direct-ingest-first product direction documented in `planning.md`

### DEC-082: Apply session-wide metadata overrides at a true session-level merge point
Status: Accepted

Reasoning:
- Injecting session-wide overrides through the first inspected source was an architectural shortcut that became misleading for hybrid sessions.
- Session-wide override semantics are still acceptable for the current product milestone, but they need a merge point that does not depend on source ordering.
- The normalization layer is the right boundary because it already owns canonical-field reconciliation across sources.

Consequences:
- `RegistrySourceInspectionService` no longer injects session-wide overrides into the first source extraction result
- `RuleBasedNormalizationService` now applies session-wide overrides after extracted metadata has been normalized into canonical models
- override values are recorded as `USER_SUPPLIED` canonical values rather than being disguised as source-extracted fields

### DEC-083: Use first-pass source-role precedence for canonical conflict handling
Status: Accepted

Reasoning:
- Source roles were visible in the UI but too close to decorative unless they affected at least one real downstream behavior.
- Full role-aware grouping, provenance weighting, and mapping policy remain larger follow-on work, but conflict resolution needed an honest first-pass rule now.
- A simple precedence rule gives mixed-source sessions deterministic behavior while still surfacing conflicts for review.

Consequences:
- normalization conflicts now retain `primary` values over `metadata`, and `metadata` over `supplemental`
- equal-rank conflicts remain deterministic by current merge order and are still marked `needs_review`
- the review workspace now describes that precedence explicitly so users can understand why a value was retained

### DEC-084: Complete category-first cleanup for the supported media family
Status: Accepted

Reasoning:
- Leaving image and audio adapters at the top level while behavior and tabular routes were already grouped by family was unnecessary drift.
- Image and audio are both media-oriented supported routes even though their optional dependencies differ.
- Category-first packaging is more important than minimizing file count when route dependencies and semantics differ materially.

Consequences:
- supported image and audio adapters now live under `src/nwbforge/adapters/supported/media/`
- public adapter exports remain stable through the existing package-level exports
- future media routes should extend the same family-first layout instead of adding more top-level supported modules

### DEC-085: Expand structured logging into direct-ingest and desktop state-management paths during internal testing
Status: Accepted

Reasoning:
- Internal testing needs actionable logs outside the core conversion runtime or triage becomes too dependent on UI state and manual reproduction.
- Session assembly, draft persistence, settings persistence, and desktop bootstrap are all user-facing behaviors that can fail before preview/build starts.
- A focused logging hardening pass is enough for this phase without pretending every UI interaction is fully instrumented.

Consequences:
- desktop bootstrap, session assembly, direct-ingest workspace persistence, and settings persistence now emit structured logs
- broader persistence, review, and UI-interaction logging remains follow-on hardening work
- `planning.md` should continue to treat logging coverage as improved but not complete until those remaining paths are addressed

### DEC-086: Prefer automatic grouping heuristics first in the direct-ingest workflow
Status: Accepted

Reasoning:
- The intended product should help users load heterogeneous inputs without forcing them to manually assemble every candidate grouping from scratch.
- Fully automatic grouping would overclaim scientific understanding too early, but fully manual grouping would be too slow and brittle for the current desktop direction.
- A heuristic-first approach keeps the app proactive while leaving room for richer confirmation and correction workflows later.

Consequences:
- direct-ingest planning should treat automatic grouping heuristics as the default first-pass grouping strategy
- current flat selected-path assembly remains only a narrow first implementation of that direction
- future grouping work should add confirmation and correction workflows on top of heuristic grouping rather than replacing heuristics with purely manual assembly

### DEC-087: Use parent-folder grouping as the first implemented direct-ingest heuristic
Status: Accepted

Reasoning:
- The repo needed a real grouping behavior for internal testing before a richer dataset model or correction workflow existed.
- Parent-folder and known-session-descriptor grouping is simple, explainable, and less risky than speculative scientific grouping logic.
- A shallow heuristic is preferable to a purely flat ingest model because it at least exposes likely related inputs early in the `New Session` workflow.

Consequences:
- `SessionAssemblyService` now assigns first-pass group keys and labels during draft assembly
- auto-grouping stays reviewable through explicit issues rather than being treated as fully trusted interpretation
- future grouping work should refine and correct this heuristic baseline rather than reintroducing flat path-to-source assembly as the default

### DEC-088: Reflect source roles in preview provenance before deeper mixed-source policy exists
Status: Accepted

Reasoning:
- Once roles influence normalization precedence, provenance should stop pretending that all sources are equivalent.
- Role-aware provenance ordering and labeling is a small change that improves reviewability without overcommitting to a full mixed-source policy engine.
- This keeps review and audit output aligned with the current direct-ingest role model.

Consequences:
- preview provenance now orders input artifacts by `primary > metadata > supplemental`
- input-artifact descriptions now include source-role context for reviewer clarity
- grouping behavior and deeper mapping policy remain follow-on work even though provenance is now role-aware

### DEC-089: Expand structured logging into review and persistence during internal testing
Status: Accepted

Reasoning:
- Internal testing needs more than runtime-core logs to make failures diagnosable.
- Review submission and session persistence are core user-visible workflows, so missing logs there would leave obvious triage gaps.
- A focused expansion into those services gives meaningful observability gains without blocking all forward feature work on complete UI-action instrumentation.

Consequences:
- review submission and snapshot persistence/loading now emit structured logs with session and decision context
- the repository should treat logging coverage as improved but still incomplete until broader desktop/UI interaction paths are instrumented
- future hardening should continue from this boundary instead of treating runtime-core logging as sufficient

### DEC-090: Allow per-source grouping correction on top of direct-ingest heuristics
Status: Accepted

Reasoning:
- Heuristic grouping is useful, but it is not honest enough on its own for mixed real-world inputs.
- The first correction layer should be small and understandable rather than a full dataset editor.
- Per-source group-label overrides let users fix obvious mistakes without introducing a second assembly model before the broader grouping design is ready.

Consequences:
- direct-ingest workspace state now persists manual group-label overrides
- the `New Session` dialog now lets users edit a selected source's group label directly
- future grouping work should treat these overrides as a bridge to richer dataset-level grouping, not the final grouping model

### DEC-091: Detect simple same-stem metadata sidecars during direct ingest
Status: Accepted

Reasoning:
- Some heterogeneous lab sessions already contain obvious metadata sidecars such as `recording.json` beside `recording.tif`.
- Treating those files as generic supplemental or primary sources is misleading during early review.
- A conservative same-stem heuristic is narrow enough to avoid pretending the app understands arbitrary sidecars.

Consequences:
- same-folder JSON, YAML, YML, and TXT files with the same stem as a non-sidecar file are now flagged as likely metadata sidecars
- those sources default to `metadata` role and surface a reviewable sidecar-association issue in the session-assembly workflow
- richer sidecar models and broader association heuristics remain follow-on work

### DEC-092: Expand structured logging into desktop shell file and artifact actions
Status: Accepted

Reasoning:
- Internal testing still depends heavily on shell-driven actions such as opening sessions, choosing outputs, and opening generated artifacts.
- Missing logs at that layer would hide failures that never reach the conversion runtime.
- This is a focused observability gain that improves triage without requiring full widget-level instrumentation.

Consequences:
- desktop session loading, reopen behavior, output selection, and artifact open/reveal actions now emit structured logs
- observability coverage is materially better for internal testing, but broader desktop/UI interaction logging is still follow-on work
- planning/docs should treat shell-action logging as implemented rather than still grouping it under the older review/persistence-only expansion

### DEC-093: Make explicit direct-ingest project files a first-class desktop workflow
Status: Accepted

Reasoning:
- Draft-only app-state persistence was enough for early `New Session` work, but it was too weak for a credible local desktop product.
- Users need a real saved-work state for reopen, handoff, and manual testing without falling back to hand-authored bootstrap JSON session files.
- A project document should persist assembled workspace state, not replace the real scientific source files as the authoritative data inputs.

Consequences:
- the desktop shell now exposes `Open Project...`, `Save Project`, `Save Project As...`, and `Open Recent Project`
- direct-ingest project files now persist selected paths, grouping, roles, and metadata override state as app-owned workspace documents
- JSON session fixtures remain compatibility/testing inputs, but explicit project files are now the preferred saved-state workflow

### DEC-094: Apply source-specific metadata overrides at the inspection boundary
Status: Accepted

Reasoning:
- Session-wide overrides are useful, but they are not enough once mixed-source sessions disagree on subject or session metadata.
- Source-specific overrides should behave like user edits to one source's extracted facts, not like hidden normalization shortcuts.
- Applying them at inspection keeps adapter parsing and normalization boundaries honest while preserving source provenance.

Consequences:
- `ConversionSession` now carries `source_metadata_overrides` in addition to session-wide overrides
- source-specific overrides are injected into `ExtractionResult` as user overrides before normalization
- normalization now converts those values into `USER_SUPPLIED` canonical values while still respecting the current source-role precedence model

### DEC-095: Preserve project identity through direct-ingest draft recovery
Status: Accepted

Reasoning:
- Once explicit project files exist, reopening a draft without its saved project path creates a confusing half-project state.
- Recovery should preserve whether the current workspace is anonymous draft state or a saved project with a clean/dirty lifecycle.
- This is necessary for credible local-app behavior even before deployment or richer project history exists.

Consequences:
- persisted direct-ingest workspace state now retains project-path identity and clean/dirty status
- reopened `New Session` drafts can retain their saved project context instead of reverting to anonymous draft state
- recovery remains latest-state only; richer project history is still follow-on work

### DEC-096: Add a repeatable internal smoke suite before deployment work
Status: Accepted

Reasoning:
- Full pytest coverage is necessary but not sufficient for a local desktop milestone that spans direct ingest, saved projects, and real supported/custom/hybrid execution paths.
- Internal testing needed one command that exercises the current product stack in a more integrated way than unit tests alone.
- This improves confidence and shortens future triage during the first manual testing round.

Consequences:
- `scripts/run_internal_smoke.py` now exercises supported, custom, hybrid, and direct-ingest project round trips
- internal local testing now has a documented checklist and smoke baseline in addition to the full automated suite
- deployment and release engineering remain deferred, but the local app now has a stronger repeatable test gate

### DEC-097: Promote direct-ingest groups into first-class session-assembly state
Status: Accepted

Reasoning:
- Per-source group labels were enough to prove regrouping, but they were not enough for a usable desktop ingest workflow.
- The `New Session` workspace needs to reason about dataset groups directly so it can show group-level pathway hints, counts, and review status.
- Grouping can remain heuristic-first while still exposing a clearer dataset-level model to users.

Consequences:
- `SessionAssemblyDraft` now includes explicit group summaries instead of leaving grouping implicit in source rows
- the `New Session` dialog now shows detected dataset groups with pathway and composition summaries
- grouping is still heuristic and reviewable; merge/split confirmation workflows remain follow-on work

### DEC-098: Surface mixed-source conflicts in a dedicated metadata-review workspace after preview
Status: Accepted

Reasoning:
- Source-specific overrides fixed the architecture boundary problem, but they still left conflict review too implicit for real internal testing.
- Mixed-source sessions need a post-preview workspace that shows the retained canonical value and the competing source values that produced it.
- This is enough to make disagreement handling visible now without prematurely designing a full conflict-resolution engine.

Consequences:
- the conversion workspace now projects pending normalized conflicts into a dedicated metadata-review tab
- the metadata-review tab shows canonical keys, retained values, contributing source values, and normalization notes
- direct field-by-field resolution actions remain follow-on work; users still resolve conflicts through the existing override/edit flows

### DEC-099: Add dataset-level grouping actions on top of heuristic direct-ingest grouping
Status: Accepted

Reasoning:
- First-class group summaries improved visibility, but the `New Session` workflow was still too dependent on per-source text edits.
- Users need small dataset-level actions now to make heuristic grouping honest enough for internal testing.
- A lightweight rename plus create/move model is enough to improve usability without inventing a full dataset editor yet.

Consequences:
- the `SessionAssemblyDialog` now supports selected-group rename and selected-source create/move actions
- `SessionAssemblyScreenModel` now exposes bulk grouping operations instead of only per-source group-label edits
- richer dataset confirmation, merge/split history, and a stronger dataset model remain follow-on work

### DEC-100: Start actionable metadata resolution with session-wide overrides from the metadata-review workspace
Status: Accepted

Reasoning:
- The dedicated metadata-review tab made mixed-source conflicts visible, but it was still read-only.
- The current product direction still prefers session-wide overrides as the first simple user-facing resolution path.
- Letting users promote a selected source value into a session-wide override directly from the review workspace is the narrowest truthful next step.

Consequences:
- `ConversionSessionScreenModel` now supports applying and clearing session-wide overrides from the conversion workspace
- using a metadata-review resolution action clears stale preview/execution state and prompts the user to rebuild
- fuller field-by-field conflict policy, source-specific post-preview resolution, and richer resolution history remain follow-on work

### DEC-101: Add a standalone read-only NWB viewer instead of embedding file inspection into the conversion panel
Status: Accepted

Reasoning:
- NWB inspection is a legitimate user workflow, but it is distinct from conversion-session authoring and review.
- Generated outputs and arbitrary external `.nwb` files should use the same viewer path.
- Keeping the viewer as a separate top-level window preserves a cleaner desktop workflow and avoids bloating the conversion surface.

Consequences:
- the desktop shell now has `File -> Open NWB Viewer...`
- generated `.nwb` artifacts now launch an app-owned viewer window instead of delegating immediately to the operating system
- the main conversion UI stays focused on conversion, review, and artifacts rather than becoming a generic NWB browser

### DEC-102: Use PyNWB-first lazy tree/detail viewing as the baseline NWB inspection architecture
Status: Accepted

Reasoning:
- PyNWB is the correct semantic-first access layer for `.nwb` files and should remain the source of truth for generic viewing.
- A lightweight tree/detail model is enough for the first local-app viewer and avoids introducing notebook-oriented tooling as a hard dependency.
- Lazy child loading and bounded previews keep the first viewer usable without committing immediately to a heavier rendering stack.

Consequences:
- `NwbFileController` now opens `.nwb` files in read-only mode through `NWBHDF5IO(..., mode="r", load_namespaces=True)`
- viewer tree nodes are generated lazily over major NWB sections and immediate child branches
- richer renderers such as `nwbwidgets` remain optional follow-on work rather than a base viewer dependency

### DEC-103: Add `nwbwidgets + Panel` only as an optional rich-preview layer for the standalone viewer
Status: Accepted

Reasoning:
- `nwbwidgets` can provide richer object-specific NWB rendering, but it is primarily notebook-oriented and should not redefine the base desktop viewer architecture.
- The local app still needs a robust generic viewer even when richer web/notebook tooling is unavailable.
- A browser-backed optional preview is enough to prove richer rendering without turning the Qt viewer into a web shell.

Consequences:
- the base standalone viewer remains `PyNWB` + custom Qt tree/detail UI
- the viewer now has an optional `Open Rich Preview` action powered by `nwbwidgets + Panel` when those packages are installed
- `nwbwidgets` and `panel` are now exposed through an optional dependency group rather than the core app dependency set

### DEC-104: Treat direct-ingest group confirmation and source-specific metadata resolution as first-class local-app state
Status: Accepted

Reasoning:
- Heuristic grouping and read-only disagreement review were enough for first-pass testing, but not enough for a stronger local-app workflow.
- Users need to explicitly acknowledge dataset bundles and preserve that acknowledgement through project save/reopen flows.
- Mixed-source conflict review also needs a narrower source-specific path before a fuller field-by-field conflict engine exists.

Consequences:
- direct-ingest groups now carry explicit confirmation state, and that state persists through workspace recovery and saved project files
- the `New Session` dialog now supports confirming groups and splitting selected sources back into individual groups
- the post-preview metadata-review workspace now supports source-specific override actions in addition to the existing session-wide override path
- fuller dataset modeling and richer conflict-resolution history remain follow-on work

### DEC-105: Require confirmation for reviewable multi-source bundles and broaden metadata-review actions before local-app signoff
Status: Accepted

Reasoning:
- Direct-ingest grouping was still too easy to ignore; users could create sessions from heuristic multi-source bundles without explicitly acknowledging them.
- The metadata-review workspace had become useful, but it still favored one narrow override path instead of deliberate per-field decisions.
- A stronger local-only app needs clearer bundle semantics and a more truthful per-field resolution surface before broader internal testing.

Consequences:
- direct-ingest groups now expose dataset kind and anchor-path context in addition to label/pathway summaries
- reviewable auto-grouped or mixed-pathway bundles now block session creation until they are explicitly confirmed
- the metadata-review workspace now supports manual session overrides, one-click source-to-source override actions, and clearer override-count summaries
- fuller dataset/session modeling and true conflict-resolution history remain follow-on work

### DEC-106: Explain heuristic dataset bundles explicitly and add per-field metadata review controls before deeper dataset modeling
Status: Accepted

Reasoning:
- Heuristic grouping had become actionable, but users still lacked enough context to understand why a bundle existed or what was inside it.
- The metadata-review workspace surfaced conflicts, but it still needed stronger review ergonomics before a fuller conflict engine existed.
- The next local-app step should improve explanation and control, not jump prematurely into a larger rewrite of dataset/session modeling.

Consequences:
- direct-ingest groups now surface grouping reason text, member labels, and whole-group split actions in the `New Session` workflow
- the metadata-review workspace now supports pending/resolved filtering, explicit resolution-status/history display, and clearing all overrides for one canonical field
- richer dataset/session modeling and durable field-resolution history remain follow-on work rather than being hidden behind current UI state

### DEC-107: Apply one shared desktop visual system before broader local-app polish
Status: Accepted

Reasoning:
- The desktop app had enough behavior to be useful, but it still looked like separate engineering panels rather than one product.
- A shared visual system is cheaper and more durable than continuing to hand-tune each dialog independently.
- Local-app polish should improve hierarchy and scanability without introducing a heavy custom widget framework.

Consequences:
- the Qt layer now uses one shared application stylesheet plus reusable header-card and metric-card helpers
- the main shell, direct-ingest dialog, package installer, settings dialog, and NWB viewer now share cleaner spacing, restrained color treatment, and stronger section hierarchy
- future UI polish should extend the shared design system rather than adding one-off widget styling

### DEC-108: Consolidate routine desktop workflows into one integrated main-window workspace
Status: Accepted

Reasoning:
- Internal testing showed that separate top-level dialogs and windows were adding lifecycle complexity, slowing down routine task switching, and making the app feel less like one product.
- The local desktop app has now grown past the stage where `New Session`, settings, package management, NWB viewing, and conversion review should behave like loosely related utilities.
- The shell already had a stable central workspace and tab pattern, so consolidating routine surfaces into one main window was lower risk than continuing to tune separate windows.

Consequences:
- the main window now hosts conversion review, direct-ingest session assembly, package management, settings, and NWB viewing inside one integrated tabbed workspace
- routine flows no longer depend on separate top-level dialogs or a separate NWB viewer window during normal shell use
- the standalone `NwbViewerWindow` remains only as a compatibility wrapper around the embedded viewer widget, not the primary user-facing path
- future desktop UI work should default to integrated workspace tabs or panes unless a separate top-level window is clearly justified

### DEC-109: Favor incremental UI log rendering and true record timestamps during internal testing
Status: Accepted

Reasoning:
- UI responsiveness had started to degrade as more runtime and desktop actions emitted structured logs into the in-app viewer.
- Internal testing also needed log timestamps that match the original logging event, not the later UI append time.
- The cheapest durable improvement was to preserve `logging` record timestamps and avoid resetting the entire log widget on every new entry.

Consequences:
- UI log entries now use the originating `logging` record timestamp when rendered or mirrored to file
- the docked log viewer now appends incrementally when possible instead of redrawing the entire visible log buffer for every update
- future high-volume UI observability work should prefer incremental rendering and stable event timestamps over convenience rebuilds

### DEC-110: Gate optional supported-route availability on installed route dependencies
Status: Accepted

Reasoning:
- Supported-route growth now needs to scale, but the local app should not expose every route unconditionally just because code exists in the repository.
- Route-based package installation already exists for setup and later UI installs, so adapter registration should respect those same route boundaries.
- The desktop registry is the cleanest first enforcement point because it controls what direct ingest can detect and what supported execution can select.

Consequences:
- optional supported routes now carry curated dependency gates through the route package catalog
- the desktop adapter registry now skips optional adapters whose required route dependencies are not installed in the current environment
- newly implemented optional routes should be wired through both the package catalog and the registry gate, not added as unconditional app surface area
- the first routes added under this rule are `ScanImage` and `SLEAP`

### DEC-111: Scale optional route growth by extending category-first family backbones instead of adding isolated wrappers
Status: Accepted

Reasoning:
- Supported-route growth is now a scaling problem, so new routes should reinforce the family-module pattern rather than drifting back toward one-off top-level adapter files.
- The package-gated registry model makes it safe to add more implemented routes, but only if those routes stay organized around shared semantics and dependency gates.
- Behavior pose, media, and imaging each need at least one more proof case to validate that the optional-route model works across different route shapes.

Consequences:
- the `behavior` family now includes `LightningPose` alongside `FicTrac`, `DeepLabCut`, and `SLEAP`
- the `media` family now includes `Videos` alongside still-image and audio support
- the `imaging` family now includes `HDF5 Imaging` alongside `ScanImage`
- new optional routes should continue to land through category-first family modules plus package-catalog gates rather than unconditional registry growth

### DEC-112: Prefer distinctive source-pattern routes before adding generic overlapping TIFF backbones
Status: Accepted

Reasoning:
- Optional route growth now needs to improve practical ingest coverage without flooding direct ingest with ambiguous adapter matches.
- Several imaging routes in NeuroConv share `.tif` or `.tiff` suffixes, but some have stronger directory or sidecar signatures that are safer to expose first.
- A generic TIFF route is still valuable later, but it should not arrive before more distinctive imaging routes such as Micro-Manager, Miniscope, or Thor are in place.

Consequences:
- the next imaging-family scaling slice prioritizes `Micro-Manager TIFF`, `Miniscope`, and `Thor`
- route matching should use the strongest available path/layout hints rather than only suffix matching when overlapping formats exist
- future generic TIFF-family routes should be evaluated against direct-ingest ambiguity and may need stronger user-review affordances before being exposed

### DEC-113: Add configuration-gated task routes and distinctive acquisition-file routes before broader ambiguous behavior/ecephys backbones
Status: Accepted

Reasoning:
- The optional route catalog now needs to grow beyond imaging, but behavior/task and ecephys routes should still be chosen to minimize direct-ingest ambiguity.
- MedPC is a good task-route proof case because it should not match arbitrary text files; it can be exposed honestly only when explicit NeuroConv interface configuration is provided.
- Intan is a good acquisition-route proof case because `.rhd` and `.rhs` files are distinctive enough to gate cleanly without inventing a broader ecephys catch-all.

Consequences:
- the `behavior` family now includes `MedPC` as a configuration-gated task/events route
- the new `ecephys` family now starts with `Intan` as a distinctive acquisition-file route
- optional route scaling should continue to prefer strong path/config signatures before exposing broader ambiguous behavior or ecephys backbones
