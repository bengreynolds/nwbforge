# Mapping Planner Baseline

Purpose: express how normalized metadata should populate NWB structures before any file is written.

Current baseline:
- `RuleBasedMappingPlanner` emits reviewable mapping decisions
- Required-field gaps surface as explicit issues
- Identifier generation and other transforms stay visible in the plan

Constraints:
- The planner should not perform direct NWB construction
- Mapping should depend on normalized models, not raw parser output
- Ambiguous cases should remain reviewable

Next step:
- Expand only through stable normalized contracts and documented container choices
