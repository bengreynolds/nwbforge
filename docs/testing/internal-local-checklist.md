# Internal Local Testing Checklist

Last updated: 2026-04-01

## Purpose

This checklist defines the current local-only internal testing baseline before deployment work begins.

## Automated baseline

Run the full suite in the dedicated Conda environment:

```text
powershell -ExecutionPolicy Bypass -File scripts/test-conda-dev.ps1
```

Run the focused desktop/backend smoke suite:

```text
conda run -n nwbforge-dev python scripts/run_internal_smoke.py
```

What the smoke suite covers:
- checked-in supported session example through preview and NWB write
- checked-in custom session example through preview and NWB write
- checked-in hybrid session example through preview and NWB write
- direct-ingest project round-trip: ingest -> save project -> reload project -> preview -> write

## Manual desktop baseline

Launch the local app:

```text
conda run -n nwbforge-dev python scripts/run_app.py
```

Launch with explicit test fixtures when needed:

```text
conda run -n nwbforge-dev python scripts/run_app.py --session examples\sessions\supported\session_manifest.json
conda run -n nwbforge-dev python scripts/run_app.py --session examples\sessions\custom\custom_session.json
conda run -n nwbforge-dev python scripts/run_app.py --session examples\sessions\hybrid\hybrid_session.json
conda run -n nwbforge-dev python scripts/run_app.py --project path\to\saved-project.nwbforge-project.json
```

## Manual checks

1. Start from `New Session`.
2. Add a supported file, a custom file, or both.
3. Review heuristic grouping and correct at least one group label when appropriate.
4. Apply at least one session-wide metadata override.
5. Apply at least one source-specific metadata override.
6. Save the direct-ingest workspace as a project.
7. Reopen that project and confirm paths, grouping, and overrides are restored.
8. Create the conversion session and run `Build Preview`.
9. Run `Write NWB` and confirm output, validation report, and review artifacts appear.
10. Use artifact open/reveal actions and confirm failures surface cleanly when a file is missing.
11. Close and reopen the desktop workflow and confirm latest-state recovery is visible.
12. Check `Settings`, `Open Recent`, `Open Recent Project`, and the log viewer.

## Known warnings

- NeuroConv DeepLabCut fixture warning: metadata not found
- PyNWB `manufacturer` deprecation warning for devices

These are currently known and do not block the internal local-app baseline.
