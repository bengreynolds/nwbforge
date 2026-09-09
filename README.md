# NWB Forge

NWB Forge is a desktop-focused platform for converting heterogeneous lab data into NWB with explicit review steps and provenance. The current codebase is a first-pass local desktop app: it has a real PySide6 shell, supported/custom/hybrid conversion flows, direct-ingest `New Session`, saved-project support, integrated NWB viewing, structured logging, and internal-testing workflows. It is not yet packaged for release.

## What It Does
- Converts supported, custom, and hybrid sessions through shared contracts
- Keeps normalization, mapping, assembly, validation, review, and provenance separate
- Uses NeuroConv first for supported routes and PyNWB for custom or hybrid assembly
- Treats mixed-source grouping and metadata conflicts as reviewable workflow state

## Typical Workflow
1. Start `New Session`
2. Add supported sources, custom files/folders, or both
3. Review detected groups, source roles, and metadata overrides
4. Build preview, inspect validation and metadata-review output, then write NWB
5. Open generated artifacts, review decisions, or NWB files from the shell

## Current Desktop Surface
- Conversion workspace with review, artifacts, diagnostics, and session state
- Direct-ingest project save/open and recent-project history
- Integrated read-only NWB viewer with optional rich preview
- Package-management, settings, and log-viewer tabs

## Key Docs
- [planning.md](planning.md): active plan and current deviations
- [AGENTS.md](AGENTS.md): repository operating rules
- [decisions.md](decisions.md): compact decision log
- [CONTRIBUTING.md](CONTRIBUTING.md): contribution guide
- [docs/architecture/](docs/architecture/): short architecture baselines
- [docs/research/](docs/research/): background notes
- [docs/testing/internal-local-checklist.md](docs/testing/internal-local-checklist.md): smoke and manual test baseline

## Development
Use the dedicated Conda environment defined in `environment.yml`.

```text
conda env update -n nwbforge-dev -f environment.yml
conda run -n nwbforge-dev python scripts/run_app.py
conda run -n nwbforge-dev python scripts/run_internal_smoke.py
```

## Release Direction
Final releases are planned as PyInstaller-built desktop apps wrapped in native installers. That work stays post-first-pass.

## Next Steps
1. Tighten direct-ingest grouping and conflict resolution
2. Expand representative internal testing
3. Broaden structured logging and diagnostics where coverage is still thin
4. Keep route growth on the approved NeuroConv-first path
