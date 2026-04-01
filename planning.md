# NWB Forge Planning

Last updated: 2026-04-01
Status: Late Phase 2 / entering Phase 3 supported-path MVP

## Current Execution Status

Completed:
- Phase 1 planning and repository scaffolding
- Initial Phase 2 domain contract baseline under `src/nwbforge/domain/`
- Initial extraction, adapter, registry, and service-interface contracts
- First concrete application services for source inspection and provenance
- First concrete normalization-layer implementation
- First concrete mapping-layer implementation
- First concrete validation-layer implementation
- First concrete supported-path pilot adapter and integration test flow
- First high-level orchestration service for preview and execution evaluation
- First concrete PyNWB-backed NWB assembly/writer service
- First PyNWB schema-validation integration layered onto output validation
- First NWB Inspector integration layered onto output validation
- Expanded subject and session metadata coverage for the initial writer pathway
- Added initial device support across the manifest-backed supported conversion path
- Added initial acquisition-stream support across the manifest-backed supported conversion path
- Added first modality-specific acquisition assembly for behavior streams
- Added behavior spatial-data assembly through `Position` and `SpatialSeries`
- Established NeuroConv-first supported-path planning as explicit repository policy
- Added an explicit approved NeuroConv-first route catalog for supported-path work
- Added `neuroconv` as a declared project dependency
- Implemented the first real NeuroConv-backed supported adapter via CSV time intervals
- Implemented a shared NeuroConv interface-adapter framework for supported routes
- Added a dedicated NeuroConv workflow-adapter base for future combined gallery routes
- Added a direct NeuroConv execution service for supported routes backed by base-`NWBFile` assembly plus NeuroConv append/conversion
- Added structured logging helpers plus runtime instrumentation across pipeline, supported execution, and executor paths
- Implemented concrete runtime contracts for stage/progress/error reporting plus a threaded conversion executor
- Clarified that bounded parallel Codex subagent execution is a development workflow rule rather than an application runtime feature
- Expanded the real supported text/tabular family to include Excel time intervals
- Added a NeuroConv-backed still-image route using `ImageInterface`
- Added a NeuroConv-backed audio route using `AudioInterface`
- Added a NeuroConv-backed FicTrac behavior route using `FicTracDataInterface`
- Added a NeuroConv-backed DeepLabCut pose-estimation route using `DeepLabCutInterface`
- Added first-class normalized interval-table and trial-row support
- Added trial-table mapping and PyNWB trial assembly support
- Added machine-readable validation report artifacts to the execution pipeline
- Added an explicit validation review-outcome policy for UI and workflow consumers
- Added persisted post-execution review decisions and override records as machine-readable artifacts
- Added resumable JSON session snapshots for execution and review state
- Dedicated isolated Conda workflow for current development and testing
- Added backend package-management service contracts for future setup and extension-install UI flows
- Added backend package-install execution service with progress, logging, and user-facing failure wrapping
- Added a threaded runtime executor for package-install execution
- Added a thin package-management controller as the first UI-facing consumer of the package-management backend
- Applied category-first packaging to the supported tabular family under `src/nwbforge/adapters/supported/tabular/`
- Added the first toolkit-agnostic desktop UI model layer with a shell model and package-installer screen model
- Added the first conversion-session screen model over `ConversionExecutor` and pipeline runtime events
- Added a shared UI observability layer with an in-memory log sink, logging handler bridge, and shared user-facing error presenter
- Added the first concrete PySide6 widget baseline over the existing shell, package-install, and conversion-session UI models
- Added shell-level widget error presentation and an opt-in file-backed/composite UI log-sink path for the PySide6 widget layer
- Added a persisted desktop settings service plus a model-backed PySide6 settings dialog for verbose logging and file-log configuration
- Added review/approval controls to the conversion-session UI plus a temporary `scripts/run_app.py` desktop launcher for manual testing
- Added a real desktop composition/bootstrap module that wires the current shell, settings, package-management, conversion, and review services together for manual testing
- Switched the temporary `scripts/run_app.py` launcher from demo-only conversion behavior to the real manifest-backed desktop pipeline and screen-model stack
- Added shell-level `File -> Open Session...` wiring for manifest-backed desktop sessions
- Added generated-artifact visibility to the conversion-session UI so review and report outputs are visible during desktop testing
- Added persisted last-opened-session and recent-session tracking through the desktop settings path
- Added a dynamic `Open Recent` desktop menu backed by persisted session history
- Added direct desktop actions for opening generated artifacts and their containing folders from the conversion panel
- Focused tests for session, normalization, mapping, provenance, and validation models

In progress:
- Supported-path MVP expansion beyond the initial text/tabular, image, audio, and first behavior routes
- Continued expansion of direct NeuroConv-backed supported routes beyond the initial text/tabular family
- Modality-aware assembly expansion beyond the current behavior trace/position baseline
- Preview-state persistence and snapshot-history design beyond the current latest-snapshot store
- UI runtime and observability expansion beyond the current logging/progress baseline
- Route-based dependency management and package-install workflow for setup and future UI package management
- First UI-facing screen/controller layer on top of the current package-management backend services
- File-backed/composite log sinks and widget-level presentation on top of the new UI model layer
- Broader PySide6 widget expansion beyond the first shell/dialog/panel baseline
- File-backed/composite desktop logging expansion beyond the current opt-in shell log-file path
- Broader desktop settings expansion beyond the initial logging-focused settings dialog
- Transition from the temporary manual-test launcher to a packaged desktop entry point later in the release pipeline

Next:
- Add another real NeuroConv-backed supported adapter from the approved route catalog
- Richer multimodal assembly beyond the current generic acquisition-stream baseline
- Additional modality-specific NWB containers beyond the new behavior baseline
- Additional behavior subtypes and non-behavior modality containers beyond the new trace/position baseline
- Expand structured logging from the current core runtime services into broader persistence, review, and plugin paths
- Preview-state persistence and review history beyond the current latest-snapshot baseline
- Longer-term persistence backend decision beyond the current JSON snapshot store

