# NWB Forge Planning

Last updated: 2026-04-09
Status: First pass complete; internal testing and hardening underway.

## Current Baseline
- Layered domain, adapter, normalization, mapping, validation, assembly, and provenance contracts exist
- PyNWB-backed assembly, PyNWB schema validation, NWB Inspector validation, validation reports, and review artifacts are implemented
- Supported routes follow a NeuroConv-first policy with category-first family modules and direct NeuroConv execution where documented
- Direct ingest `New Session` is the default desktop path; supported, custom, and hybrid inputs can mix in one session, with project save/open as saved internal state
- Direct-ingest grouping is heuristic but reviewable: sessions carry group summaries, source roles, source-specific overrides, confirmation state, split/rename/move actions, and a metadata-review workspace
- The integrated desktop shell now includes conversion, direct ingest, packages, settings, NWB viewing, diagnostics, generated-artifact actions, and structured logging
- Background execution, stage/progress/error events, and timestamp-preserving log records are part of the runtime contract
- JSON session snapshots, bounded history, review decisions, and validation reports provide resume and recovery support
- Optional supported routes are gated by installed route dependencies
- Release engineering remains post-first-pass work; the planned release model is PyInstaller-first with native installers

## Active Deviations and Risks
- JSON session/project compatibility still exists and should remain a compatibility path, not the primary ingest model
- Direct-ingest grouping is still a heuristic draft model rather than a full dataset model with durable merge/split history
- Source-role semantics and mixed-source conflict resolution are partial
- Structured logging is better but not yet uniform across every UI path
- The NWB viewer is still a generic baseline with an optional rich-preview path
- Release and installer work remain deferred until the desktop workflow is stable

## Near-Term Priorities
1. Tighten direct-ingest grouping, confirmation, and conflict resolution
2. Expand representative internal testing and capture deviations explicitly
3. Broaden structured logging and diagnostics where coverage is still thin
4. Continue supported-route growth only through the approved NeuroConv-first path
5. Defer release, installer, and updater work until the local desktop app is stable

## Open Questions
- Which representative datasets should define the internal-testing matrix?
- When should the heuristic draft model become a fuller dataset model?
- Which conflict-resolution policies should become durable defaults?
- When, if ever, should the desktop app move beyond the current integrated shell?
- What minimum provenance and validation record is required for auditability?

## References
- [AGENTS.md](AGENTS.md)
- [decisions.md](decisions.md)
- [docs/architecture/](docs/architecture/)
- [docs/research/](docs/research/)
- [docs/testing/internal-local-checklist.md](docs/testing/internal-local-checklist.md)
