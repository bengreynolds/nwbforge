# AGENTS.md

## Role Definition

Contributors and coding agents in this repository act as senior scientific software and data-platform engineers building a maintainable NWB conversion platform for heterogeneous laboratory data.

Primary priorities:
- Protect scientific interpretability
- Preserve modular architecture boundaries
- Prefer durable contracts over quick one-off scripts
- Document assumptions, especially for custom mappings

## Branch Policy

- `main` is the default integration branch for the repository
- Work on `dev` or a short-lived feature branch created from `dev`
- Do not use a `master` branch in this repository
- Never commit directly to `main`
- If the current branch is `main`, stop and switch before making changes

## PR Policy

- Open pull requests for meaningful milestones; do not merge directly to `main`
- Use PR review as the default integration checkpoint
- Assume cloud Codex review workflows may be invoked with `@codex`
- Summaries on PRs should call out architecture impact, assumptions, and validation status

Note: if no remote repository is configured yet, prepare the branch and commit history locally so the next connected workflow can open the PR cleanly.

## Planning-First Rule

- Read [planning.md](planning.md) before starting implementation work
- Keep [AGENTS.md](AGENTS.md), [planning.md](planning.md), and [decisions.md](decisions.md) current as core repository documents
- If scope, architecture, or sequencing changes, update [planning.md](planning.md) in the same branch
- Do not begin substantial implementation until the affected plan sections exist and are current
- Do not implement release, installer, updater, or distribution logic before the relevant plan sections are updated

## Environment Rule

- For the current development phase, perform project installs and test runs in the dedicated Conda environment defined by [environment.yml](environment.yml)
- Use new isolated environments rather than repurposing unrelated existing environments
- Do not rely on user-site Python packages for development or test success
- Release artifacts must remain self-contained and must not require Conda or a virtual environment on user machines
- Development bootstrap may support `minimal`, `selected`, and `full` install modes, but it must still target the dedicated Conda environment rather than arbitrary active user environments

## Change-Size Rule

- Prefer small, reviewable changes with clear intent
- Keep early milestones narrow: contracts, scaffolding, and representative slices before broad feature work
- Avoid mixing architecture refactors with new feature behavior unless necessary

## Commit Policy

- Commit frequently with meaningful, scoped messages
- When work can be split cleanly, prefer more small commits over fewer large commits
- Do not batch multiple independent implementation steps into one commit just because they were completed in the same session
- Separate planning/doc changes from implementation changes when practical
- Do not squash unrelated work into a single commit just to keep history short

## Architecture Rules

- Maintain explicit boundaries between:
  - UI and workflow orchestration
  - source adapters and parsers
  - metadata normalization
  - NWB mapping and assembly
  - validation and provenance
- Source adapters must not write NWB directly
- NWB assembly code must not contain raw source-format parsing logic
- Normalize metadata into canonical internal models before NWB mapping
- Treat supported, custom, and hybrid pathways as different workflows over shared contracts, not as unrelated codepaths
- Do not design the primary user workflow around hand-authored app-specific session JSON files
- Prefer real file and folder ingestion, followed by inspection, grouping, classification, and explicit metadata override/review
- For first-pass direct ingest, prefer automatic grouping heuristics first and add richer confirmation/correction workflows incrementally
- Treat direct-ingest groups as first-class review state in the session-assembly workflow rather than only as labels attached to sources
- When refining direct-ingest grouping, prefer dataset-level group actions over piling more behavior onto per-source text edits
- For current desktop-facing startup behavior, prefer a direct-ingest `New Session` flow by default and keep JSON session loading as a compatibility, testing, or reopen path
- App-owned session or project files may exist for internal persistence, reopen behavior, or future `Save Project` flows, but they should not be the required initial user input format
- Treat explicit direct-ingest project files as saved internal workspace state for reopen/recovery, not as the primary scientific source of truth
- Session-wide metadata overrides must merge at the session/normalization layer rather than being injected through one source inspection result
- Source-specific metadata overrides should attach to the selected source, be applied at the inspection boundary, and normalize as user-supplied values
- For first-pass mixed-source conflict handling, treat source-role precedence as `primary > metadata > supplemental` and keep conflicting values reviewable
- Prefer a dedicated post-preview metadata-review surface for mixed-source conflicts instead of hiding disagreement context only in override notes or validation text
- For first actionable post-preview conflict resolution, prefer session-wide override actions from the metadata-review workspace before adding a fuller field-by-field policy editor
- For supported-path conversions, check NeuroConv support before designing a custom parser or direct PyNWB converter
- For supported proprietary or acquisition-system routes that NeuroConv documents, use direct NeuroConv conversion APIs as the primary execution path
- Use UI/orchestration code to collect metadata and user selections, then feed those into NeuroConv rather than rebuilding supported conversion logic in custom PyNWB code
- Treat official PyNWB documentation as the source of truth for NWB API usage, container placement, and file-writing patterns
- Prefer the simplest correct documented PyNWB container and method rather than wrapping built-in APIs without need
- When `pynwb.file` or another standard PyNWB module solves the problem directly, use it instead of inventing a parallel abstraction
- For software and workflows listed in [docs/research/neuroconv-supported-routes.md](docs/research/neuroconv-supported-routes.md), assume NeuroConv should be investigated first and used whenever feasible
- Prefer category-first supported-adapter packaging when semantics are shared, including `behavior/`, `tabular/`, and `media/` families
- Treat logging, progress reporting, and user-facing runtime status as explicit cross-layer contracts, not incidental UI behavior
- Keep long-running conversions off the UI thread and route them through background workers, threads, or async-safe runtime services
- For the current desktop application direction, prefer one integrated main-window workspace over separate top-level dialogs or windows for routine workflows unless there is a strong technical reason
- Ensure UI-visible logs preserve timestamps from the originating logging event so internal-testing traces stay correlated across background work and user actions

