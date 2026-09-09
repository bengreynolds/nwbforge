# Assembly Service Baseline

Purpose: write normalized models into NWB using documented PyNWB patterns.

Current baseline:
- `PyNWBAssemblyService` is the current writer baseline
- The service starts with the core subject/session fields and grows in narrow slices
- Custom and hybrid paths can use standard PyNWB containers when the semantics fit

Constraints:
- Follow official PyNWB docs for container placement and file-writing patterns
- Do not invent parallel abstractions when `pynwb.file` or another standard module suffices
- Keep unsupported or uncertain semantics reviewable

Next step:
- Add modality-specific assembly only when the semantics are clear and documented
