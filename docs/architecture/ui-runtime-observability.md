# UI Runtime And Observability Baseline

Last updated: 2026-03-31

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

## Expected first implementation contracts

- `PipelineProgressEvent`
- `PipelineStage`
- `PipelineRuntimeError`
- `ConversionWorker` or equivalent background-runner abstraction
- `LogSink` abstraction that can feed file output and an optional in-app viewer

## Immediate follow-on work

1. Define domain-safe runtime event models for stage, progress, and error propagation.
2. Define a worker/executor abstraction that the future desktop UI can consume.
3. Define structured logging conventions before instrumenting broader backend code paths.
