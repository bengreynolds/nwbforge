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

### DEC-012: Start validation with artifact-policy checks before toolchain integration
Status: Accepted

Reasoning:
- The system needs a concrete validation layer now, but PyNWB and NWB Inspector should be added deliberately rather than as an incidental dependency spike.
- Artifact-level checks provide immediate value and exercise the validation boundary cleanly.

Consequences:
- `ArtifactValidationService` is the current validation baseline
- Missing, empty, or ambiguous output artifacts can be surfaced before schema validation is integrated
- PyNWB and NWB Inspector remain the next validation-expansion steps

### DEC-013: Use a repo-native manifest adapter as the first supported-path pilot
Status: Accepted

Reasoning:
- The project needs an end-to-end supported-path slice now, but no real departmental source format has been selected and scoped yet.
- A small structured manifest source lets the architecture be exercised honestly without pretending a real acquisition format is already supported.

Consequences:
- `SessionManifestAdapter` is the first supported-path pilot adapter
- Integration tests can now cover inspection through mapping with a deterministic source fixture
- A real NeuroConv-backed format remains the next supported-path milestone

### DEC-014: Represent preview and execution as separate orchestration stages
Status: Accepted

Reasoning:
- The product must preserve transparency around what can be reviewed before writing outputs and what happens after outputs exist.
- A single opaque run call would hide important checkpoints needed for UI-driven workflows and future approval gates.

Consequences:
- `ConversionPipelineService` exposes `build_preview` and `evaluate_outputs` separately
- Preview and execution results are explicit application-layer models
- Future writer integration should fit between preview generation and output evaluation

### DEC-015: Introduce PyNWB as the first real NWB writer dependency
Status: Accepted

Reasoning:
- The project needs a real NWB-writing path to validate the architecture end to end.
- A thin PyNWB-backed writer provides a truthful implementation step without overcommitting on broader format support.

Consequences:
- `pynwb` is now a declared project dependency
- `PyNWBAssemblyService` becomes the current writer baseline
- Assembly remains intentionally narrow until richer supported formats and validation integrations are added

### DEC-016: Use a dedicated Conda environment for development, but never require it at release time
Status: Accepted

Reasoning:
- The project needs an isolated local runtime now without interfering with existing Python installations.
- End users of the released product should not be asked to manage Conda or virtual environments.

Consequences:
- Current installs and tests should use the dedicated `nwbforge-dev` Conda environment
- Development helpers should disable user-site package leakage
- Release packaging must remain fully self-contained

### DEC-017: Layer PyNWB schema validation on top of artifact-policy checks
Status: Accepted

Reasoning:
- A generated `.nwb` file should be checked for schema validity before the project adds broader best-practice inspection.
- Artifact existence checks and schema validation solve different problems and should remain composable.

Consequences:
- Validation now combines `ArtifactValidationService` with `PyNWBSchemaValidationService`
- Placeholder or unreadable `.nwb` files now fail validation even if they exist on disk
- NWB Inspector remains a separate follow-on integration rather than being folded into schema validation

### DEC-018: Use a PyInstaller-first release pipeline wrapped by native installers
Status: Accepted

Reasoning:
- The product is a desktop-oriented Python application with a likely scientific Python stack.
- End users in research labs should not be required to install Python, Conda, or manage environments manually.
- A PyInstaller-first payload preserves a Python-centric architecture while still allowing native installer and updater workflows.

Consequences:
- Final releases must package the app with PyInstaller before any installer wrapping step
- Windows, macOS, and Linux distributions must wrap the PyInstaller build in native installers or installable packages
- The in-app updater should resolve and download release assets from GitHub Releases
- Release engineering must account for scientific Python packaging risks such as compiled dependencies, larger bundles, and platform-specific signing behavior

### DEC-019: Keep NWB Inspector best-practice checks separate from PyNWB schema validation
Status: Accepted

Reasoning:
- PyNWB schema validation and NWB Inspector answer different questions and should remain independently composable.
- The current writer needs visibility into best-practice-critical gaps without hiding them behind schema-only success.

Consequences:
- Validation now composes `ArtifactValidationService`, `PyNWBSchemaValidationService`, and `NWBInspectorValidationService`
- `NWBInspectorValidationService` runs with `skip_validate=True` to avoid duplicating PyNWB schema checks
- Writer-generated NWB files can now fail execution on NWB Inspector critical findings even when schema validation passes

### DEC-020: Expand the initial writer path with richer subject and session metadata before devices or acquisitions
Status: Accepted

Reasoning:
- The next concrete value after validation integration was to close best-practice-critical gaps in the existing writer path, not jump immediately into devices or multimodal assembly.
- The manifest-backed supported pilot can now be exercised more honestly when source metadata includes experiment description and key subject fields.

Consequences:
- Canonical normalization now includes `session.experiment_description`, `subject.description`, and `subject.date_of_birth`
- The mapping planner and PyNWB writer now carry those fields through to NWB objects
- The next assembly expansion should move to devices, acquisition streams, and richer modality content rather than revisiting these core subject/session fields first