### Current application baseline
- The repository now includes a real desktop-shell baseline for development and manual testing, but it is not yet a packaged or production-ready application.
- Supported-path adapters in code now include the repo-native `session_manifest.json` pilot plus real NeuroConv-backed CSV, Excel, still-image, audio, FicTrac, and DeepLabCut adapters.
- NeuroConv-backed single-interface routes now share a common framework for source-config parsing, interface construction, and extracted-field helpers.
- Supported NeuroConv routes are moving toward a category-first package layout, with shared family modules under category packages rather than software-named top-level adapter files when semantics are shared.
- Combined NeuroConv workflows now have a dedicated adapter base with declarative multi-source matching requirements, though no real workflow route is implemented yet.
- The project can write real NWB files for the manifest-backed pilot path, for combined manifest-plus-CSV or manifest-plus-Excel trial sessions, and for combined manifest-plus-image, manifest-plus-audio, manifest-plus-FicTrac, and manifest-plus-DeepLabCut supported sessions, validate them, persist review/report artifacts, and persist latest-state session snapshots.
- Supported-path execution can now choose a direct NeuroConv write path for compatible routes while still using repository-owned PyNWB assembly as the base-file builder and as the fallback/custom/hybrid path.
- Structured logging is now implemented on actionable runtime paths in the conversion pipeline, supported execution service, and threaded executor.
- The project now includes runtime contracts for stage/progress/error reporting and a threaded executor abstraction for the future UI, but does not yet include a production UI shell, broader acquisition-format coverage beyond the current supported families, or full multimodal NWB coverage.
- Supported behavior-route execution now includes direct NeuroConv processing-module writes for FicTrac and DeepLabCut, which reinforces the planned product shape: the UI should gather route-specific configuration and metadata overrides, then pass them into NeuroConv rather than attempting to recreate those conversions in local PyNWB code.
- The first concrete category-first package refactors are now in place for supported behavior routes under `src/nwbforge/adapters/supported/behavior/` and the text/tabular family under `src/nwbforge/adapters/supported/tabular/`.
- Development workflow now also requires explicit Codex subagent orchestration guidance: use at most three concurrent subagents, keep state isolated, collate results deterministically, and fall back to sequential handling on failure.
- Package-management work is now split between developer bootstrap and future UI flows: setup remains tied to the dedicated Conda environment, while the future UI should expose route-name package selection and post-setup installs without forcing a full reinstall.
- The route-based package layer now includes a service boundary for future UI consumers: screens should call backend package-management services for route listing, install preview, persisted selection loading, and compatibility validation rather than reaching directly into setup scripts.
- The route-based package layer now also includes an install-execution service so future setup and extension-install screens can run installs, surface progress, log context, and present user-facing errors without owning subprocess logic.
- The route-based package layer now also has a threaded runtime executor, so future setup and extension-install screens can run installs off the UI thread while preserving queued, progress, completion, and failure events.
- The route-based package layer now also has a thin `PackageManagementController`, giving the future UI one small binding point for route listing, install preview, saved-selection loading, and background install execution.
- The repository now also includes a first toolkit-agnostic `ui/` layer: a `DesktopShellModel` for File-menu/status/log-viewer state and a `PackageInstallerScreenModel` for setup and extension-install flows over the package-management controller.
- The `ui/` layer now also includes a `ConversionSessionScreenModel`, which consumes `ConversionExecutor`, `PipelineProgressEvent`, and `PipelineRuntimeError` directly instead of duplicating preview/execution workflow logic in future widgets.
- The `ui/` layer now also includes a shared observability baseline: `InMemoryUiLogSink` and `UiLogHandler` for an in-app log viewer path, plus `DefaultUiErrorPresenter` for consistent user-facing errors across screens.
- The repository now also includes the first concrete `PySide6` widget layer under `src/nwbforge/ui/qt/`, with a `QMainWindow`, File menu, status bar, log dock, package-install dialog, and conversion-session widget bound to the existing UI models.
- The PySide6 shell can now optionally mirror UI-visible logs to a JSON-lines file while preserving the in-app log viewer, and shell-level user-facing errors are now surfaced through real modal warnings rather than status text alone.
- The `File -> Settings` entry point is now a real dialog backed by persisted desktop settings, with current coverage for verbose logging and file-log path/configuration.
- The conversion-session UI now exposes validation-summary, review-outcome, issue-acknowledgement, and approve/reject controls over the existing execution-review service.
- The repository now also includes a real desktop bootstrap/composition module under `src/nwbforge/app/desktop.py` that assembles the manifest-backed pipeline, package-management services, review service, threaded executors, and current UI models into one manual-testable application stack.
- A temporary Python launcher now exists at `scripts/run_app.py`, and it now boots the real desktop service composition plus a real manifest-backed conversion session rather than a fake conversion executor.
- The desktop shell can now load manifest-backed sessions from disk through `File -> Open Session...` rather than relying only on launcher-provided startup state.
- The conversion-session UI now also surfaces generated artifacts from execution and review provenance so users can see the NWB output, validation-report artifacts, and later review artifacts directly in the desktop panel.
- The desktop settings path now also persists `last_open_session_path` and a bounded recent-session list, and the shell uses that state to populate `Open Recent` and to prefer the last-opened manifest on startup when no explicit path is supplied.
- The conversion-session panel now also supports direct actions for opening a selected artifact or its containing folder, which gives immediate desktop access to validation reports and later review artifacts.

## Project Vision and Scope

Build a UI-driven conversion platform that helps labs transform heterogeneous acquisition outputs into understandable, validated NWB files. The system must scale from straightforward supported conversions to complex assisted conversions that combine proprietary and custom data streams while preserving provenance, interpretability, and maintainability.

In scope for the product:
- Guided conversion workflows for multiple lab archetypes
- Clear distinction between supported, custom, and hybrid conversion pathways
- Plugin-style source adapters for lab- or system-specific inputs
- Metadata normalization before NWB assembly
- NWB assembly using the appropriate level of abstraction
- Validation, provenance capture, and human-readable conversion summaries
- User review steps for ambiguous mappings
- Formal cross-platform packaging, installation, update, and distribution support

Out of scope for the first phases:
- Fully automated interpretation of arbitrary proprietary formats without adapter work
- A universal ontology that solves all departmental metadata inconsistencies at once
- Direct replacement of all existing lab-side preprocessing pipelines
- Enterprise-scale workflow orchestration before core conversion contracts stabilize

## Assumptions and Unknowns

