# UI Screen Model Baseline

Last updated: 2026-04-01

## Purpose

This note captures the first toolkit-agnostic UI layer in the repository and how the current Qt widget baseline binds to it.

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
- clear the current session explicitly when the shell starts a new session
- track source summaries, source details, preview state, execution state, and the selected output path
- submit preview work through `ConversionExecutor`
- submit write/validation work through `ConversionExecutor`
- consume `PipelineProgressEvent` updates directly
- surface `PipelineRuntimeError` user messages into screen state
- project validation issues into UI-facing acknowledgement items
- project generated provenance artifacts into UI-facing artifact items
- capture reviewer name, rationale, override, and acknowledgement state for review submission
- submit approve/reject decisions through `ExecutionReviewService` when review support is configured
- persist latest preview, execution, and review state through `SessionPersistenceService` when desktop persistence is configured
- recover the latest saved snapshot on session load when desktop persistence is configured

Current scope:
- one loaded session at a time
- in-memory interaction state backed by latest-state snapshot persistence in the real desktop path
- explicit separation between preview-running and execution-running flags
- listener-based updates suitable for a future widget binding layer
- review controls are intentionally attached to the same session workflow instead of a separate review screen
- the same screen model now supports demo sessions plus real supported/custom/hybrid desktop sessions loaded through the desktop bootstrap module
- persistence failures are surfaced as translated user-facing errors rather than being swallowed inside the screen model
- recovered state currently restores latest artifacts, validation issues, review status, and last known output path without attempting to recreate a full execution object

### `SettingsScreenModel`

Location: `src/nwbforge/ui/settings.py`

Responsibilities:
- load persisted desktop settings through `UiSettingsService`
- manage draft settings for verbose logging and file-log configuration
- validate required settings such as the log-file path when file logging is enabled
- save settings back through the service without exposing persistence details to widgets
- expose applied settings separately from unsaved draft changes so the shell can reconfigure runtime behavior only after save
- record the last-opened session path and bounded recent-session history for shell-level reuse
- record the last-used output directory so newly loaded sessions can receive a default NWB target path

## Design constraints

- UI models are toolkit-agnostic and do not import widget libraries
- view/widget code should bind to these models rather than own package-planning or runtime logic directly
- backend services remain the source of truth for package planning and execution
- runtime executors remain the source of truth for background execution behavior
- shared user-facing error translation should come from one presenter rather than ad hoc `str(exception)` handling in each screen
- shared log-viewer state should be fed from a common UI log sink rather than per-screen logging logic
- screen models may expand preset selections for display, but must preserve the backend distinction between preset-based installs and explicit custom route selection

## Widget binding baseline

- `src/nwbforge/ui/qt/main_window.py` binds `DesktopShellModel`, `PackageInstallerScreenModel`, and `ConversionSessionScreenModel` into a thin `QMainWindow`
- the shell now also owns the first file-based session-loading step through `File -> Open Session...`, with supported/custom/hybrid session loading delegated to the desktop bootstrap helper
- the shell's recent-session submenu is now rebuilt from settings-backed recent-session state rather than widget-local memory
- the shell now also owns explicit `New Session` and `Reopen Last Session` actions while the app remains single-session
- `src/nwbforge/ui/qt/package_dialog.py` binds the route-based package-install flow into a modal dialog
- `src/nwbforge/ui/qt/conversion_session_widget.py` binds one conversion-session workflow into a central panel
- `src/nwbforge/ui/qt/settings_dialog.py` binds persisted desktop settings into a modal dialog
- `src/nwbforge/ui/qt/log_viewer.py` exposes the current in-memory UI log sink through a docked log viewer
- `src/nwbforge/ui/qt/bridge.py` provides a minimal QObject signal bridge so model callbacks can safely update Qt widgets

The current Qt layer is intentionally thin:
- widgets do not reimplement package planning or conversion lifecycle logic
- widgets render model state and invoke model/controller actions
- the toolkit-agnostic models remain the primary UI-state contracts for the application
- shell-level dialog presentation now consumes `DesktopShellState.last_user_error` so package and conversion widgets still do not own popup policy

## Current limitations

- the current widget layer supports an opt-in composite sink for file-backed JSON-lines logging, but no broader app-level log retention policy exists yet
- shell state is in-memory only and not persisted
- the current Qt widget layer is a baseline shell and does not yet include richer layout, navigation, or persisted view state
- multi-session navigation is still not implemented; the shell still works on one loaded session at a time

## Immediate follow-on work

1. Add broader shell/navigation state while preserving the current model-first architecture.
2. Expand the Qt layer with additional screens and persisted view state on top of the current review-capable conversion workflow.
3. Strengthen multi-source presentation now that hybrid sessions are real desktop flows.
