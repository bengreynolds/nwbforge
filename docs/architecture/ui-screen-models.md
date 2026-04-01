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

### `ConversionSessionScreenModel`

Location: `src/nwbforge/ui/conversion_session.py`

Responsibilities:
- load a `ConversionSession` into UI-facing state
- track source summaries, preview state, execution state, and the selected output path
- submit preview work through `ConversionExecutor`
- submit write/validation work through `ConversionExecutor`
- consume `PipelineProgressEvent` updates directly
- surface `PipelineRuntimeError` user messages into screen state

Current scope:
- one loaded session at a time
- in-memory state only
- explicit separation between preview-running and execution-running flags
- listener-based updates suitable for a future widget binding layer

## Design constraints

- UI models are toolkit-agnostic and do not import widget libraries
- view/widget code should bind to these models rather than own package-planning or runtime logic directly
- backend services remain the source of truth for package planning and execution
- runtime executors remain the source of truth for background execution behavior
- shared user-facing error translation should come from one presenter rather than ad hoc `str(exception)` handling in each screen
- shared log-viewer state should be fed from a common UI log sink rather than per-screen logging logic
- screen models may expand preset selections for display, but must preserve the backend distinction between preset-based installs and explicit custom route selection

## Current limitations

- no actual desktop widget toolkit is implemented yet
- only an in-memory log-viewer sink is implemented; file-backed or composite log sinks still remain to be added
- shell state is in-memory only and not persisted
- the current UI layer covers package-management flows and the first conversion-session screen model, but still does not include concrete widgets or persisted view state

## Immediate follow-on work

1. Add file-backed or composite log sinks on top of the current in-memory UI log sink.
2. Bind translated `UserFacingError` payloads into concrete dialog/banner behavior once widget work begins.
3. Choose the first concrete widget toolkit layer only after the shell and screen-model contracts settle further.
