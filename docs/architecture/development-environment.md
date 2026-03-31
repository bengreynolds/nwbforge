# Development Environment Baseline

Last updated: 2026-03-31

## Purpose

This note captures the current local development and test environment policy.

## Current policy

For now, project installs and test runs should use a dedicated Conda environment:
- environment name: `nwbforge-dev`
- environment spec: `environment.yml`
- setup helper: `scripts/setup-conda-dev.ps1`
- test helper: `scripts/test-conda-dev.ps1`

The helpers explicitly disable Python user-site package resolution so development work does not silently depend on unrelated local installs.

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
