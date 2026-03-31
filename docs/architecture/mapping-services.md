# Mapping Planner Baseline

Last updated: 2026-03-31

## Purpose

This note captures the first concrete mapping-layer implementation.

## Implemented planner

### `RuleBasedMappingPlanner`

Location: `src/nwbforge/mapping/planners.py`

Responsibilities:
- turn normalized metadata into explicit `MappingDecision` entries
- surface blocking issues for missing required NWB-facing metadata
- preserve unmapped normalized fields as reviewable mapping decisions
- recommend manual review when identifier generation or unmatched metadata policy is still unsettled

## Current mapping scope

The first planner handles a conservative core:
- session description
- experiment description
- session start time
- session id
- NWB identifier seeding from session id
- experimenter, institution, lab, keywords
- subject id, species, sex, age, date of birth, description, genotype, strain
- device name, description, and manufacturer
- acquisition stream name, description, data, unit, and timing metadata
- behavior-stream targets through `BehavioralTimeSeries[behavior].TimeSeries[...]`
- unmatched additional metadata as `DESCRIBE` decisions

## Design constraints

- the planner emits decisions and issues only; it does not construct NWB objects
- target paths are explicit and reviewable
- missing required information becomes blocking issues, not silent defaults
- identifier policy remains visible as a review step instead of hidden logic

## Immediate follow-on work

1. Add modality-specific acquisition mapping beyond the current behavior baseline.
2. Introduce lab-profile-aware mapping templates.
3. Add explicit device-model policy rather than relying on temporary manufacturer bridging.
