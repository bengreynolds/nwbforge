# Contributing to NWB Forge

Contributions are welcome for bug fixes, conversion improvements, adapter work, documentation, and performance.

## Working Model
- Target `dev` or a short-lived branch from `dev`
- Do not commit directly to `main`
- Open PRs for meaningful changes
- Keep changes scoped and reviewable

## Before You Start
1. Read [AGENTS.md](AGENTS.md)
2. Read [planning.md](planning.md)
3. Check [decisions.md](decisions.md)

## Issues and PRs
Include:
- the problem or change clearly
- reproduction steps or example data
- expected vs actual behavior
- relevant logs, traces, or screenshots
- source format / route / failure stage for conversion work
- assumptions about file structure or scientific meaning

## Development and Testing
Use the dedicated Conda environment from `environment.yml` for installs and tests.

```text
conda env update -n nwbforge-dev -f environment.yml
conda run -n nwbforge-dev python -m pytest
```

When behavior changes:
- add or update tests when practical
- update plan or docs when contracts change
- keep assumptions explicit instead of guessing mappings

## Scientific Safety
- Protect interpretability
- Keep adapters, normalization, mapping, assembly, and validation separate
- Use NeuroConv first for supported formats
- Use PyNWB only when NeuroConv does not fit or the custom path is clearly required
- Document uncertain mappings or NWB-extension needs

## License
This repository uses the MIT License