### Assumptions
- The department has repeated conversion needs across roughly 20 labs with partial overlap in metadata and acquisition patterns.
- Some labs already fit existing NWB ecosystem tools with modest configuration.
- Other labs will require custom adapters, manual metadata review, and hybrid composition.
- Researchers need a UI because conversion cannot rely on Python literacy alone.
- NWB output quality matters as much as file creation success.
- Long-term maintainability is better served by explicit contracts and modular boundaries than by one-off scripts.

### Unknowns
- Which acquisition systems are most common across the department
- How much metadata currently lives in files versus notebooks, spreadsheets, or operator memory
- Whether labs need local desktop execution, shared server execution, or both
- What minimum review and approval workflow is required before writing final NWB files
- Which lab-specific concepts should remain descriptive metadata versus formal extensions
- How much dataset merging is needed across clocks, modalities, and file families

## NWB Ecosystem Research Summary

### What NWB is intended to standardize
NWB standardizes neurophysiology data together with the metadata needed to interpret it. The standard is designed so experimental data, subject/session metadata, device context, and modality-specific structures can live in one navigable file layout rather than scattered across ad hoc lab formats.

Academic adoption goals typically include:
- Improving data sharing and reuse across labs and repositories
- Making multimodal experiments easier to analyze together
- Preserving experimental context and provenance
- Reducing bespoke format handling in downstream analysis
- Supporting archive deposition workflows such as DANDI

### Where NWB GUIDE fits
NWB GUIDE is the strongest reference point for straightforward, user-facing conversions. It is a desktop application that walks researchers through common conversion requirements and DANDI-oriented workflows. In this repository, GUIDE should be treated as the benchmark for the supported pathway UX, not as the full solution for unsupported or hybrid cases.

### Where NeuroConv fits
NeuroConv is the primary supported-path backend for known acquisition formats. It provides data interfaces and automated conversion patterns for many source systems. In this project, NeuroConv should be the default engine behind supported adapters and the first thing evaluated before writing custom ingest logic.

### Where PyNWB fits
PyNWB is the lower-level construction layer for reading, writing, validating, and customizing NWB files. It is the escape hatch for unsupported formats, hybrid assembly, and advanced cases where the system must construct or augment NWB structures directly.

### How custom data and metadata are typically represented
The NWB stack supports several levels of customization:
- Descriptive metadata placed into existing NWB fields when semantics match
- Lab-specific metadata through `LabMetaData` patterns
- Additional tabular fields where schema supports custom columns
- Neurodata Extensions (NDX) when truly new data types or structured metadata are required

Planning implication: the product should not jump straight to extensions for every mismatch. It should guide users through a decision ladder:
1. Map to existing NWB fields when semantics are clear.
2. Use descriptive metadata or supported custom fields when the concept is local but not novel.
3. Use NDX only when the data model itself needs a durable extension.

### Validation and review
Validation in the NWB ecosystem is layered:
- PyNWB validation checks schema compliance
- NWB Inspector checks best-practice issues and likely conversion mistakes
- Manual inspection remains necessary for scientific correctness and usability

Planning implication: validation must be a dedicated layer with machine checks and human review artifacts.

### Implementation-source-of-truth policy
- Official PyNWB documentation is the source of truth for API usage, data modeling, container selection, and file-writing patterns.
- Supported-path implementation should begin by checking the NeuroConv Conversion Gallery for an existing interface or combined workflow.
- The approved repository route catalog lives in [docs/research/neuroconv-supported-routes.md](docs/research/neuroconv-supported-routes.md).
- For supported proprietary and acquisition-system routes, direct NeuroConv conversion APIs should be the primary execution path rather than custom low-level NWB writing.
- UI-collected metadata, timezone handling, channel/plane selections, and similar user inputs should parameterize documented NeuroConv interfaces and workflows rather than duplicating their conversion logic in custom code.
- Direct PyNWB construction is the fallback path when NeuroConv does not support the format, the dataset is unusually custom, or the direct PyNWB route is clearly simpler and more maintainable.
- When a supported session also contributes repo-owned normalized metadata, devices, or other assembled content, build the base `NWBFile` in PyNWB and let NeuroConv append its supported modality into that file when the documented API allows it.
- Custom HDF5-level writing should be avoided when documented PyNWB APIs provide a schema-compliant path.

## Department-Wide Requirements and Constraints

### Functional requirements
- Support repeated use across many labs without per-project rewrites
- Accommodate single-format and multi-input conversion sessions
- Support partial automation with explicit human review gates
- Produce NWB outputs that are understandable to downstream researchers
- Persist conversion configuration, decisions, assumptions, and provenance
- Allow users to resume recent execution and review state without reconstructing it from artifact files alone
- Evaluate NeuroConv support status as a first-class step in supported-path planning
- Expose actionable runtime status, progress, logs, and user-facing errors during conversion work
- Support a desktop-style File menu with settings entry points and modular hooks for future tools

### Non-functional requirements
- Modular codebase with stable internal contracts
- Strong traceability from input fields to output NWB structures
- Safe handling of unsupported or ambiguous mappings
- Extensible plugin model for new labs and formats
- Testable backend components independent of UI
- Production-grade packaging and update story for Windows, macOS, and Linux
- Isolated local development environment that does not interfere with unrelated Python installations
- Structured logging throughout actionable code paths with no reliance on print-based diagnostics
- Non-blocking conversion execution through background workers, threads, or async orchestration
- Real progress reporting tied to actual pipeline steps rather than artificial timers
- User-friendly error propagation from backend failures into the UI without silent failure modes

### Organizational constraints
- Lab conventions will differ in naming, metadata completeness, and file layout
- Some formats may be legally or practically opaque
- Adoption depends on low-friction workflows for non-programmer users
- Department-wide governance will likely lag behind implementation, so local assumptions must be documented explicitly

## User Personas and Lab Archetypes

### Persona 1: Supported-path lab
Uses a common acquisition system already handled well by NeuroConv or GUIDE. Needs a fast UI workflow, metadata entry help, validation, and export.

### Persona 2: Semi-structured custom lab
Uses a mix of common files plus spreadsheets, JSON sidecars, or naming conventions. Needs file inspection, mapping assistance, and repeatable lab templates.

### Persona 3: Hybrid multimodal lab
Needs to combine proprietary acquisition output, derived signals, annotations, and custom metadata into one coherent NWB file. Needs staged review, provenance visibility, and explicit merge semantics.

