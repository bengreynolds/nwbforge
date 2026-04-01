# Package Management Baseline

Last updated: 2026-04-01

## Purpose

This note captures the current route-based dependency-management direction for developer setup and the future desktop package-install flow.

## Core model

Package installation is framed around supported route names rather than raw dependency names. Examples:
- `DeepLabCut`
- `ScanImage`
- `Audio`
- `Excel`

The route catalog should be the shared source of truth for:
- developer bootstrap
- future initial setup UI
- future `File -> Install Extensions / Packages` flow

## Current implementation baseline

The repository now includes a Python package-planning layer under `src/nwbforge/app/packages/` that provides:
- curated route package specs
- named presets
- install-plan resolution for `minimal`, `selected`, and `full` modes
- persisted selection state for repeated setup runs

Current route package catalog examples:
- `audio`
- `deeplabcut`
- `excel`
- `image`
- `scanimage`

## Setup modes

- `minimal`: core repository dependencies only
- `selected`: a chosen preset or explicit route-name subset
- `full`: all curated route packages

## Presets

- `minimal`
- `common`
- `full`
- `custom`

`common` is intended to cover the currently exercised optional route packages during active development. `full` is reserved for broader development coverage and can include heavier or not-yet-implemented route packages where early install support is still useful.

## Persistence

The current setup flow persists the selected install plan at:
- `.nwbforge/install-selection.json`

This file is local state, not tracked source.

## Future UI expectations

Initial setup should:
- show the same preset names
- let the user select route names explicitly
- validate compatibility before starting installs
- show progress and errors during install work

Post-setup package installation should be accessible from:
- `File -> Install Extensions / Packages`

That later flow should:
- install additional route packages without requiring a full reinstall
- reuse the same route catalog and preset language
- report progress and failures through the standard runtime/logging model
