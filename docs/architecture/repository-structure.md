# Repository Structure Proposal

Purpose: keep the top-level layout small and predictable.

Current shape:
```text
.
|-- AGENTS.md
|-- README.md
|-- decisions.md
|-- planning.md
|-- docs/
|   |-- architecture/
|   `-- research/
|-- src/
`-- tests/
```

Rationale:
- Keep the root docs small and stable
- Put deeper research and design notes under `docs/`
- Keep implementation under `src/` and validation under `tests/`
