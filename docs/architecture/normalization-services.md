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
- normalize first-pass acquisition-stream metadata from extracted stream records
- normalize first-pass time-interval tables and interval rows from NeuroConv-backed text/tabular extraction
- apply declarative aliases from `NormalizationRuleSet`
- preserve unmatched fields in `additional_metadata`
- mark unknown and conflicting values for human review instead of silently dropping them
- fall back to the conversion session id when no source session id is present

## Rule scope

The initial rule set is intentionally narrow. It currently covers:
- subject id, species, sex, age, date of birth, description, genotype, strain
- session id, description, experiment description, start time, experimenter, institution, lab, keywords
- device id, name, description, manufacturer, modality for manifest-backed device records
- acquisition stream id, name, modality, description, and writer-facing metadata such as data, unit, rate, and timestamps for manifest-backed stream records
- interval-table name, description, row timing, and per-row metadata for CSV and Excel trial sources

This is enough to exercise the normalization boundary without inventing broad ontology behavior too early.

## Design constraints

- normalization remains independent of NWB-specific target structures
- aliases are declarative and replaceable
- ambiguous mappings surface as reviewable state rather than hidden heuristics
- unmatched fields are preserved for later mapping and review

## Immediate follow-on work

1. Add lab-profile overrides on top of the base alias rules.
2. Introduce richer stream normalization for external/binary payloads instead of only inline manifest data.
3. Introduce richer interval-table policy for epochs or custom `TimeIntervals` targets beyond the current trials baseline.
