# Qt Widget Baseline

Last updated: 2026-04-03

## Purpose

This note captures the current concrete desktop widget layer under `src/nwbforge/ui/qt/`. The goal is no longer only to prove widget bindings; it is also to keep the local desktop app visually coherent, fast enough for internal testing, and organized around one integrated application workspace.

## Implemented widgets

### `MainWindow`

Location: `src/nwbforge/ui/qt/main_window.py`

Responsibilities:
- host the first `QMainWindow` shell
- apply the shared desktop visual system and workspace header treatment
- expose the current `File` menu actions
- bind shell/package/conversion state into the status bar
- host one integrated tabbed workspace for conversion, direct ingest, packages, settings, and NWB viewing
- host the conversion-session central widget
- host the new-session assembly workspace
- host the docked log viewer
- host the package-install workspace
- host the settings workspace
- host a manually testable real desktop composition built from the current backend services
- open and save explicit direct-ingest project files from the shell
- open supported, custom, and hybrid session fixtures or saved-state descriptors from disk through `File -> Open Session...`
- open arbitrary `.nwb` files into the integrated NWB viewer through `File -> Open NWB...`
- rebuild the `Open Recent Project` submenu from persisted project-history state
- rebuild the `Open Recent` submenu from persisted session-history state
- expose explicit `New Session` and `Reopen Last Session` actions
- route `New Session` into the direct-ingest session-assembly workflow instead of treating it as a simple screen reset
- preserve in-progress direct-ingest drafts when `New Session` is reopened
- open generated `.nwb` artifacts in the app-owned integrated viewer tab instead of delegating them to the operating system
- keep routine workflows inside the same main window instead of depending on separate top-level dialogs or windows

### `SessionAssemblyDialog`

Location: `src/nwbforge/ui/qt/session_assembly_dialog.py`

Responsibilities:
- let users add files and folders to a new conversion session
- present direct-ingest work through a cleaner split layout and dedicated grouping/metadata tabs
- show the suggested session id, title, pathway, source preview, and assembly issues
- show saved-project path and clean/dirty status
- show detected dataset-group summaries with pathway and role composition
- show detected dataset-group kind and anchor-path context
- show detected dataset-group reasons and member summaries
- support lightweight dataset-level grouping actions for selected groups and selected sources
- persist and surface explicit group-confirmation state for detected groups
- block session creation until required grouped bundles are explicitly confirmed
- remove selected inputs from the draft
- edit source-specific metadata overrides for the selected source
- create a real `ConversionSession` through `SessionAssemblyScreenModel`

### `ConversionSessionWidget`

Location: `src/nwbforge/ui/qt/conversion_session_widget.py`

Responsibilities:
- render one loaded conversion session
- present high-level pathway/stage/validation/artifact metrics before deeper workflow controls
- show source summaries, selected-source details, and output-path entry
- separate the session workflow into dedicated summary, execution, review, and artifact panes
- summarize run readiness through explicit stage, output-target, validation-count, artifact-count, and review-guidance fields
- expose the right-hand conversion workspace through explicit desktop tabs for run overview, review work, metadata review, and artifacts
- expose saved snapshot history through a dedicated history tab with explicit restore actions
- expose runtime progress history through a dedicated diagnostics tab for manual-testing triage
- surface recovered latest-state session information when a saved snapshot exists for the reopened session
- open a save dialog for NWB output selection through the shell-provided chooser callback
- start preview and execution through `ConversionSessionScreenModel`
- display current status and final preview/execution result text
- render validation-summary and review-outcome details
- render generated execution/review artifacts from projected provenance state
- open a selected generated artifact or its containing folder directly from the widget
- open the validation report and latest review decision directly through dedicated shortcuts
- delegate artifact-open and reveal behavior to shell-provided callbacks so missing files and failed shell launches can use the standard desktop error path
- render issue acknowledgement, reviewer, rationale, and approve/reject controls for review submission
- render pending mixed-source metadata conflicts as explicit canonical-key comparisons with source-value context and normalization notes
- let users promote a selected source value into a session-wide override directly from the metadata-review workspace
- let users type a manual session-wide override directly from the metadata-review workspace
- let users apply and clear source-specific overrides from the metadata-review workspace
- show summary counts for pending conflicts, session overrides, and source overrides
- filter metadata conflicts between pending and resolved states
- clear all override state for one canonical field from the metadata-review workspace
- show resolution-status and derived override-history detail for the selected metadata conflict