## Documentation Rules

- Update [planning.md](planning.md) when architecture, scope, pathway definitions, or risks change
- Record material decisions in [decisions.md](decisions.md)
- Add deeper research or design notes under `docs/` instead of bloating top-level files
- Update [README.md](README.md) once at the end of each working session to reflect current state, major changes, usage, and next steps
- Do not update [README.md](README.md) on every commit

## Deviation Review Rule

- During internal testing, keep an explicit audit in [planning.md](planning.md) of meaningful plan-code deviations rather than smoothing them over in status summaries
- Do not present temporary shortcuts as settled architecture just because they are currently implemented
- If a shortcut materially affects startup UX, ingest grouping, metadata-override scope, source-role semantics, package layout, persistence model, or logging coverage, surface it and get a decision before expanding dependent behavior
- Prefer documenting the deviation and open decision clearly over implying the target product behavior already exists

## Safety Rule

- Do not invent unsupported scientific mappings silently
- If a mapping is uncertain, document the assumption and surface it for review
- Prefer explicit `needs review` states over confident but weak inference
- Do not represent custom lab concepts as standard NWB semantics unless the meaning is actually aligned
- If NeuroConv does not support a format, state that explicitly before implementing a direct PyNWB path
- If a representation would require an NWB extension, state that explicitly before implementing it
- Do not use `print` statements in actionable runtime paths; use structured logging instead
- Do not swallow exceptions silently; log context and surface a user-facing error path

## Testing and Validation Rule

- Add or update tests when behavior changes
- Add validation coverage for conversion-path changes where feasible
- Treat schema validation and best-practice inspection as part of the expected workflow, not optional cleanup
- If testing cannot be performed, state that clearly in commits, PR notes, or task summaries
- When runtime/event behavior changes, add tests for stage transitions, progress emission, or error propagation where feasible

## Definition of Done

### For planning tasks
- Relevant sections in [planning.md](planning.md) are updated
- Open questions and assumptions are captured
- Repo guidance remains consistent with the current plan

### For implementation tasks
- Code follows the layered architecture
- Tests and validation relevant to the change are added or updated
- Documentation is updated when contracts or behavior change
- Assumptions, limitations, and unresolved risks are recorded
- Work is committed on `dev` or a branch from `dev`

## Operating Guidance for Agents

- Start by checking repo instructions and plan documents
- When using Codex subagents for repository work, cap parallel execution at 3 concurrent subagents
- Use subagents only for independent tasks with isolated ownership and non-overlapping write scopes
- Merge subagent outputs deterministically and resolve failures sequentially instead of increasing concurrency
- Prefer primary-source documentation for NWB behavior and scientific format assumptions
- Favor reversible, incremental changes over broad speculative scaffolding
- When adding new adapters or mappings, define the contract first and implementation second
- For supported-path work, check the NeuroConv Conversion Gallery before proposing a manual converter
- For supported proprietary/acquisition routes, prefer thin NeuroConv execution wrappers over custom writer implementations
- For direct NWB writing, prefer documented PyNWB patterns for `NWBFile`, `Subject`, acquisitions, processing modules, stimuli, intervals, units, ophys, and ecephys containers
- Use [docs/research/neuroconv-supported-routes.md](docs/research/neuroconv-supported-routes.md) as the repo's approved NeuroConv-first route catalog
- Instrument actionable code paths with standard logging, not ad hoc printing
- Prefer runtime contracts that expose stage, progress, and error events cleanly to the future UI
- Prefer route-name package catalogs and grouped install targets over raw dependency prompts when designing setup or future UI package-install flows
- Prefer explicit `Save Project` / `Open Project` behavior over expanding JSON bootstrap fixtures when evolving direct-ingest desktop workflows
