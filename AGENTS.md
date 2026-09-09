# AGENTS.md

## Role
Contributors and coding agents act as senior scientific software and data-platform engineers for a maintainable NWB conversion platform.

Priorities:
- Protect scientific interpretability
- Preserve modular architecture boundaries
- Prefer durable contracts over quick one-off scripts
- Document assumptions, especially for custom mappings

## Branch and PR Rules
- Work on `dev` or a short-lived branch created from `dev`
- Never commit directly to `main`
- Stop and switch if the current branch is `main`
- Use pull requests for meaningful milestones
- PR summaries should call out architecture impact, assumptions, and validation status

## Planning First
- Read [planning.md](planning.md) before implementation
- Keep [AGENTS.md](AGENTS.md), [planning.md](planning.md), and [decisions.md](decisions.md) current
- Update `planning.md` when scope, sequencing, architecture, or risks change
- Do not start substantial implementation until the relevant plan sections exist
- Do not begin release, installer, updater, or distribution work before the plan is updated

## Architecture Boundaries
- Keep UI/workflow orchestration, source adapters, normalization, NWB mapping/assembly, and validation/provenance separate
- Source adapters must not write NWB directly
- Normalize metadata before NWB mapping
- Treat supported, custom, and hybrid pathways as shared-contract workflows
- Prefer real file/folder ingest over hand-authored session JSON as the primary UX
- Treat app-owned session/project files as saved internal state, not scientific source of truth
- For supported routes, check NeuroConv first and use documented NeuroConv APIs when available
- For custom assembly, use documented PyNWB patterns
- Treat logging, progress, and user-facing runtime status as cross-layer contracts
- Keep long-running work off the UI thread

## Environment and Testing
- Use the Conda environment defined in [environment.yml](environment.yml) for installs and tests
- Do not rely on user-site packages
- Release artifacts must be self-contained
- Add or update tests for behavior changes and runtime event changes
- Do not use `print` in actionable runtime paths
- Log failures with context and do not swallow exceptions silently

## Change Size and Commits
- Prefer small, reviewable changes
- Commit frequently with scoped messages
- Separate docs and implementation changes when practical
- Do not batch unrelated work just to shorten history
- Do not amend commits unless explicitly requested

## Documentation
- Record material decisions in [decisions.md](decisions.md)
- Keep deeper research under `docs/`
- Update [README.md](README.md) at the end of a working session, not every commit

## Agent Workflow
- Cap Codex subagents at 3 concurrent workers
- Use subagents only for independent tasks with isolated ownership and non-overlapping write scopes
- Merge subagent results deterministically and resolve conflicts sequentially

## Definition of Done
- Relevant plan sections are updated
- Tests and validation are updated where applicable
- Assumptions and unresolved risks are recorded
- Work is committed on `dev` or a branch from `dev`
