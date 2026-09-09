# Internal Local Testing Checklist

Purpose: define the current local-only smoke and manual testing baseline.

Automated baseline:
```text
powershell -ExecutionPolicy Bypass -File scripts/test-conda-dev.ps1
conda run -n nwbforge-dev python scripts/run_internal_smoke.py
```

Smoke coverage:
- supported fixture session preview and write
- custom fixture session preview and write
- hybrid fixture session preview and write
- direct-ingest project round trip

Manual baseline:
1. Start from `New Session`
2. Add supported and/or custom sources
3. Review grouping and metadata overrides
4. Save and reopen a direct-ingest project
5. Build preview, write NWB, and inspect generated artifacts
6. Confirm recovery, recent items, settings, and the log viewer

Known warnings:
- DeepLabCut fixture metadata may be missing
- PyNWB `manufacturer` deprecation warnings may appear for devices
