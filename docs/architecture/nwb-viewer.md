# Standalone NWB Viewer

Last updated: 2026-04-01

## Purpose

This note documents the first standalone NWB viewer path for the local desktop app.

The viewer is intentionally separate from the conversion workflow surface:
- conversion screens stay focused on ingest, preview, write, validation, and review
- the viewer handles generic read-only inspection of arbitrary `.nwb` files
- generated outputs and external NWB files use the same viewer path

## Implemented components

### `NwbFileController`

Location: `src/nwbforge/app/services/nwb_viewer.py`

Responsibilities:
- open `.nwb` files through `PyNWB` in read-only mode
- own the `NWBHDF5IO` handle and loaded `NWBFile`
- build a lazy tree model over the loaded file
- return structured node-detail payloads for UI rendering
- keep viewing logic separate from validation and conversion orchestration

### `NwbTreeModel`

Location: `src/nwbforge/app/services/nwb_viewer.py`

Responsibilities:
- expose top-level NWB sections as normalized tree nodes
- keep all branches collapsed by default on first load
- prefer a metadata-first initial expansion path
- load only immediate children for an expanded node
- represent tree state by NWB-semantic paths rather than raw widget state

### `NwbDetailPane`

Location: `src/nwbforge/ui/qt/nwb_detail_pane.py`

Responsibilities:
- render selected node details without performing file traversal itself
- show summary metadata rows for all node types
- show scalar/text content when appropriate
- show small tabular previews for `DynamicTable` objects
- show bounded array/time-series preview text without forcing full-file traversal

### `NwbViewerWindow`

Location: `src/nwbforge/ui/qt/nwb_viewer_window.py`

Responsibilities:
- own a standalone top-level viewer lifecycle
- support `File -> Open NWB...`
- support `Reload`
- optionally support `Open Rich Preview` for the selected node when optional renderer packages are installed
- keep viewer state independent from the main conversion shell
- host the tree/detail split view and default expansion behavior

### `NwbWidgetsPanelRenderer`

Location: `src/nwbforge/app/services/nwb_viewer_rich.py`

Responsibilities:
- remain optional and unavailable unless both `nwbwidgets` and `panel` are installed
- wrap the selected NWB node with `nwbwidgets.nwb2widget(...)`
- serve that widget through a small Panel session
- open the resulting rich preview in a browser without changing the base Qt viewer architecture
- keep richer rendering outside the base viewer contract so the default path remains lightweight

## Read-only behavior

- the viewer opens `.nwb` files through `NWBHDF5IO(..., mode="r", load_namespaces=True)`
- viewing is inspection-only; it does not validate, rewrite, or mutate files
- file-open errors and unreadable-file errors are surfaced explicitly

## Tree behavior

- top-level sections map to major NWB groups when present, including metadata, acquisition, processing, stimulus, intervals, analysis, scratch, lab metadata, units, and electrodes
- all nodes start collapsed on load
- the `Metadata` node is expanded initially when available
- expanding one node loads only that node’s immediate children
- selecting a node updates the detail pane without changing unrelated expansion state
- explicit actions now include:
  - `Expand All`
  - `Collapse All`
  - `Expand Children`
  - `Collapse Subtree`

## Desktop integration

- the main shell now exposes `File -> Open NWB Viewer...`
- opening a generated `.nwb` artifact from the conversion workspace now launches the standalone viewer window instead of delegating to the operating system
- `scripts/run_app.py --view-nwb <path>` can open the desktop app and a preloaded viewer window for manual testing
- inside the viewer window, `Render -> Open Rich Preview` is enabled only when the optional renderer is installed and a node is selected

## Optional renderer path

- the base viewer path depends only on `PyNWB` and the desktop Qt layer
- the optional rich renderer path uses `nwbwidgets + Panel`
- the optional dependency group is exposed through the project extra `viewer_rich`
- notebook/web tooling is still not a hard dependency of the local app baseline

## Current limitations

- initial file open still happens synchronously in the current process; lazy traversal and bounded previews are the main protection against slow loads
- the viewer currently uses generic text/table previews instead of modality-specific plots
- `nwbwidgets` integration is now available only as an optional browser-backed rich preview layer, not as a base dependency
- raw HDF5 fallback traversal is intentionally absent from the first baseline

## Immediate follow-on work

1. Add more specialized node renderers where generic text/table previews are not sufficient.
2. Consider background loading only if it can be done without compromising read-only file-handle correctness.
3. Add richer viewer launch affordances from the desktop shell once the broader local-app workflow settles.
