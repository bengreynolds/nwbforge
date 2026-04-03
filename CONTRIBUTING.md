# Contributing to NWB Forge

## Overview

NWB Forge accepts community contributions for bug fixes, conversion improvements, additional proprietary or custom data-format support, documentation, and performance work.

This repository is maintained with a review-first workflow:
- all meaningful changes should arrive through pull requests
- direct commits to `main` are not permitted
- contributors should target `dev` or a short-lived feature branch created from `dev`

The primary maintainer is Benjamin Reynolds.
- Contact: benjamin.g.reynolds@ucdenver.edu
- Affiliation: Christie Lab (Jason Christie)

## Contribution model

Contributors are expected to preserve the repository’s layered architecture:
- UI and workflow orchestration
- source adapters and parsers
- metadata normalization
- NWB mapping and assembly
- validation and provenance

Keep proprietary-format logic isolated from shared application flow. Do not hardcode lab-specific assumptions into common paths unless the behavior is explicitly planned and documented.

Before making substantial implementation changes:
1. Read [AGENTS.md](AGENTS.md).
2. Read [planning.md](planning.md).
3. Check [decisions.md](decisions.md) for existing architectural decisions.

## Issues

All users may file issues.

When reporting a problem, include:
- a clear description of the issue
- reproduction steps
- expected behavior versus actual behavior
- relevant logs, tracebacks, or screenshots when available

For conversion-related issues, also include:
- source data format or acquisition system
- NeuroConv package or route, if applicable
- failure stage, such as ingest, grouping, preview, mapping, write, or validation

## Pull requests

All pull requests should:
- target a non-`main` branch
- describe the change clearly
- reference related issues when applicable
- remain consistent with the existing architecture and naming
- avoid introducing breaking changes without justification

For conversion-related pull requests, also:
- describe the handled data format clearly
- document assumptions about file structure and scientific meaning
- add tests or validation coverage where practical
- state any remaining ambiguity explicitly instead of silently claiming a mapping

## Development expectations

Current development and testing should use the dedicated Conda environment defined by [environment.yml](environment.yml).

Recommended baseline:

```text
conda env update -n nwbforge-dev -f environment.yml
conda run -n nwbforge-dev python -m pytest
```

When behavior changes:
- update tests where feasible
- update planning or architectural docs when the contract changes materially
- keep commits scoped and reviewable
- separate documentation changes from implementation changes when practical

## Design and scientific safety

Contributions should follow these principles:
- protect scientific interpretability
- prefer durable contracts over ad hoc scripts
- surface uncertain mappings for review
- treat supported, custom, and hybrid pathways as shared-contract workflows rather than isolated products

If a format is not supported by NeuroConv, say so explicitly before introducing a direct PyNWB path. If a representation would need an NWB extension, document that requirement explicitly.

## License

This project uses the MIT License. See [LICENSE](LICENSE).
