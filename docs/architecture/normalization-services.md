# Normalization Service Baseline

Last updated: 2026-03-31

## Purpose

This note captures the first concrete normalization-layer implementation.

## Implemented service

### `RuleBasedNormalizationService`

Location: `src/nwbforge/normalization/services.py`

Responsibilities:
- normalize a conservative set of subject and session metadata fields from `ExtractionResult`
- apply declarative aliases from `NormalizationRuleSet`
- preserve unmatched fields in `additional_metadata`
- mark unknown and conflicting values for human review instead of silently dropping them
- fall back to the conversion session id when no source session id is present

## Rule scope

The initial rule set is intentionally narrow. It currently covers:
- subject id, species, sex, age, genotype, strain
- session id, description, start time, experimenter, institution, lab, keywords

This is enough to exercise the normalization boundary without inventing broad ontology behavior too early.

## Design constraints

- normalization remains independent of NWB-specific target structures
- aliases are declarative and replaceable
- ambiguous mappings surface as reviewable state rather than hidden heuristics
- unmatched fields are preserved for later mapping and review

## Immediate follow-on work

1. Add lab-profile overrides on top of the base alias rules.
2. Add normalization for devices and acquisition streams.
3. Add a mapping-planner implementation that consumes the normalized bundle.
