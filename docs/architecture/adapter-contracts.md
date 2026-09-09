# Adapter and Service Contract Baseline

Purpose: define the boundary between source extraction, orchestration, and canonical domain models.

Current baseline:
- Extraction models represent adapter output before normalization
- Adapter contracts and registries keep discovery explicit
- Shared NeuroConv interface adapters and workflow adapters cover the supported-route framework
- Service protocols define inspection, normalization, mapping, validation, and provenance boundaries

Constraints:
- Most adapters remain extraction-only
- Direct-conversion supported adapters are the exception and delegate final writing to documented NeuroConv APIs
- Registry logic should stay small and deterministic

Next step:
- Add new adapter families only when they fit the shared contract shape
