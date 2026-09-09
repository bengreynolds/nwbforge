# Validation Service Baseline

Purpose: validate generated artifacts and turn validation results into reviewable workflow state.

Current baseline:
- Artifact checks verify that expected outputs exist and are readable
- PyNWB schema validation and NWB Inspector checks are layered separately
- Validation reports and review-policy outcomes are persisted as artifacts

Constraints:
- Validation should stay separate from report generation
- Schema validity and best-practice checks are different concerns
- Blocking, review, and pass states must remain explicit

Next step:
- Add only the validation checks needed to protect the current desktop workflow
