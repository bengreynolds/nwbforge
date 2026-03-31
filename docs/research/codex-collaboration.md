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

## Why this matters here

This project will likely involve repeated agent work across planning, adapters, metadata contracts, validation, and UI slices. Without stable repository instructions, contributors will drift toward one-off conversion logic and undocumented scientific assumptions.

## Source

- OpenAI Codex guide, `Custom instructions with AGENTS.md`: https://developers.openai.com/codex/guides/agents-md
