# AGENTS.md

## Role Definition

Contributors and coding agents in this repository act as senior scientific software and data-platform engineers building a maintainable NWB conversion platform for heterogeneous laboratory data.

Primary priorities:
- Protect scientific interpretability
- Preserve modular architecture boundaries
- Prefer durable contracts over quick one-off scripts
- Document assumptions, especially for custom mappings

## Branch Policy

- Work on `dev` or a short-lived feature branch created from `dev`
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
- If scope, architecture, or sequencing changes, update [planning.md](planning.md) in the same branch
- Do not begin substantial implementation until the affected plan sections exist and are current

## Change-Size Rule

- Prefer small, reviewable changes with clear intent
- Keep early milestones narrow: contracts, scaffolding, and representative slices before broad feature work
- Avoid mixing architecture refactors with new feature behavior unless necessary

## Commit Policy

- Commit frequently with meaningful, scoped messages
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

## Documentation Rules

- Update [planning.md](planning.md) when architecture, scope, pathway definitions, or risks change
- Record material decisions in [docs/decision-log.md](docs/decision-log.md)
- Add deeper research or design notes under `docs/` instead of bloating top-level files
- Keep README concise and accurate

## Safety Rule

- Do not invent unsupported scientific mappings silently
- If a mapping is uncertain, document the assumption and surface it for review
- Prefer explicit `needs review` states over confident but weak inference
- Do not represent custom lab concepts as standard NWB semantics unless the meaning is actually aligned

## Testing and Validation Rule

- Add or update tests when behavior changes
- Add validation coverage for conversion-path changes where feasible
- Treat schema validation and best-practice inspection as part of the expected workflow, not optional cleanup
- If testing cannot be performed, state that clearly in commits, PR notes, or task summaries

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
- Prefer primary-source documentation for NWB behavior and scientific format assumptions
- Favor reversible, incremental changes over broad speculative scaffolding
- When adding new adapters or mappings, define the contract first and implementation second
