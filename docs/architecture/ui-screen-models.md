# UI Screen Model Baseline

Last updated: 2026-04-01

## Purpose

This note captures the first toolkit-agnostic UI layer in the repository. The goal is to begin desktop-UI development without locking the project to widget code too early.

## Implemented pieces

### `DesktopShellModel`

Location: `src/nwbforge/ui/shell.py`

Responsibilities:
- expose the current File-menu baseline
- track status-bar stage text, percent complete, and error/busy state
- track log-viewer visibility
- track the currently active dialog placeholder such as `settings` or `install_packages`
- consume pipeline and package-install progress/error events without touching widgets directly

Current menu actions:
- `Settings`
- `Install Extensions / Packages`
- `Toggle Log Viewer`

### `PackageInstallerScreenModel`

Location: `src/nwbforge/ui/package_setup.py`

Responsibilities:
- load available route packages and any saved package selection
- expand preset-based route selection for the screen
- preview install requests through `PackageManagementController`
- track compatibility issues, resolved extras, and installability state
- submit background package installs through the controller
- update screen state from real package-install progress and completion/failure outcomes

## Design constraints

- UI models are toolkit-agnostic and do not import widget libraries
- view/widget code should bind to these models rather than own package-planning or runtime logic directly
- backend services remain the source of truth for package planning and execution
- runtime executors remain the source of truth for background execution behavior
- screen models may expand preset selections for display, but must preserve the backend distinction between preset-based installs and explicit custom route selection

## Current limitations

- no actual desktop widget toolkit is implemented yet
- no log-sink/viewer backend exists yet beyond shell visibility state
- shell state is in-memory only and not persisted
- the current UI layer covers package-management flows only; conversion-session screens still remain to be built

## Immediate follow-on work

1. Add a first conversion-session shell model that binds pipeline progress, status, and user-facing errors.
2. Add a log-sink abstraction that can feed both file logging and a future in-app log viewer.
3. Choose the first concrete widget toolkit layer only after the shell and screen-model contracts settle further.
