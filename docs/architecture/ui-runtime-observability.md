# UI Runtime And Observability Baseline

Last updated: 2026-04-01

## Purpose

This note captures the required runtime behaviors for the future desktop shell before UI implementation begins.

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

Still pending:
- file-backed or multi-sink log output beyond the current in-memory viewer sink
- the actual desktop widget components that render status, progress, dialogs, and logs
- broader structured logging coverage across persistence, review, and plugin paths
- shared widget-level presentation of translated user-facing errors

## Immediate follow-on work

1. Add a file-backed log sink or composite sink on top of the current in-memory viewer sink.
2. Bind translated `UserFacingError` payloads into concrete dialog/banner presentation once widget code begins.
3. Introduce the first widget-level UI layer that renders shell, package-install, and conversion-session state.
