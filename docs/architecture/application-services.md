# Application Service Baseline

Purpose: hold the thin application-layer services that connect adapters, domain models, and UI-facing orchestration.

Current baseline:
- Source inspection and provenance services bridge adapters to normalized models
- Session assembly builds draft conversion sessions from direct ingest
- Package-management services and controllers support route-based installs
- Local file preview and NWB file controllers support read-only inspection flows

Constraints:
- Services should stay protocol-driven and narrow
- UI code should not own domain truth
- Application services should not embed parser logic or direct file-writing policy

Next step:
- Add new services only when a stable application boundary is missing
