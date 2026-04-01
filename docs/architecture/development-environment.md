# Development Environment Baseline

Last updated: 2026-04-01

## Purpose

This note captures the current local development and test environment policy.

## Current policy

For now, project installs and test runs should use a dedicated Conda environment:
- environment name: `nwbforge-dev`
- environment spec: `environment.yml`
- setup helper: `scripts/setup-conda-dev.ps1`
- test helper: `scripts/test-conda-dev.ps1`
- persisted selection state: `.nwbforge/install-selection.json`

The helpers explicitly disable Python user-site package resolution so development work does not silently depend on unrelated local installs.

## Bootstrap modes

The setup helper now supports three install modes inside the dedicated Conda environment:
- `minimal`: core repository dependencies only
- `selected`: install a named preset or explicit route-name subset
- `full`: install the full curated route package set

The `selected` mode supports these presets:
- `minimal`
- `common`
- `full`
- `custom`

Route selection is expressed in user-facing route names such as `DeepLabCut` or `ScanImage`, not raw dependency strings. The current setup flow persists the selected install set so later setup runs can reuse it.

## Current default workflow

Current test/development helpers default to the `common` selected preset because it covers the route packages exercised by the current automated test suite without forcing the heaviest future extras on every setup run.

## Why Conda for now

- it gives the project an isolated and repeatable local runtime
- it avoids interfering with existing Python environments on the machine
- it is a practical short-term answer while the desktop packaging and installer story is still being built

## Release policy

The Conda environment is a development-only workflow. Release artifacts must not require:
- Conda
- virtual environments
- manual dependency installation

Production releases should remain fully self-contained installers or installable packages as described in [release-strategy.md](release-strategy.md).
