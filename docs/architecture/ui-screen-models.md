# UI Screen Model Baseline

Purpose: keep desktop state in toolkit-agnostic models before binding to widgets.

Current baseline:
- Shell, package installer, conversion session, session assembly, and settings models exist
- The models bridge the runtime contracts to later widget layers
- Shared log and error presentation live behind the model layer

Constraints:
- Screen models should stay independent of the concrete widget toolkit
- Runtime truth should remain outside widget state
- Keep the models thin and explicit

Next step:
- Add more screen models only when a stable workflow needs one
