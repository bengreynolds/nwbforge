# Decisions

This log keeps the durable repository decisions. Route-level implementation churn has been collapsed into broader themes so the file stays readable.

## 2026-03-31 to 2026-04-09

### DEC-001: Keep supported, custom, and hybrid pathways as first-class workflows
Status: Accepted

Reasoning:
- The workflow, risk profile, and review needs differ across the three cases.
- A single undifferentiated conversion path would hide important complexity.

Consequences:
- Session orchestration branches by pathway
- Reports and reviews must state the pathway explicitly
- Tests should cover each pathway separately

### DEC-002: Keep normalization separate from adapters and NWB assembly
Status: Accepted

Reasoning:
- Source naming and NWB semantics should not be coupled directly.
- A dedicated normalization layer improves reuse, traceability, and lab-profile support.

Consequences:
- Canonical internal models are a core design asset
- Adapters remain focused on extraction
- NWB assembly targets normalized models instead of raw parser output

### DEC-003: Use NeuroConv first for supported ingestion, with PyNWB as the fallback for custom or hybrid assembly
Status: Accepted

Reasoning:
- Existing NWB ecosystem tooling should be reused wherever it already fits.
- Lower-level PyNWB control is still needed for unsupported and hybrid cases.

Consequences:
- Supported-path work must check NeuroConv before manual converter design
- Direct PyNWB remains the fallback for unsupported or unusually custom cases
- PyNWB docs are the source of truth for low-level NWB API usage

### DEC-004: Keep repo governance explicit and review-first
Status: Accepted

Reasoning:
- Long-lived agent collaboration needs small canonical docs that stay current.
- Branch and PR rules should be stable and easy to discover.

Consequences:
- `dev` is the working branch; `main` is the integration target
- `planning.md`, `AGENTS.md`, and `decisions.md` stay current together
- PR review is the default integration checkpoint

### DEC-005: Treat release engineering as a first-class architecture concern
Status: Accepted

Reasoning:
- The product is intended for non-technical lab users and must ship as a desktop app.
- Installer, updater, and rollback behavior materially affect architecture and trust.

Consequences:
- Release and update design must be specified before implementation
- Final releases are planned around a PyInstaller-first payload wrapped in native installers
- Packaging risks such as compiled dependencies and signing must be planned explicitly

### DEC-006: Keep validation, review outcomes, and persisted artifacts separate
Status: Accepted

Reasoning:
- Schema validation and best-practice inspection answer different questions.
- UI and workflow layers need stable artifacts rather than only in-memory summaries.

Consequences:
- Validation composes artifact checks, PyNWB schema checks, and NWB Inspector checks
- Validation reports are written as machine-readable artifacts
- Review decisions are persisted separately from raw validation results

### DEC-007: Start session persistence with JSON snapshots and bounded history
Status: Accepted

Reasoning:
- Execution and review state need a resumable store before a richer local database is chosen.
- Keeping a stable latest snapshot path preserves reopen behavior.

Consequences:
- Session persistence writes the latest snapshot plus bounded history
- The desktop workflow can reopen or restore previous session states
- Recovery settings are explicit desktop preferences

### DEC-008: Make direct ingest the primary desktop path and keep JSON session loading as compatibility state
Status: Accepted

Reasoning:
- The app should start from real file/folder ingest rather than hand-authored session descriptors.
- Saved project/session files are useful for recovery, reopen, and testing, but not as the primary scientific input model.

Consequences:
- `New Session` is the default desktop entry point
- Supported, custom, and hybrid inputs can mix in one draft session
- Project/session files remain compatibility and saved-state paths

### DEC-009: Treat source roles, metadata overrides, and conflict review as first-class workflow state
Status: Accepted

Reasoning:
- Mixed-source disagreement should be explicit rather than accidental.
- Reviewable conflicts are better than silent inference.

Consequences:
- Session-wide overrides merge at the normalization/session layer
- Source-specific overrides attach at the inspection boundary
- Source roles influence precedence and provenance ordering
- A dedicated metadata-review workspace is preferred over ad hoc notes

### DEC-010: Treat logging, progress, and background work as explicit runtime contracts
Status: Accepted

Reasoning:
- Long-running conversion and install work must not block the UI thread.
- Users and testers need stage, progress, and error reporting that maps to real work.

Consequences:
- Background execution is required for conversions and installs
- Structured logs are part of the runtime contract
- UI-visible timestamps should preserve the original logging event time

### DEC-011: Organize supported routes by family modules and gate optional routes on installed dependencies
Status: Accepted

Reasoning:
- Supported-route growth is easier to scale when semantically related routes share family modules.
- Optional routes should only appear when their curated dependencies are present.

Consequences:
- Category-first packaging is preferred for shared semantics
- The route catalog becomes the package-install and registry gate
- Ambiguous readers should be matched conservatively

### DEC-012: Compose combined NeuroConv workflows from existing delegates before inventing bespoke writers
Status: Accepted

Reasoning:
- Combined workflows should be recognized and executed honestly without forcing a new writer design too early.
- Reusing existing delegates keeps the workflow layer smaller and clearer.

Consequences:
- Workflow adapters can match whole-session combinations
- Direct execution should compose existing direct delegates first
- Bespoke workflow writers remain optional follow-on work

### DEC-013: Keep the integrated desktop workspace and embedded NWB viewer as the normal shell path
Status: Accepted

Reasoning:
- Routine desktop workflows are easier to test and use inside one integrated window.
- Read-only NWB viewing should remain available without folding it into conversion state.

Consequences:
- The main shell hosts conversion, ingest, packages, settings, and viewing
- The standalone viewer remains a compatibility wrapper
- Optional rich preview stays layered on top of the PyNWB-first baseline

### DEC-014: Keep current internal-testing deviations explicit until the workflow is hardened
Status: Accepted

Reasoning:
- Temporary shortcuts should not be mistaken for settled architecture.
- Internal testing needs explicit deviation notes for anything that still affects UX, grouping, conflicts, or logging.

Consequences:
- Planning tracks known deviations instead of smoothing them over
- Release work stays deferred until the desktop baseline is stable
- The next iteration should focus on hardening, not broad new scope
