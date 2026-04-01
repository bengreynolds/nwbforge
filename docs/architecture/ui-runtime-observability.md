# UI Runtime And Observability Baseline

Last updated: 2026-04-01

## Purpose

This note captures the required runtime behaviors for the desktop shell and the current baseline for surfacing them through UI models and widgets.

## Required runtime behaviors

### Background execution
- all conversion work must run off the main UI thread
- the runtime layer may use threads, workers, or async orchestration, but the UI must remain responsive
- long-running tasks must report real stage and progress events back to the UI

### Structured logging
- actionable runtime paths must use a standard logger
- `print` statements are not acceptable for conversion diagnostics
- logs should carry enough context to correlate events with session id, source id, adapter id, and pipeline stage
- the runtime must support a normal mode and a verbose conversion mode

### Progress and status
- progress updates must be tied to real work, not timers
- both percentage progress and coarse stage transitions are required
- the UI should expose:
  - a status bar for high-level stage text
  - a progress bar bound to actual task progress
  - an optional log viewer for deeper diagnostics

### Error handling
- backend exceptions must be caught and logged with context
- the UI should receive concise user-facing error messages derived from those failures
- detailed stack/context remains available through logs rather than becoming the primary user message
- silent failures are not acceptable

## Architectural boundaries

- conversion logic emits runtime events; it does not manipulate UI widgets directly
- UI components render status, progress, and logs; they do not own conversion-state truth
- logging, progress reporting, and user-facing error messages should be modeled through explicit contracts
- future desktop menu structure should include a `File` menu with settings entry and modular hooks for future tools/extensions
- future desktop menu structure should include `File -> Install Extensions / Packages` backed by the same curated route catalog used during setup

## Implemented contracts

- `PipelineProgressEvent`
- `PipelineStage`
- `PipelineRuntimeError`
- `ThreadedConversionExecutor`

Current scope:
- `ConversionPipelineService` now emits real stage/progress events at inspection, normalization, mapping, writing, validation, and terminal states
- `ThreadedConversionExecutor` runs preview and execution work off the calling thread and wraps failures in `PipelineRuntimeError`
- `ThreadedPackageInstallationExecutor` now runs route-based package installs off the calling thread and preserves install-stage progress/failure events
- structured logging is now implemented across `ConversionPipelineService`, `NeuroConvSupportedExecutionService`, and `ThreadedConversionExecutor`
- log records now carry stable context payloads for session id, source id, adapter id, output path, and related runtime details where applicable
- `DesktopShellModel` now gives the future UI a toolkit-agnostic shell state for File-menu actions, status-bar text, progress display, and log-viewer visibility
- `PackageInstallerScreenModel` now gives the future setup and extension-install UI a toolkit-agnostic state model over `PackageManagementController`
- `ConversionSessionScreenModel` now gives the future conversion-session UI a toolkit-agnostic state model over `ConversionExecutor`, `PipelineProgressEvent`, and `PipelineRuntimeError`
- `InMemoryUiLogSink` and `UiLogHandler` now provide the first shared log-viewer bridge from standard logging into UI-visible log entries
- `DefaultUiErrorPresenter` now provides one shared translation policy for package-install and conversion runtime errors across the UI model layer
- `PySide6` widget bindings now exist for the first desktop shell slice, including a `QMainWindow`, status bar, log dock, package-install dialog, and conversion-session widget that consume the existing UI-model layer
- the current widget tests run headlessly with an offscreen Qt platform and validate real menu, dialog, progress, and log-viewer bindings
- the current shell can optionally mirror UI-visible logs into a JSON-lines file through a composite sink while retaining the in-memory log viewer
- shell-level `UserFacingError` payloads are now presented through real warning dialogs in the Qt shell instead of only appearing as status-bar text

Still pending:
- richer widget behavior beyond the current baseline shell/dialog/panel set
- broader structured logging coverage across persistence, review, and plugin paths
- broader dialog/banner presentation beyond the current shell-level warning dialogs

## Immediate follow-on work

1. Expand the current file-backed/composite log-sink path into a durable app-level default and retention policy.
2. Add richer dialog/banner presentation on top of the current shell-level warning-dialog baseline.
3. Expand the current widget layer with additional screens and layout polish without bypassing the existing UI-model contracts.
