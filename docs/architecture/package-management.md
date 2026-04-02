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
- backend package-management service contracts for future UI or setup consumers

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

## Backend service boundary

The route-based package layer now includes a backend service boundary so future UI components do not need to call planner helpers directly.

Current service-facing models:
- `PackageInstallRequest`
- `PackageCompatibilityIssue`
- `PackageInstallPreview`
- `PackageInstallProgressEvent`
- `PackageInstallResult`
- `PackageInstallRuntimeError`

Current service:
- `PackageManagementService`
- `PackageInstallationService`
- `PackageManagementController`
- `ThreadedPackageInstallationExecutor`

Current service responsibilities:
- list available route packages
- expose preset route groupings
- load the last saved selection
- preview an install request
- surface compatibility warnings or blocking issues
- persist a validated selection when requested
- execute an install command for a validated selection
- emit install progress events and structured failure information
- expose one thin UI-facing binding for route listing, preview, saved selection loading, and background install submission
- run install execution off the UI thread for future setup and extension-install screens

## Future UI expectations

Initial setup should:
- show the same preset names
- let the user select route names explicitly
- validate compatibility before starting installs
- show progress and errors during install work
- call the backend package-management service for preview/validation rather than duplicating planner logic in UI code
- call the backend package-management controller so the screen does not own service/executor wiring

Post-setup package installation should be accessible from:
- `File -> Install Extensions / Packages`

That later flow should:
- install additional route packages without requiring a full reinstall
- reuse the same route catalog and preset language
- report progress and failures through the standard runtime/logging model
- call the same backend package-management service boundary used by setup
- reuse the same backend package-install execution service used by initial setup through the controller boundary
- run the actual install through the threaded package runtime executor rather than directly on the UI thread