### Persona 4: Platform maintainer
Adds adapters, normalization rules, and lab profiles. Needs stable contracts, tests, traceability, and a clear place to encode assumptions.

## Data Source Taxonomy

### By format support status
- Known supported formats with mature ecosystem tooling
- Partially supported formats requiring additional metadata or restructuring
- Unsupported proprietary formats requiring custom parsers
- Unsupported custom lab formats requiring bespoke adapters

### By data organization style
- Single recording file plus sidecar metadata
- Session folder with multiple modality files
- Multi-run experiment with separate acquisitions and derived outputs
- Mixed raw data plus spreadsheets or notebooks for annotations

### By metadata quality
- Rich embedded metadata
- Sparse metadata with recoverable conventions
- Fragmented metadata across files and human-entered records
- Ambiguous metadata requiring explicit user interpretation

## Conversion Pathway Taxonomy

### Supported pathway
Use existing ecosystem support with minimal custom logic.

Characteristics:
- Recognized source format
- Metadata model maps cleanly to NWB
- Conversion can mostly be expressed through NeuroConv and standard metadata entry

Expected system behavior:
- Guided format detection
- Pre-filled metadata forms
- Standard validation and summary

### Custom mapping pathway
Use custom adapter and explicit mapping logic.

Characteristics:
- Unsupported format or schema
- Non-standard metadata organization
- Need for manual field interpretation or local heuristics

Expected system behavior:
- Source inspection workflow
- Field-level mapping UI
- Persistent mapping configuration and review notes

### Hybrid pathway
Combine supported and custom components into one NWB file.

Characteristics:
- Multiple inputs from different systems
- Some components handled by NeuroConv, others custom
- Need to merge timelines, metadata, provenance, and descriptions

Expected system behavior:
- Multi-input session model
- Merge plan preview
- Unified validation and provenance report

## Proposed System Architecture

The architecture should preserve explicit layers and avoid format-specific logic leaking into UI or NWB assembly code.

### Layer 1: UI frontend
Responsibilities:
- Session creation
- File selection and source inspection views
- Metadata entry and review
- Mapping preview
- Validation and conversion reporting
- Status bar reflecting current pipeline stage
- Progress bar bound to real pipeline progress
- Optional in-app log viewer
- File menu with settings entry point and hooks for future tools/extensions

Preferred design direction:
- Build a workflow-oriented UI, not a generic form dump
- Model conversion as stages with checkpoints
- Preserve transparency around automatic versus manual decisions
- Keep long-running work off the UI thread at all times
- Surface both concise user-facing status and expandable verbose diagnostics

### Layer 2: Orchestration and application services
Responsibilities:
- Manage conversion sessions
- Route sessions into supported, custom, or hybrid flows
- Coordinate adapters, normalization, assembly, validation, and reporting
- Persist intermediate state and decisions
- Expose resumable session state through explicit persistence services
- Emit structured stage, progress, and error events for UI consumers
- Support verbose logging mode and worker-safe progress callbacks
- Provide backend service contracts for package-management screens and setup flows

Key rule:
- Orchestration knows process state, but not format-specific parsing details
- For real supported acquisition-system routes, orchestration should prefer driving NeuroConv conversion interfaces/workflows directly and reserve custom NWB assembly for fallback, custom, and hybrid cases.

### Layer 3: Adapter and plugin layer
Responsibilities:
- Detect source systems
- Read raw files and sidecar metadata
- Expose canonical extracted records to the rest of the system
- Prefer NeuroConv interfaces when the source format is already supported

Key rule:
- Adapters translate source-specific structures into internal extraction models
- Supported proprietary and acquisition-system adapters may orchestrate documented NeuroConv conversion APIs directly as the primary write path
- Custom adapters and fallback pathways should continue to feed the repository's normalization and PyNWB assembly layers
- Before writing a custom supported-path adapter, check the NeuroConv gallery and documented interfaces for an existing route

### Layer 4: Metadata normalization layer
Responsibilities:
- Normalize field names, units, identifiers, subject/session concepts, and controlled vocabularies
- Merge metadata from files, profiles, and user edits
- Track confidence, source, and override history

Key rule:
- Normalization creates internal canonical models that are independent of both raw source naming and final NWB serialization

### Layer 5: NWB mapping and assembly layer
Responsibilities:
- Map normalized models into NWB structures
- Choose between standard mappings, descriptive metadata, and extension points
- Compose hybrid outputs from multiple extracted streams

Key rule:
- This is the only layer allowed to construct NWB containers
- Direct construction should follow documented PyNWB APIs, with preference for built-in container classes and `pynwb.file` metadata objects over custom wrappers
- This layer is the primary write path for custom and hybrid conversions, and the fallback path for supported routes that NeuroConv does not cover cleanly

### Layer 6: Validation, provenance, and reporting layer
Responsibilities:
- Run PyNWB validation
- Run NWB Inspector
- Build human-readable reports describing mappings, assumptions, warnings, and unresolved items
- Record structured logs and contextual failure data alongside review/report artifacts when appropriate

Key rule:
- Validation outcomes should inform UI review and export readiness, not just logs

### Cross-cutting observability and runtime architecture
Responsibilities:
- Instrument actionable code paths with structured logging
- Emit pipeline-stage and percentage progress updates from real processing steps
- Capture exceptions with contextual metadata suitable for both logs and user-facing errors
- Support optional in-app log viewing without coupling UI widgets to backend logger internals

Key rule:
- Logging, progress reporting, and user-facing status are part of the application contract, not optional diagnostics

### Cross-cutting release and update architecture
Responsibilities:
- Package the application into platform-native installers
- Provide in-app update checks and update-launch flows
- Preserve user settings and local state across upgrades
- Publish release artifacts and metadata consumable by the updater

Key rule:
- Release engineering is an architecture concern, not post hoc packaging glue

## Backend Module Layout

Recommended Python package layout for implementation:

```text
src/nwbforge/
  app/
    sessions/
    services/
    workflows/
    runtime/
    logging/
  domain/
    models/
    contracts/
    enums/
  adapters/
    base/
    registry/
    supported/
    custom/
  normalization/
    schemas/
    rules/
    resolvers/
  mapping/
    planners/
    transformers/
    assemblers/
  validation/
    schema/
    inspector/
    reports/
  updates/
  release/
  provenance/
    models/
    emitters/
  lab_profiles/
  persistence/
  cli/
  ui/
```

