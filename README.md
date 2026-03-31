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
- [docs/architecture/validation-services.md](docs/architecture/validation-services.md): first validation implementation
- [docs/architecture/pilot-supported-adapter.md](docs/architecture/pilot-supported-adapter.md): first supported-path pilot adapter
- [docs/architecture/development-environment.md](docs/architecture/development-environment.md): current Conda-based dev/test policy
- [docs/architecture/release-strategy.md](docs/architecture/release-strategy.md): release, installer, and updater planning
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
- PyNWB-backed assembly service for minimal NWB output
- Composite validation made up of artifact-policy checks plus PyNWB schema validation
- Supported-path pilot adapter for structured `session_manifest.json` sources

The supported-path pilot adapter is intentionally a repo-native fixture source for architecture validation. It is not yet a claim of real acquisition-format support.

All current implementation slices are backed by tests and documented under `docs/architecture/`.

## Local development

Current development and testing should use the dedicated `nwbforge-dev` Conda environment:

```text
powershell -ExecutionPolicy Bypass -File scripts/setup-conda-dev.ps1
powershell -ExecutionPolicy Bypass -File scripts/test-conda-dev.ps1
```

This environment is intended only for development. Release artifacts should package everything needed so that Conda or virtual environments are not required for end users.

## Initial next steps

1. Add NWB Inspector integration and richer validation reporting.
2. Expand assembly coverage beyond the current minimal metadata subset.
3. Choose the first real supported acquisition format and spike a NeuroConv-backed adapter.
4. Continue release-packaging design toward installer and updater implementation once the desktop application direction is finalized.
