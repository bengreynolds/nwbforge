# Session Persistence Baseline

Purpose: persist session state so desktop workflows can reopen, recover, and restore previous work.

Current baseline:
- JSON snapshots store the latest session state
- Bounded history preserves recent recovery points
- The desktop shell can reopen or restore saved session states

Constraints:
- Keep the latest snapshot path stable
- Preserve review and artifact state with the session
- Do not replace the snapshot model with a richer store until the need is clear

Next step:
- Add richer persistence only when the current snapshot model becomes a bottleneck
