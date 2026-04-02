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
- surface no-match and ambiguous-match conditions as reviewable issues
- build a real `ConversionSession` once the draft is acceptable

This keeps direct-ingest session assembly in the application layer instead of scattering path grouping, source-role decisions, metadata-override handling, and adapter classification logic across widgets or desktop bootstrap helpers.

## Design constraints

- application services depend on domain contracts and adapter contracts only
- services remain small and deterministic
- services should fail clearly when selection or workflow state is invalid
- UI-adjacent package flows should depend on backend service contracts instead of reading setup-script conventions directly
- package-install execution should expose progress and user-facing failure contracts rather than leaking raw subprocess behavior into callers
- future UI setup and package-management screens should use thin controller bindings over backend services instead of embedding planning or runtime wiring in widgets
- direct file/folder ingestion should go through `SessionAssemblyService` instead of pushing adapter-discovery logic into the Qt layer

## Immediate follow-on work

1. Expand session assembly from current path selection, source-role assignment, and session-wide metadata overrides into richer grouping and source-specific disagreement workflows.
2. Keep broadening the desktop UI while preserving small controller/service boundaries.
3. Continue operational hardening for internal testing and saved-state recovery.