Rationale:
- `domain/` keeps canonical models and contracts stable
- `adapters/` isolates source-specific logic
- `normalization/` prevents direct source-to-NWB coupling
- `mapping/` handles assembly and merge planning
- `validation/` and `provenance/` remain explicit first-class concerns
- `persistence/` now provides a dedicated place for resumable session-state backends
- `updates/` and `release/` reserve explicit space for installer and updater logic when that work begins
- `app/runtime/` and `app/logging/` reserve explicit space for background execution, progress emission, and structured logging contracts
- `ui/` reserves space for the eventual desktop shell, including status, log-viewer, and menu integration

## UI and Workflow Design

Recommended first-pass workflow:
1. Create conversion session
2. Add one or more input sources
3. Detect likely format and pathway
4. Check NeuroConv support and recommended interface/gallery example for supported candidates
5. Inspect extracted structure and metadata coverage
6. Apply lab profile or mapping template if available
7. Review normalized metadata
8. Review planned NWB mapping and hybrid merge decisions
9. Run validation precheck
10. Write NWB
11. Review final report and export artifacts

Critical UX principles:
- Always show what was inferred versus explicitly supplied
- Surface missing required metadata early
- Let users preview NWB organization before final write
- Support draft sessions and re-runs
- Keep conversions responsive by running them off the main UI thread
- Show current high-level stage in a status bar, not only in deep logs
- Bind progress bars to actual backend progress events and percentages
- Offer a clean optional log panel or window for verbose diagnostics
- Present concise user-facing errors with access to deeper logged context
- Express package installation choices in route names such as `DeepLabCut` or `ScanImage`, not raw pip requirement strings

### Planned desktop shell behaviors
- File menu with:
  - settings/configuration entry point
  - reserved hooks/placeholders for future tools and extensions
  - `Install Extensions / Packages` entry point for adding route-specific support after setup
- Status bar states such as `loading`, `inspecting`, `normalizing`, `mapping`, `writing`, `validating`, `complete`, and `failed`
- Progress bar driven by backend-reported percentage updates
- Toggleable verbose log viewer for troubleshooting and review
- Clear separation between view state, background worker state, and conversion domain state

### Desktop toolkit baseline
- The first concrete widget layer should use `PySide6` as the desktop toolkit.
- Widget code should live under `src/nwbforge/ui/qt/` and bind to the existing toolkit-agnostic UI models rather than replacing them.
- The first widget slice should stay narrow:
  - `QMainWindow` shell
  - File menu actions wired to the shell model
  - status bar plus progress bar
  - docked log viewer fed by the shared UI log sink
  - package-install dialog over `PackageInstallerScreenModel`
  - conversion-session central widget over `ConversionSessionScreenModel`
- Widget tests should run headless in offscreen mode and avoid dependence on broader GUI test frameworks until the widget layer settles.

### Planned setup and package-install behaviors
- Initial setup should support install modes:
  - `minimal`
  - `selected`
  - `full`
- Initial setup should support route-name presets:
  - `minimal`
  - `common`
  - `full`
  - `custom`
- Package selection should be curated around route names rather than raw dependency names.
- Selected package sets should persist so repeated developer setup or future UI setup flows can reuse the last selection.
- Later package installation should reuse the same route catalog through `File -> Install Extensions / Packages`.
- Future UI screens should call a backend package-management service for:
  - available route listing
  - preset expansion
  - install preview
  - compatibility validation
  - persisted selection loading/saving

## Metadata Normalization Strategy

Normalization should be a dedicated internal contract, not an incidental helper.

Core ideas:
- Canonical internal models for subject, session, device, acquisition stream, timing, and annotations
- Field provenance on each normalized value
- Confidence and ambiguity markers for inferred mappings
- Rule-based normalization first, with room for future assisted suggestions
- Lab profiles that provide defaults, aliases, unit conventions, and required-field policies

Normalization outputs should answer:
- What concept does this source field represent?
- What source produced it?
- Was it inferred, defaulted, user-supplied, or adapter-extracted?
- Is it ready to map into NWB, or does it still require review?

## Provenance and Validation Strategy

Provenance requirements:
- Capture input file list, hashes if feasible, adapter versions, lab profile used, and user overrides
- Record pathway used: supported, custom, or hybrid
- Preserve mapping decisions and unresolved warnings
- Produce a human-readable conversion summary alongside machine-readable records

Validation requirements:
- Run schema validation with PyNWB before completion
- Run NWB Inspector for best-practice review
- Separate blocking errors from advisory warnings
- Derive an explicit workflow-facing review outcome from validation results
- Persist validation outputs in session artifacts
- Persist resumable execution/review state separately from generated report artifacts
- Log validation failures with enough context to diagnose source, stage, and affected artifact

### Logging, progress, and error-handling requirements

Structured logging:
- Instrument actionable code paths with a standard logger
- Avoid print statements in runtime paths
- Support normal and verbose conversion logging modes
- Preserve enough context to correlate logs with session id, source id, adapter id, and pipeline stage

Progress reporting:
- All conversion processes must be non-blocking
- Progress updates must come from real processing steps
- Emit both high-level stage transitions and percentage-based progress
- Progress reporting contracts should be UI-agnostic and safe for worker-thread or async execution

Error handling:
- Catch and log exceptions with contextual metadata
- Convert backend failures into concise, user-friendly UI-facing messages
- Preserve detailed logs for troubleshooting without exposing raw stack traces as the primary user message
- Avoid silent failure paths in adapters, orchestration, writing, validation, or persistence

### Development subagent orchestration requirements

- Codex subagent orchestration is a development workflow only and is not part of the shipped application.
- Maximum concurrent subagents: `3`
- Use parallel subagents only for independent tasks or code slices with isolated ownership.
- Collate subagent outputs deterministically before integration.
- When a subagent fails, conflicts, or returns ambiguous output, fall back to sequential local handling rather than adding more concurrent work.

Recommended report sections:
- Inputs
- Detected sources and adapters
- Metadata sources and overrides
- NWB mapping summary
- Validation results
- Manual review notes
- Known limitations and assumptions

## Cross-Platform Build, Packaging, and Distribution Strategy

The product must ship as a production-grade desktop application with formal releases on Windows, macOS, and Linux. This requirement does not change the current implementation sequence, but it does constrain architecture and tool choices now.

