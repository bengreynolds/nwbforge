# Package Management Baseline

Purpose: plan route-based package installation and optional-route availability.

Current baseline:
- The package catalog is route-name oriented and supports curated install presets
- Backend services handle package planning, installation, progress, and failure wrapping
- Optional routes are only registered when their required dependencies are installed

Constraints:
- Keep the UI thin and route-name oriented
- Reuse the same dependency catalog for setup and in-app installs
- Preserve explicit progress and error reporting for installs

Next step:
- Extend the catalog only as new route families are approved
