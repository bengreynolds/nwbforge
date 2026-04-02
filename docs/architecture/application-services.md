# Application Service Baseline

Last updated: 2026-04-01

## Purpose

This note captures the first concrete application-layer services added on top of the domain and adapter contracts.

## Implemented services

### `RegistrySourceInspectionService`

Location: `src/nwbforge/app/services/inspection.py`

Responsibilities:
- locate a source within a `ConversionSession`
- resolve an adapter from `AdapterRegistry`
- honor `adapter_hint` when present, while still verifying compatibility
- reject missing, ambiguous, or incompatible adapter selection

This gives the orchestration layer a concrete inspection path without embedding source-format logic outside adapters.

### `SessionProvenanceService`

Location: `src/nwbforge/app/services/provenance.py`

Responsibilities:
- build a `ProvenanceRecord` from session state and artifact lists
- surface lab profile and session notes
- derive adapter ids from the sources attached to the session

This keeps provenance assembly as an explicit service instead of implicit glue code.

### `PackageManagementService`

Location: `src/nwbforge/app/packages/services.py`

Responsibilities:
- expose curated route-name package options to setup flows and future UI screens
- resolve install previews from `minimal`, `selected`, and `full` modes
- load and persist the last selected package set
- surface compatibility warnings and blocking issues for install requests

This keeps route-based package-management logic behind a backend service boundary instead of scattering it across setup scripts and future UI components.

### `PackageInstallationService`

Location: `src/nwbforge/app/packages/execution.py`

Responsibilities:
- execute route-based package installs in the dedicated development environment
- emit explicit install progress events
- log structured install context and failures
- wrap subprocess failures in a user-facing runtime error

This keeps install execution separate from both setup-script glue and future UI components.

### `PackageManagementController`

Location: `src/nwbforge/app/services/package_management.py`

Responsibilities:
- expose a thin UI-facing boundary over package preview and install execution
- list available route packages and preset groupings for setup and extension-install screens
- load the persisted package selection for setup defaults
- delegate install preview to `PackageManagementService`
- delegate background install execution to the threaded package-install executor

This keeps the future UI shell dependent on small controller-level operations instead of reaching directly into planner helpers, setup scripts, or subprocess orchestration.

### `SessionAssemblyService`

Location: `src/nwbforge/app/services/session_assembly.py`

Responsibilities:
- accept real selected files and folders instead of requiring a hand-authored app session descriptor
- ask the adapter registry which sources can be handled directly
- suggest a session pathway (`supported`, `custom`, or `hybrid`) from the selected inputs
- apply first-pass automatic grouping heuristics to related selected inputs before session creation
- promote detected groups into first-class draft state with pathway and composition summaries
- support explicit per-source grouping correction on top of those heuristics
- support lightweight dataset-level grouping actions over selected sources on top of those heuristics
- persist explicit group-confirmation state for draft groups and project files
- detect simple same-stem metadata sidecars before session creation
- carry both session-wide and source-specific metadata overrides into the assembled session model
- surface no-match and ambiguous-match conditions as reviewable issues
- surface mixed supported/custom-looking groups as explicit reviewable issues
- build a real `ConversionSession` once the draft is acceptable

This keeps direct-ingest session assembly in the application layer instead of scattering path grouping heuristics, source-role decisions, metadata-override handling, and adapter classification logic across widgets or desktop bootstrap helpers.

### `JsonSessionAssemblyProjectStore`

Location: `src/nwbforge/app/services/projects.py`

Responsibilities:
- persist explicit direct-ingest project files as app-owned workspace documents
- load saved direct-ingest project files back into `SessionAssemblyWorkspace`
- keep saved project state distinct from hand-authored scientific source inputs

This gives the desktop app a truthful `Save Project` / `Open Project` path without treating JSON bootstrap fixtures as the long-term primary ingest model.

### `NwbFileController`

Location: `src/nwbforge/app/services/nwb_viewer.py`

Responsibilities:
- open `.nwb` files through `PyNWB` in read-only mode
- hold the active file handle for a standalone viewer session
- expose lazy top-level and child tree nodes over the loaded `NWBFile`
- return structured node-detail payloads for tree selections
- keep generic file inspection separate from validation and conversion logic

This keeps standalone NWB viewing backend-first and widget-thin instead of embedding PyNWB traversal rules directly inside the Qt layer.

### `NwbWidgetsPanelRenderer`

Location: `src/nwbforge/app/services/nwb_viewer_rich.py`

Responsibilities:
- detect whether optional `nwbwidgets` and `panel` dependencies are available
- expose a small availability/support contract for selected viewer nodes
- launch a richer browser-backed preview session for the selected node when available
- keep richer rendering optional and separate from the base `NwbFileController` path

## Design constraints

- application services depend on domain contracts and adapter contracts only
- services remain small and deterministic
- services should fail clearly when selection or workflow state is invalid
- UI-adjacent package flows should depend on backend service contracts instead of reading setup-script conventions directly
- package-install execution should expose progress and user-facing failure contracts rather than leaking raw subprocess behavior into callers
- future UI setup and package-management screens should use thin controller bindings over backend services instead of embedding planning or runtime wiring in widgets
- direct file/folder ingestion should go through `SessionAssemblyService` instead of pushing adapter-discovery logic into the Qt layer
- standalone NWB viewing should go through `NwbFileController` instead of embedding PyNWB file traversal directly in the Qt widgets
- optional rich NWB rendering should stay behind a distinct renderer service so the base viewer remains usable without web/notebook tooling

## Immediate follow-on work

1. Expand session assembly from current path selection, heuristic grouping, first-class group summaries, group confirmation, current group actions, simple sidecar association, explicit project files, and current session/source override support into richer dataset/session modeling and post-preview conflict-resolution workflows.
2. Keep broadening the desktop UI while preserving small controller/service boundaries.
3. Continue operational hardening for internal testing and saved-state recovery.
4. Expand standalone NWB viewing beyond the current generic lazy tree/detail baseline only when a specific richer renderer is justified.
