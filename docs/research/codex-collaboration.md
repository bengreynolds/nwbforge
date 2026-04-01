# Codex Collaboration Notes

Research date: 2026-03-31

## Summary

For long-lived agent collaboration, the most important repository practice is to make project instructions persistent, local to the repository, and easy to discover before work begins. Official Codex guidance centers this on `AGENTS.md`.

## Practical takeaways

- Keep repository-level instructions in `AGENTS.md`
- Put durable project expectations in the repo root so new agent runs pick them up automatically
- Keep specialized overrides close to specialized subdirectories if the repo later needs them
- Keep instructions concise enough to remain within Codex instruction loading limits
- Use PR-based workflows so architecture and assumption changes are reviewed explicitly
- When parallel Codex subagents are useful, cap concurrent work at 3 and keep write scopes isolated
- Merge subagent results deterministically and prefer sequential fallback when one branch fails or conflicts

## Parallel subagent guidance

For this repository, bounded Codex subagent use is a development workflow convenience, not a product feature. The important guardrails are:
- maximum 3 concurrent subagents
- independent subtasks with isolated ownership
- deterministic integration after the subagent work returns
- sequential local handling when a subagent result is ambiguous or conflicting

## Why this matters here

This project will likely involve repeated agent work across planning, adapters, metadata contracts, validation, and UI slices. Without stable repository instructions, contributors will drift toward one-off conversion logic and undocumented scientific assumptions.

## Source

- OpenAI Codex guide, `Custom instructions with AGENTS.md`: https://developers.openai.com/codex/guides/agents-md
