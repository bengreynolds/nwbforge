# UI Runtime And Observability Baseline

Purpose: define the runtime contracts for background work, logging, progress, and user-facing errors.

Current baseline:
- Conversion and install work run off the UI thread
- Stage, progress, and error events are explicit
- Standard logging carries context into the UI-visible log stream
- Error presentation stays concise in the UI while logs keep the detail

Constraints:
- UI code should render runtime state, not own it
- Logging should preserve the original event timestamp
- Silent failures are not acceptable

Next step:
- Expand coverage only when a new runtime path needs the same contract