### `PackageInstallerDialog`

Location: `src/nwbforge/ui/qt/package_dialog.py`

Responsibilities:
- render install mode and preset selection
- present route-based package setup through cleaner options, route-list, and summary sections
- render selectable route packages for custom route sets
- show resolved extras, compatibility issues, and install status
- submit background installs through `PackageInstallerScreenModel`
- behave as an embedded workspace panel instead of a separate top-level dialog

### `SettingsDialog`

Location: `src/nwbforge/ui/qt/settings_dialog.py`

Responsibilities:
- render persisted desktop settings for verbose logging and file-log configuration
- present desktop preferences through a cleaner settings header and grouped form layout
- present recovery/history controls alongside logging controls
- manage draft changes through `SettingsScreenModel`
- save or discard settings without embedding persistence logic in widgets
- behave as an embedded workspace panel instead of a separate top-level dialog

### `LogViewerDockWidget`

Location: `src/nwbforge/ui/qt/log_viewer.py`

Responsibilities:
- render `InMemoryUiLogSink` entries as plain text
- support the shell's optional log-viewer workflow
- preserve the original logging-event timestamp in visible UI entries
- append incrementally when possible instead of redrawing the full log buffer on every update

### `NwbViewerWidget`

Location: `src/nwbforge/ui/qt/nwb_viewer_widget.py`

Responsibilities:
- host the integrated read-only NWB viewer workspace
- apply the shared desktop visual system to the generic NWB browser path
- support `File -> Open NWB...` and `Reload`
- support an optional `Open Rich Preview` action for the selected node when richer renderer packages are installed
- render a lazy tree over major NWB sections and child nodes
- keep all branches collapsed by default except the initial metadata expansion
- render selected-node details through a dedicated detail pane
- emit viewer status back to the main shell without requiring a second window lifecycle

### `NwbViewerWindow`

Location: `src/nwbforge/ui/qt/nwb_viewer_window.py`

Responsibilities:
- provide a thin compatibility wrapper around `NwbViewerWidget`
- preserve standalone manual/viewer-specific entry points where useful
- avoid becoming the primary routine viewer path for the local desktop app

### `NwbDetailPane`

Location: `src/nwbforge/ui/qt/nwb_detail_pane.py`

Responsibilities:
- render summary metadata for the selected NWB node
- show text/scalar detail, table previews, and bounded array/time-series previews
- stay backend-thin by consuming structured node-detail payloads instead of traversing the file directly

### Shell-level error presentation

Location: `src/nwbforge/ui/qt/main_window.py`

Responsibilities:
- observe `DesktopShellState.last_user_error`
- present translated user-facing errors through a central warning dialog
- keep package and conversion widgets free of ad hoc popup policy

### `StateBridge`

Location: `src/nwbforge/ui/qt/bridge.py`

Responsibilities:
- translate model callbacks into Qt signals so widget updates happen through QObject signal delivery

## Design constraints

- The Qt layer is intentionally thin and should not become a second application-service layer.
- Widget code should bind to `DesktopShellModel`, `PackageInstallerScreenModel`, `ConversionSessionScreenModel`, and shared UI observability helpers rather than duplicating their logic.
- Background execution remains owned by runtime executors and backend services, not by widgets.
- Logging still flows through standard logging plus `UiLogHandler`; widgets only render captured entries.
- The shell may mirror logs through `CompositeUiLogSink` so the docked log viewer and a file-backed JSON-lines sink receive the same entries.
- UI-visible logs should use real event timestamps and avoid unnecessary full-buffer redraw work.
- The conversion-session widget should preserve clear workflow sections instead of collapsing status, review, and artifacts into one undifferentiated stacked form.
- The conversion-session widget should prefer desktop navigation patterns such as tabs when they make the review and artifact workflow easier to scan.
- The conversion-session widget should keep enough source/session context visible that supported, custom, and later hybrid sessions remain readable without opening a second inspector view.
- Routine desktop workflows should default to one integrated main window unless a separate top-level window is strongly justified.
- The NWB viewer should remain generic and read-only; validation, conversion, and workflow-specific controls should stay outside the viewer surface even when it is embedded in the main shell.

