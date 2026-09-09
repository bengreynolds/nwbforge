# Core Contract Baseline

Purpose: stable domain models for sessions, sources, normalization, mapping, provenance, and validation.

Current baseline:
- Session and source references model the workflow container and raw inputs
- Normalized metadata carries origin and review status
- Mapping and validation models keep reviewable decisions explicit

Constraints:
- Domain models stay independent of UI, adapters, and PyNWB
- Source parsing details do not leak into normalization or mapping
- Keep the models small and immutable

Next step:
- Extend only when a new orchestration or persistence need requires a stable contract