### Release requirements
- Single installer or installable package per platform release
- Bundled runtime and dependencies
- Support for fresh installation and updating an existing installation
- Built-in UI updater backed by GitHub releases
- Preservation of user settings and local configuration where feasible
- No end-user requirement for Conda or a virtual environment

### Current development environment policy
- During active development, installs and tests should run in the dedicated `nwbforge-dev` Conda environment
- The Conda environment is a developer convenience and isolation layer only
- Development environment setup must not interfere with existing project or user environments on the machine
- Current helper entry points are `scripts/setup-conda-dev.ps1` and `scripts/test-conda-dev.ps1`
- Development bootstrap should support:
  - `minimal` core install
  - `selected` route-name install using presets or explicit route names
  - `full` curated route install
- Route-name package selection should persist outside tracked source files so repeated setup runs can reuse the prior selection.
- Setup/install terminology must stay aligned with the future UI package-management flow.

### Required release packaging strategy

All final application releases must use this deployment model:
1. Build the application in Python
2. Package the application with PyInstaller
3. Wrap the PyInstaller build in a native installer or installable package for each supported platform
4. Provide an in-app updater that checks GitHub Releases and launches a user-friendly update flow

This is the required release baseline, not an open packaging evaluation.

### PyInstaller as the primary packaging layer

PyInstaller is the required first-stage packaging tool because it aligns with the intended product shape:
- Python-first application architecture
- desktop deployment across Windows, macOS, and Linux
- bundled scientific Python dependencies
- no end-user Python, Conda, or virtual environment requirement

Dependency bundling expectations:
- bundle the Python interpreter with the application
- bundle application code and required Python dependencies
- bundle scientific-stack dependencies needed for supported runtime behavior
- treat the PyInstaller output as the canonical application payload consumed by native installers

Scientific Python packaging tradeoffs and risks:
- larger application size due to bundled interpreter and binary dependencies
- platform-specific handling for compiled packages such as HDF5-backed libraries
- more complex signing, notarization, and codesigning behavior on macOS and Windows
- need for repeatable build inputs so PyInstaller output remains stable across release environments
- possible hidden-import, data-file, and plugin-discovery issues that require explicit PyInstaller configuration

Mitigation direction:
- keep the desktop stack Python-centric to avoid a sidecar runtime
- add dedicated PyInstaller specs and packaging tests before release implementation
- pin and validate release-build dependencies separately from day-to-day development tooling
- test packaged builds with representative scientific dependencies on every supported platform

### Native installer strategy

The installer layer must wrap the PyInstaller build rather than replace the Python-first architecture.

Windows:
- package the PyInstaller-built application with a native installer such as Inno Setup, NSIS, or WiX
- support install location selection, desktop shortcut creation, start menu entry creation, and standard uninstall/repair flows

macOS:
- package the PyInstaller-built application as a signed `.app` wrapped in a signed `.dmg` or `.pkg`
- support standard drag-install or guided install behavior, depending on the selected installer form

Linux:
- package the PyInstaller-built application as at least one broadly distributable format such as AppImage
- additionally evaluate one native package path such as `.deb` for managed lab environments if needed

### Packaging constraints and assumptions

- native installers should install the packaged app without asking the user to configure Python
- installers must preserve user data and settings outside the installed application directory where practical
- installers and updates must not interfere with existing Python or Conda installations on the user machine
- Conda remains a development-time isolation tool only

### Update mechanism design
- Built-in updater should query GitHub releases for the current platform
- Updater should present release notes and version availability in the UI
- Update flow should download the correct platform-native installer/package wrapping the PyInstaller payload and launch the update process
- User settings, lab profiles, templates, and local session state should live outside the installed app directory when possible

Updater architecture requirements:
- use GitHub Releases as the authoritative release feed
- resolve update assets by platform and application version
- support explicit user-driven update checks in the UI first
- preserve user settings and local state whenever the installer/update path allows it
- fail safely by leaving the current installation usable if update download or handoff fails

### Versioning strategy
- Use semantic versioning for public releases
- Use pre-releases for departmental pilots
- Track compatibility notes for config, plugin, and local-state changes

### Release pipeline
1. Build the Python desktop application for the target platform
2. Package the application with PyInstaller into a self-contained application payload
3. Validate bundled runtime and scientific dependencies in the packaged output
4. Wrap the PyInstaller payload in a platform-native installer or installable package
5. Publish GitHub release assets and notes
6. Application updater consumes published release metadata and launches the correct update artifact

### Rollback and failure considerations
- Failed updates must not corrupt user settings or session data
- Installers should support repair or reinstall paths
- Release metadata should support rollback to the last known-good version
- Config and state migrations must be versioned and reversible where feasible
- Packaged scientific dependencies must be validated on every supported platform before release promotion

## Plugin and Adapter Strategy for Lab-Specific Formats

Design goals:
- Add new source support without touching orchestration internals
- Distinguish core adapters from department-specific plugins
- Support lab profiles separately from source adapters

Recommended concepts:
- Adapter manifest with id, version, supported patterns, and capability flags
- Registry-based discovery for supported adapters
- NeuroConv-backed adapter implementations for officially supported source systems
- Family registries and route configuration declarations for supported routes that differ mostly by metadata, interface class, or light sniffing behavior
- Category-first family packages for supported route groups such as `behavior/` and `tabular/`
- Plugin package contract for lab-specific parsers and mapping presets
- Lab profile package for naming conventions, metadata aliases, defaults, and review policies
- Route-name package catalog that maps supported software/workflow names to optional dependency groups for developer setup and future UI package installation

Important separation:
- Source adapter: how to parse a format or folder structure
- Lab profile: how a specific lab uses or names concepts
- Mapping template: how normalized concepts should populate NWB for a repeated experiment style

### Supported-path implementation protocol
1. Determine whether the source format or pipeline is already supported by NeuroConv.
2. Check the approved route catalog and then the NeuroConv Conversion Gallery for the exact interface or combined workflow.
3. For supported proprietary and acquisition-system routes, use the documented NeuroConv conversion API as the primary execution path.
4. Let the UI and orchestration layers supply metadata overrides, timezone resolution, source-specific options, and user selections into NeuroConv rather than recreating its writer logic locally.
5. Fall back to direct PyNWB only when NeuroConv does not support the format, the dataset is unusually custom, or the direct PyNWB solution is clearly simpler and more maintainable.
6. When using direct PyNWB, use documented high-level APIs and standard NWB container placement, including `NWBFile`, `Subject`, `acquisition`, `processing`, `stimulus`, `intervals`, and `units` as appropriate.
7. If an NDX is required, stop and document that requirement before implementation.

