# Normalization Service Baseline

Last updated: 2026-03-31

## Purpose

This note captures the first concrete normalization-layer implementation.

## Implemented service

### `RuleBasedNormalizationService`

Location: `src/nwbforge/normalization/services.py`

Responsibilities:
- normalize a conservative set of subject and session metadata fields from `ExtractionResult`
- normalize first-pass device metadata from extracted device records
- apply declarative aliases from `NormalizationRuleSet`
- preserve unmatched fields in `additional_metadata`
- mark unknown and conflicting values for human review instead of silently dropping them
- fall back to the conversion session id when no source session id is present

## Rule scope

The initial rule set is intentionally narrow. It currently covers:
- subject id, species, sex, age, date of birth, description, genotype, strain
- session id, description, experiment description, start time, experimenter, institution, lab, keywords
- device id, name, description, manufacturer, modality for manifest-backed device records

This is enough to exercise the normalization boundary without inventing broad ontology behavior too early.

## Design constraints

- normalization remains independent of NWB-specific target structures
- aliases are declarative and replaceable
- ambiguous mappings surface as reviewable state rather than hidden heuristics
- unmatched fields are preserved for later mapping and review

## Immediate follow-on work

1. Add lab-profile overrides on top of the base alias rules.
2. Add acquisition-stream normalization on top of the current device baseline.
3. Introduce richer device-model policy, including how deprecated manufacturer handling should evolve.
