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

Run one or more focused smoke cases when you only need a specific workflow slice:

```text
conda run -n nwbforge-dev python scripts/run_internal_smoke.py --case supported
conda run -n nwbforge-dev python scripts/run_internal_smoke.py --case hybrid --case project
```

Write a machine-readable smoke summary for triage records:

```text
conda run -n nwbforge-dev python scripts/run_internal_smoke.py --report-json temp\smoke-report.json
```

What the smoke suite covers:
- checked-in supported session example through preview and NWB write
- checked-in custom session example through preview and NWB write
- checked-in hybrid session example through preview and NWB write
- direct-ingest project round-trip: ingest -> save project -> reload project -> preview -> write

## Internal-testing matrix

Run the local-app matrix in three layers and record findings from each layer separately.

### Layer 1: smoke baseline

Purpose:
- catch obvious regressions in the real desktop/backend stack before deeper manual testing

Required checks:
- supported fixture session smoke
- custom fixture session smoke
- hybrid fixture session smoke
- direct-ingest project round-trip smoke

Pass condition:
- all smoke cases complete preview and NWB write successfully

### Layer 2: focused workflow checks

Purpose:
- verify the current hardening targets without waiting for larger representative datasets

Required checks:
- direct-ingest grouping plus project save/load round trip
- metadata-review flow: preview -> override -> rebuild -> clear -> rebuild
- recovery flow: reopen or restore snapshot and verify diagnostics/readiness context
- multi-session conversion workspace tabs with project-aware context visible

Pass condition:
- each focused workflow can be completed without developer intervention and without ambiguous UI state

### Layer 3: representative local datasets

Purpose:
- verify that the current local app survives realistic operator scenarios instead of only checked-in fixtures

Required minimum:
- 3 representative local datasets
- at least 1 supported or supported-workflow dataset
- at least 1 custom or hybrid dataset
- at least 1 dataset that stresses mixed-source grouping or metadata disagreement review

Record for each dataset:
- dataset label or local shorthand
- pathway: supported / custom / hybrid
- major ingest characteristics
- result: pass / blocking issue / non-blocking issue
- blocking reason or notes

Pass condition:
- the dataset completes or fails in a diagnosable way with clear logs, diagnostics, and user-facing status

## Triage format

Record findings with these categories:
- `blocking`: prevents normal use of the intended workflow
- `non-blocking`: confusing or incorrect but does not stop the workflow
- `follow-up`: improvement idea discovered during testing, not yet a defect

Minimum triage fields:
- matrix layer
- case or dataset name
- observed behavior
- expected behavior
- category
- next action

Recommended attachment when available:
- JSON smoke summary from `scripts/run_internal_smoke.py --report-json ...`

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