### Preferred supported-adapter shape
- Use one shared NeuroConv core for common interface construction, source-config parsing, and extraction assembly.
- For real proprietary/acquisition formats with documented NeuroConv support, prefer a thin orchestration layer around NeuroConv `DataInterface` or workflow execution instead of reimplementing conversion in custom PyNWB code.
- Prefer family modules plus route configuration declarations when multiple supported entries target the same semantic NWB shape.
- Prefer category-first family packages before software-named top-level modules when those supported routes share the same semantic layer.
- Use smaller numbers of truly distinct route modules only when a route needs meaningfully different source sniffing, normalization bridging, mapping behavior, or NWB targets.
- Reserve dedicated workflow adapters for combined NeuroConv pipelines and multi-interface conversions rather than forcing them into single-source wrappers.

Criteria for when a supported route deserves its own module:
- it targets a different NWB container family or normalization contract
- it needs materially different extraction logic beyond declarative route config
- it requires non-trivial source sniffing or metadata bridging that would make a family module less clear
- it is a workflow composition rather than a single interface route

### Concrete NeuroConv rollout sequence
1. Build a shared NeuroConv adapter framework for single-interface routes:
   - common source-configuration parsing
   - common interface instantiation
   - common extraction-field and issue helpers
2. Refactor existing real NeuroConv-backed adapters toward family modules and route configuration declarations before adding more routes.
3. Establish a dedicated multi-source workflow-adapter base for combined NeuroConv gallery routes.
4. Add the behavior pose and trajectory family:
   - DeepLabCut
   - FicTrac
   - LightningPose
   - SLEAP
   - Neuralynx NVT
5. Add behavior task and media routes:
   - MedPC
   - Audio
   - Videos
   - Image
6. Add the first concrete combined-workflow NeuroConv routes such as `SpikeGLX & Phy`, `Tiff & Suite2p`, and electrophysiology-plus-behavior sessions.
7. Add ophys imaging and segmentation families.
8. Add intracellular and fiber photometry routes.
9. Add extracellular recording and sorting families.
10. Introduce the desktop runtime shell with:
   - background execution infrastructure
   - structured logging integration
   - real progress/status event handling
   - initial File menu, status bar, progress bar, and optional log viewer

Execution rule:
- single-interface routes should land on the shared interface-adapter framework
- routes that differ mostly by metadata or interface selection should share family modules and config declarations rather than one-file-per-route wrappers
- combined gallery workflows should land on a workflow adapter layer rather than being forced into single-source wrappers
- each implemented route must include adapter tests plus at least one orchestration-level or integration-level proof path
- UI implementation should consume runtime/logging/progress contracts rather than reaching directly into conversion internals
- Start the UI with toolkit-agnostic shell and screen models before committing to widget-specific code

## Risk Register

### High risks
- Underestimating metadata fragmentation across labs
- Treating unsupported formats as a parser problem when they are really a semantics problem
- Leaking source-specific assumptions into core NWB assembly code
- Writing opaque NWB outputs that validate but are difficult to interpret

### Medium risks
- UI becoming a thin wrapper around backend exceptions
- Early plugin API churn causing adapter rewrites
- Unclear ownership of department-wide vocabulary normalization
- Hybrid merge logic becoming tightly coupled to a few early labs

### Mitigations
- Keep canonical domain models separate from source and NWB models
- Make provenance and review visible from the start
- Pilot with multiple lab archetypes before freezing contracts
- Record assumptions and unresolved mappings in decision logs and reports

## Phased Implementation Roadmap

### Phase 1: Research and planning
- Document ecosystem, architecture, risks, and open questions
- Establish repo conventions and agent operating rules
- Define module boundaries and workflow concepts

### Phase 2: Core backend contracts
- Create canonical domain models
- Define adapter interfaces, registry contracts, and session models
- Define normalization and mapping contracts
- Add validation and provenance service interfaces

Current status:
- Canonical session, normalization, mapping, provenance, and validation models are in place
- Adapter registry and service protocols are in place
- Initial source-inspection and provenance services are in place
- Initial rule-based normalization is in place
- Initial rule-based mapping planner is in place
- Initial artifact validation is in place
- PyNWB schema validation is now integrated through the validation layer
- NWB Inspector validation is now integrated through the validation layer
- The current writer now carries richer subject/session metadata including experiment description, subject description, and subject date-of-birth support
- The manifest-backed supported path now carries normalized devices through mapping and into the PyNWB writer
- The manifest-backed supported path now carries inline acquisition streams through mapping, with behavior traces targeting `BehavioralTimeSeries`, behavior position streams targeting `Position`/`SpatialSeries`, and non-behavior streams retaining generic NWB `TimeSeries` fallback
- The pipeline now emits a machine-readable JSON validation report artifact alongside generated outputs
- The pipeline now derives an explicit validation review outcome so UI and workflow layers do not need to infer blocking versus advisory behavior from raw issue lists
- Post-execution review decisions can now be persisted as explicit approval/rejection artifacts with acknowledgement and blocked-override rules
- Execution and review state can now be resumed from JSON session snapshots through a dedicated persistence store and app service
- A repo-native supported-path pilot adapter is in place for architecture validation
- A high-level preview/execution orchestration service is in place
- A thin PyNWB-backed writer is in place for minimal NWB output generation
- The current manifest-backed supported path can now satisfy the active validation stack when required subject metadata is present and can emit NWB devices plus first-pass behavior trace and position pathways, but broader modality-specific and multimodal content remain out of scope
- Validation policy now distinguishes `pass`, `review`, and `blocked` outcomes explicitly, with persisted review-decision artifacts layered on top
- Session persistence is currently latest-snapshot JSON storage and does not yet provide full revision history, preview-state persistence, or concurrent review handling
- `neuroconv` is now a declared project dependency and the first real supported-path route is implemented through `CsvTimeIntervalsInterface`
- The current real supported text/tabular routes cover CSV and Excel interval/trial data and combine cleanly with the manifest-backed metadata pilot in multi-source supported sessions
- The current real supported text/tabular family now lives under `src/nwbforge/adapters/supported/tabular/`, aligning it with the category-first packaging direction already used for `supported/behavior/`
- Combined NeuroConv workflows now have a dedicated adapter base and matching contract, but no real workflow-backed route has been implemented yet
- Normalization, mapping, and assembly now include first-class interval-table support targeting NWB trials
- Runtime contracts now include stage/progress events, user-facing runtime error wrappers, and a threaded conversion executor abstraction on top of `ConversionPipelineService`
- Additional real supported adapters should continue to be chosen from the approved NeuroConv-first route catalog unless a documented reason is recorded otherwise
- Structured logging is now instrumented across the core runtime path, including `ConversionPipelineService`, `NeuroConvSupportedExecutionService`, and `ThreadedConversionExecutor`
- Supported CSV, Excel, image, and audio routes can now execute through direct NeuroConv conversion, with repository-owned PyNWB assembly providing the base `NWBFile` and remaining the fallback, custom, and hybrid path
- The package-management backend now also includes a thin controller layer, so the future desktop UI can consume one small binding surface instead of wiring directly to planner, service, and executor components
- The first toolkit-agnostic UI models now exist under `src/nwbforge/ui/`, which lets the repo start desktop-shell development before choosing a concrete widget toolkit
- The first conversion-session UI model is now in place, so the next UI work can focus on shared log/error presentation and then a concrete widget layer rather than inventing session workflow state from scratch
- Shared log/error presentation is now partially in place at the UI-model layer, so the next UI work can move toward file-backed/composite sinks and actual widget rendering rather than backend exception formatting

