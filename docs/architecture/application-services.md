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

## Design constraints

- application services depend on domain contracts and adapter contracts only
- services remain small and deterministic
- services should fail clearly when selection or workflow state is invalid
- UI-adjacent package flows should depend on backend service contracts instead of reading setup-script conventions directly

## Immediate follow-on work

1. Add backend execution services for route-package installation progress and error reporting.
2. Add normalization and mapping-planner service implementations.
3. Add validation-service implementations that wrap PyNWB validation and NWB Inspector.