## Testing baseline

- Widget tests live under `tests/ui/qt/`
- Tests run headlessly with `QT_QPA_PLATFORM=offscreen`
- Current coverage validates:
  - File-menu wiring
  - integrated workspace-tab switching for `New Session`, packages, settings, and the NWB viewer
  - direct-ingest project open/save wiring
  - log-dock visibility and log capture
  - package workspace binding and route-list rendering
  - conversion-session preview/execution bindings
  - conversion-session section layout for summary, execution, review, and artifacts
  - direct-ingest detected-group summaries in the `New Session` dialog
  - direct-ingest dataset-group kind/anchor summaries in the `New Session` dialog
  - direct-ingest dataset-group reason/member summaries in the `New Session` dialog
  - create-session blocking until required grouped bundles are confirmed
  - direct-ingest group rename, confirmation, split-group, split-selection, and selected-source create/move actions in the `New Session` dialog
  - conversion-session source-detail presentation for pathway, source count, and selected-source metadata
  - conversion-session run-overview and review-guidance summaries
  - conversion-session workspace-tab structure and state-driven tab selection, including metadata-review focus for pending mixed-source conflicts
  - conversion-session metadata-resolution actions that clear stale preview/execution state and require rebuild
  - conversion-session source-specific metadata-resolution actions from the metadata-review workspace
  - conversion-session manual session-override actions and metadata-resolution summaries
  - conversion-session metadata-review filtering and clear-all-field-override actions
  - conversion-session recovery display for latest saved artifacts, validation state, review state, and output path
  - conversion-session snapshot-history listing and restore actions
  - conversion-session runtime diagnostics history presentation
  - settings-dialog save flow and runtime logging reconfiguration
  - conversion-session review submission bindings
  - source-specific direct-ingest metadata override bindings
  - direct-ingest project recovery through reopened draft state
  - integrated NWB viewer file-open behavior, default collapsed tree behavior, metadata-first initial expansion, and shell-level launch from generated `.nwb` artifacts

## Current limitations

- no persisted window/layout state yet
- file-backed logging is opt-in and does not yet have an app-level retention/configuration policy
- no end-to-end packaged desktop entry point yet
- NWB viewing still uses generic previews rather than richer modality-specific renderers
- richer previews now exist only as an optional browser-backed `nwbwidgets + Panel` path rather than a native Qt rendering layer

## Temporary manual launcher

- `scripts/run_app.py` provides a temporary Python entry point for manual desktop testing
- it now bootstraps the real desktop service composition from `src/nwbforge/app/desktop.py`
- it loads either a user-provided `session_manifest.json`, `custom_session.json`, or `hybrid_session.json` path via `--session`, a direct-ingest project via `--project`, or the default direct-ingest `New Session` workflow
- it can also pre-load the integrated viewer through `--view-nwb`
- it should be treated as a development aid, not as the final application startup path

## Ingest direction

- the current Qt shell can open JSON session fixtures and descriptors, but that is not the intended primary user workflow
- the primary future desktop entry should be `New Conversion Session`, where users add real files and folders directly and the app assembles a candidate session from inspection results
- the first concrete implementation of that direction now exists through `SessionAssemblyDialog` and `SessionAssemblyScreenModel`
- JSON session files may remain as saved-project or recovery/reopen artifacts, but the widget layer should not be optimized around requiring users to author them by hand

## Immediate follow-on work

1. Expand the new-session assembly dialog from the current role-assignment, group-summary, group-confirmation/group-action baseline, simple sidecar association, explicit saved-project workflow, and narrow metadata-override baseline into richer dataset/session modeling and field-by-field disagreement-resolution workflows.
2. Improve multi-source/hybrid provenance presentation and source-specific metadata UX without losing the current source/session clarity.
3. Add richer NWB node renderers only where the generic viewer proves insufficient.
4. Add persisted window/layout state once the core desktop information architecture settles.
