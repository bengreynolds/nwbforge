# Normalization Service Baseline

Purpose: turn source-specific fields into canonical internal metadata with reviewable ambiguity.

Current baseline:
- `RuleBasedNormalizationService` is the baseline implementation
- Alias-driven rules populate the canonical models
- Unknown or conflicting values stay visible for review instead of being hidden

Constraints:
- Normalization stays separate from parsing and NWB assembly
- The service should preserve origin and review status
- Broad ontology inference remains out of scope until a stronger contract is needed

Next step:
- Add lab-profile-specific rules only when the baseline stops being enough
