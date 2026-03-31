# Decisions

This is the repository's canonical decision log. Historical decisions and reversals should be recorded here as the project evolves.

## 2026-03-31

### DEC-001: Treat supported, custom, and hybrid conversion pathways as first-class concepts
Status: Accepted

Reasoning:
- The workflow, risk profile, and review needs differ materially across these cases.
- A single undifferentiated `conversion` pipeline would hide critical complexity and make UX and validation weaker.

Consequences:
- Session orchestration must branch by pathway
- Reports should state the pathway explicitly
- Tests should cover each pathway separately

### DEC-002: Keep metadata normalization separate from source adapters and NWB assembly
Status: Accepted

Reasoning:
- Source naming and NWB semantics should not be coupled directly.
- A dedicated normalization layer improves reuse, traceability, and lab-profile support.

Consequences:
- Canonical internal models become a core design asset
- Source adapters remain focused on extraction
- NWB assembly can target normalized models instead of raw parser output

### DEC-003: Use NeuroConv first for supported ingestion, PyNWB for custom or hybrid assembly
Status: Accepted

Reasoning:
- Existing NWB ecosystem tooling should be reused wherever it already fits.
- Lower-level PyNWB control is still necessary for unsupported and hybrid cases.

Consequences:
- Supported-path adapters should evaluate NeuroConv before custom parsing is written
- The architecture must accommodate both direct and lower-level assembly paths

### DEC-004: Use `main` as the default integration branch and retire `master`
Status: Accepted

Reasoning:
- Repository conventions should be explicit from the start.
- The working branch model already centers development on `dev` with PR-based integration.

Consequences:
- `main` is the protected integration target
- `dev` remains the active working branch
- Documentation should not refer to `master`

### DEC-005: Start implementation by codifying canonical domain contracts
Status: Accepted

Reasoning:
- The architecture depends on stable boundaries between raw sources, normalized metadata, mapping plans, provenance, and validation.
- Defining these contracts first reduces downstream coupling when adapters and services are added.

Consequences:
- Initial implementation lives in `src/nwbforge/domain/`
- Early tests target immutable contract behavior rather than conversion logic
- Later orchestration, adapter, and NWB-writing layers should depend on these models instead of inventing parallel payload shapes

### DEC-006: Make adapters and orchestration services contract-first
Status: Accepted

Reasoning:
- Supported, custom, and hybrid workflows need a shared boundary between raw source inspection and downstream normalization.
- The registry and service interfaces should stabilize before concrete adapters or application services are added.

Consequences:
- Adapter output flows through `ExtractedField` and `ExtractionResult`
- Adapter discovery is centralized in `AdapterRegistry`
- Orchestration-facing services should implement explicit protocols rather than exchange untyped dictionaries

### DEC-007: Start concrete application services with inspection dispatch and provenance assembly
Status: Accepted

Reasoning:
- These services are deterministic and low-risk, but they exercise the new adapter and domain boundaries in a real way.
- They provide immediate orchestration value without forcing premature normalization or NWB-mapping logic.

Consequences:
- `RegistrySourceInspectionService` becomes the default path for adapter-backed source inspection
- `SessionProvenanceService` becomes the first concrete provenance builder
- Later services should follow the same narrow, contract-driven pattern

### DEC-008: Start normalization with a conservative alias-driven rule set
Status: Accepted

Reasoning:
- The project needs a concrete normalization layer, but broad ontology inference would be premature at this stage.
- A small declarative alias set gives us useful behavior while keeping assumptions reviewable and easy to change.

Consequences:
- `RuleBasedNormalizationService` is the current normalization baseline
- Unknown or conflicting fields are preserved and marked for review
- Lab-profile overrides and broader device/stream normalization remain future work

### DEC-009: Start mapping with an explicit reviewable plan, not direct NWB construction
Status: Accepted

Reasoning:
- The architecture depends on separating mapping intent from NWB assembly.
- Early mapping logic should make assumptions visible before any writer layer exists.

Consequences:
- `RuleBasedMappingPlanner` emits `MappingDecision` and `ReviewIssue` records only
- Required-field gaps surface as blocking issues in the plan
- Identifier generation remains an explicit reviewable transform until assembly policy is settled

### DEC-010: Make `planning.md`, `AGENTS.md`, and `decisions.md` the continuously maintained core docs
Status: Accepted

Reasoning:
- Long-lived agent collaboration depends on a small set of canonical documents that are always current.
- Repository guidance needs one clear decision source instead of split, drifting references.

Consequences:
- `planning.md`, `AGENTS.md`, and `decisions.md` are mandatory maintenance targets
- `docs/decision-log.md` remains a compatibility path only
- Future architectural and process decisions should be recorded in `decisions.md`

### DEC-011: Treat release engineering as a first-class architecture concern
Status: Accepted

Reasoning:
- The product is intended for department-wide, non-technical users and must ship as a production-grade desktop application.
- Installer, updater, and rollback behavior materially affect architecture, packaging, and user trust.

Consequences:
- Release and update design must be specified in planning before implementation
- Cross-platform installers, update behavior, and versioning become core architecture concerns
- Future UI and distribution choices must be evaluated against installer and updater requirements
