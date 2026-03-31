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
2. Define service interfaces for normalization, mapping planning, provenance emission, and validation.
3. Choose an initial supported-path pilot format and implement one end-to-end thin slice.
4. Add representative sample fixtures from a small number of lab archetypes.