### Phase 3: Supported-path MVP
- Implement one end-to-end supported workflow using NeuroConv-backed adapters
- Provide minimal UI or CLI workflow to prove session orchestration
- Produce validation and summary artifacts

Current status:
- End-to-end NeuroConv-backed supported workflows now exist for CSV and Excel time intervals carried into NWB trials plus still-image and audio conversion through documented NeuroConv interfaces
- Additional supported routes and a minimal operator-facing shell remain outstanding
- UI/runtime contracts for background execution, progress, logging, and user-facing errors are now explicit, with logging implemented across the core runtime path

### Phase 4: Custom-path MVP
- Implement source inspection workflow
- Support manual metadata mapping and persistent templates
- Write custom-path NWB assembly with explicit review gates

### Phase 5: Hybrid-path MVP
- Support multi-input conversion sessions
- Implement merge planning and combined provenance reporting
- Validate merged outputs with representative datasets

### Phase 6: Department rollout
- Add lab profiles
- Harden plugin contracts
- Expand adapter coverage
- Add onboarding docs, sample datasets, and governance guidance

## Open Questions

- Which 3 to 5 lab pipelines should define the initial architecture tests?
- Do we need a desktop-first UI, browser-first UI, or both?
- Where should session state live for early deployments: local files, SQLite, or service-backed storage?
- What minimum provenance record is required for auditability?
- When should the system recommend descriptive metadata versus a formal NDX?
- How should lab vocabularies be versioned and reviewed?
- Which validation findings should block export by default for each lab profile or deployment mode?

## Decisions Log

This file is the high-level planning document. Decision details and reversals should be recorded in [decisions.md](decisions.md).

Initial decisions:
- Use a layered architecture with explicit normalization and provenance layers.
- Treat supported, custom, and hybrid conversions as first-class pathways.
- Prefer NeuroConv first for supported ingestion, PyNWB for custom assembly, and NWB GUIDE as a UX reference for straightforward conversions.
- Avoid promising universal automatic conversion intelligence in early phases.

Implementation references:
- Core contract note: [docs/architecture/core-contracts.md](docs/architecture/core-contracts.md)
- Adapter contract note: [docs/architecture/adapter-contracts.md](docs/architecture/adapter-contracts.md)
- Application-service note: [docs/architecture/application-services.md](docs/architecture/application-services.md)
- Orchestration note: [docs/architecture/orchestration-services.md](docs/architecture/orchestration-services.md)
- UI runtime note: [docs/architecture/ui-runtime-observability.md](docs/architecture/ui-runtime-observability.md)
- UI screen-model note: [docs/architecture/ui-screen-models.md](docs/architecture/ui-screen-models.md)
- Review workflow note: [docs/architecture/review-workflow.md](docs/architecture/review-workflow.md)
- Session persistence note: [docs/architecture/session-persistence.md](docs/architecture/session-persistence.md)
- Normalization note: [docs/architecture/normalization-services.md](docs/architecture/normalization-services.md)
- Mapping note: [docs/architecture/mapping-services.md](docs/architecture/mapping-services.md)
- Assembly note: [docs/architecture/assembly-services.md](docs/architecture/assembly-services.md)
- Validation note: [docs/architecture/validation-services.md](docs/architecture/validation-services.md)
- Pilot adapter note: [docs/architecture/pilot-supported-adapter.md](docs/architecture/pilot-supported-adapter.md)
- Development environment note: [docs/architecture/development-environment.md](docs/architecture/development-environment.md)
- Release note: [docs/architecture/release-strategy.md](docs/architecture/release-strategy.md)
- NeuroConv route catalog: [docs/research/neuroconv-supported-routes.md](docs/research/neuroconv-supported-routes.md)

## Research References

- NWB Overview: https://nwb-overview.readthedocs.io/en/latest/
- Converting neurophysiology data to NWB: https://nwb-overview.readthedocs.io/en/latest/conversion_tutorial/user_guide.html
- NWB GUIDE docs: https://nwb-guide.readthedocs.io/en/latest/
- NeuroConv docs: https://neuroconv.readthedocs.io/en/stable/
- NeuroConv Conversion Gallery: https://neuroconv.readthedocs.io/en/stable/conversion_examples_gallery/index.html
- PyNWB docs: https://pynwb.readthedocs.io/en/stable/
- PyNWB file module: https://pynwb.readthedocs.io/en/stable/pynwb.file.html
- PyNWB behavior module: https://pynwb.readthedocs.io/en/stable/pynwb.behavior.html
- NWB Inspector docs: https://nwbinspector.readthedocs.io/
- OpenAI Codex AGENTS.md guide: https://developers.openai.com/codex/guides/agents-md
