# Orchestration Service Baseline

Purpose: coordinate preview and execution flow across inspection, normalization, mapping, assembly, and validation.

Current baseline:
- `ConversionPipelineService` builds previews and evaluates outputs
- Runtime stages are explicit rather than hidden inside one opaque run call
- Preview and execution remain separate orchestration concerns

Constraints:
- Orchestration should expose stage and progress events
- Long-running work belongs off the UI thread
- Preview state and execution state should stay distinguishable

Next step:
- Expand orchestration only when a new stage boundary is required
