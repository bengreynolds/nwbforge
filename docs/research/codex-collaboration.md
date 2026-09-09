# Codex Collaboration Notes

Research date: 2026-03-31

Keep persistent repository instructions in `AGENTS.md`, keep them concise, and use PR-based review for architecture changes.

Subagent guardrails:
- Maximum 3 concurrent subagents
- Independent tasks only
- Non-overlapping write scopes
- Deterministic merge after the subagent work returns

Source:
- OpenAI Codex guide: https://developers.openai.com/codex/guides/agents-md
