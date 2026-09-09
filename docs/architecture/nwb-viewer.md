# NWB Viewer

Purpose: provide a read-only way to inspect NWB files from the desktop shell.

Current baseline:
- The viewer opens NWB through PyNWB in read-only mode
- Tree expansion is lazy and starts from metadata-first context
- The integrated shell can launch the viewer directly, and a standalone wrapper remains for compatibility
- Optional rich preview can render selected nodes when the extra packages are installed

Constraints:
- Keep the base viewer usable without optional dependencies
- Favor generic read-only inspection over conversion-state coupling
- Preserve environment isolation for the optional preview path

Next step:
- Add richer modality-specific rendering only if it remains robust without the optional stack
