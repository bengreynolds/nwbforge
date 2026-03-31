# Repository Structure Proposal

## Top-level layout

```text
.
|-- AGENTS.md
|-- README.md
|-- planning.md
|-- docs/
|   |-- architecture/
|   |-- research/
|   `-- decision-log.md
|-- src/
|   `-- nwbforge/
`-- tests/
```

## Rationale

- Keep top-level guidance small and stable
- Put deeper research and design notes in `docs/`
- Reserve `src/nwbforge/` for implementation once contracts are defined
- Reserve `tests/` from the start so validation is treated as a core concern rather than a later add-on

## Planned expansion

When implementation starts, expand `src/nwbforge/` along the layered architecture documented in [planning.md](../../planning.md).
