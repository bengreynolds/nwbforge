# NWB Forge

NWB Forge is a planned UI-driven platform for converting heterogeneous lab acquisition data into understandable, validated NWB files. The project is aimed at department-wide use across labs that range from common supported acquisition systems to proprietary or highly custom pipelines.

The architecture is intentionally split into explicit layers:
- UI and workflow orchestration
- source adapters and plugins
- metadata normalization
- NWB mapping and assembly
- validation, provenance, and reporting

The system is planned around three conversion pathways:
- Supported pathway: common formats handled primarily through existing NWB ecosystem tooling
- Custom mapping pathway: unsupported or weakly structured inputs that require explicit mapping
- Hybrid pathway: sessions that merge supported and custom inputs into one NWB output

## Current repository state

This repository is in the planning and scaffolding phase. The first objective is to establish architecture, operating rules, and documentation before building implementation code.

Key files:
- [planning.md](planning.md): living project plan and architecture document
- [AGENTS.md](AGENTS.md): persistent repository operating manual for human and agent contributors
- [docs/architecture/core-contracts.md](docs/architecture/core-contracts.md): current canonical model baseline
- [docs/architecture/adapter-contracts.md](docs/architecture/adapter-contracts.md): adapter and service-interface baseline
- [docs/architecture/application-services.md](docs/architecture/application-services.md): first concrete orchestration services
- [docs/architecture/normalization-services.md](docs/architecture/normalization-services.md): first normalization implementation
- [docs/research/nwb-ecosystem.md](docs/research/nwb-ecosystem.md): initial ecosystem research summary
- [docs/research/codex-collaboration.md](docs/research/codex-collaboration.md): repo-collaboration notes for long-lived agent workflows
- [docs/decision-log.md](docs/decision-log.md): decision history

## Recommended repository structure

```text
docs/
  architecture/
  research/
  decision-log.md
src/
  nwbforge/
tests/
```

Planned backend package layout is documented in [planning.md](planning.md).

## Local development

Install the package in editable mode before running ad hoc Python imports:

```text
python -m pip install -e .
pytest
```

## Initial next steps

1. Define adapter and registry contracts for supported and custom source systems.
2. Implement a mapping planner on top of the normalized bundle.
3. Implement validation services that wrap schema and best-practice checks.
4. Choose an initial supported-path pilot format and implement one end-to-end thin slice.
