# NWB Forge Planning

Last updated: 2026-03-31
Status: Phase 1 planning

## Project Vision and Scope

Build a UI-driven conversion platform that helps labs transform heterogeneous acquisition outputs into understandable, validated NWB files. The system must scale from straightforward supported conversions to complex assisted conversions that combine proprietary and custom data streams while preserving provenance, interpretability, and maintainability.

In scope for the product:
- Guided conversion workflows for multiple lab archetypes
- Clear distinction between supported, custom, and hybrid conversion pathways
- Plugin-style source adapters for lab- or system-specific inputs
- Metadata normalization before NWB assembly
- NWB assembly using the appropriate level of abstraction
- Validation, provenance capture, and human-readable conversion summaries
- User review steps for ambiguous mappings

Out of scope for the first phases:
- Fully automated interpretation of arbitrary proprietary formats without adapter work
- A universal ontology that solves all departmental metadata inconsistencies at once
- Direct replacement of all existing lab-side preprocessing pipelines
- Enterprise-scale workflow orchestration before core conversion contracts stabilize

## Assumptions and Unknowns

### Assumptions
- The department has repeated conversion needs across roughly 20 labs with partial overlap in metadata and acquisition patterns.
- Some labs already fit existing NWB ecosystem tools with modest configuration.
- Other labs will require custom adapters, manual metadata review, and hybrid composition.
- Researchers need a UI because conversion cannot rely on Python literacy alone.
- NWB output quality matters as much as file creation success.
- Long-term maintainability is better served by explicit contracts and modular boundaries than by one-off scripts.

### Unknowns
- Which acquisition systems are most common across the department
- How much metadata currently lives in files versus notebooks, spreadsheets, or operator memory
- Whether labs need local desktop execution, shared server execution, or both
- What minimum review and approval workflow is required before writing final NWB files
- Which lab-specific concepts should remain descriptive metadata versus formal extensions
- How much dataset merging is needed across clocks, modalities, and file families

## NWB Ecosystem Research Summary

### What NWB is intended to standardize
NWB standardizes neurophysiology data together with the metadata needed to interpret it. The standard is designed so experimental data, subject/session metadata, device context, and modality-specific structures can live in one navigable file layout rather than scattered across ad hoc lab formats.

Academic adoption goals typically include:
- Improving data sharing and reuse across labs and repositories
- Making multimodal experiments easier to analyze together
- Preserving experimental context and provenance
- Reducing bespoke format handling in downstream analysis
- Supporting archive deposition workflows such as DANDI

### Where NWB GUIDE fits
NWB GUIDE is the strongest reference point for straightforward, user-facing conversions. It is a desktop application that walks researchers through common conversion requirements and DANDI-oriented workflows. In this repository, GUIDE should be treated as the benchmark for the supported pathway UX, not as the full solution for unsupported or hybrid cases.

### Where NeuroConv fits
NeuroConv is the primary supported-path backend for known acquisition formats. It provides data interfaces and automated conversion patterns for many source systems. In this project, NeuroConv should be the default engine behind supported adapters and the first thing evaluated before writing custom ingest logic.

### Where PyNWB fits
PyNWB is the lower-level construction layer for reading, writing, validating, and customizing NWB files. It is the escape hatch for unsupported formats, hybrid assembly, and advanced cases where the system must construct or augment NWB structures directly.

### How custom data and metadata are typically represented
The NWB stack supports several levels of customization:
- Descriptive metadata placed into existing NWB fields when semantics match
- Lab-specific metadata through `LabMetaData` patterns
- Additional tabular fields where schema supports custom columns
- Neurodata Extensions (NDX) when truly new data types or structured metadata are required

Planning implication: the product should not jump straight to extensions for every mismatch. It should guide users through a decision ladder:
1. Map to existing NWB fields when semantics are clear.
2. Use descriptive metadata or supported custom fields when the concept is local but not novel.
3. Use NDX only when the data model itself needs a durable extension.

### Validation and review
Validation in the NWB ecosystem is layered:
- PyNWB validation checks schema compliance
- NWB Inspector checks best-practice issues and likely conversion mistakes
- Manual inspection remains necessary for scientific correctness and usability

Planning implication: validation must be a dedicated layer with machine checks and human review artifacts.

## Department-Wide Requirements and Constraints

### Functional requirements
- Support repeated use across many labs without per-project rewrites
- Accommodate single-format and multi-input conversion sessions
- Support partial automation with explicit human review gates
- Produce NWB outputs that are understandable to downstream researchers
- Persist conversion configuration, decisions, assumptions, and provenance

### Non-functional requirements
- Modular codebase with stable internal contracts
- Strong traceability from input fields to output NWB structures
- Safe handling of unsupported or ambiguous mappings
- Extensible plugin model for new labs and formats
- Testable backend components independent of UI

### Organizational constraints
- Lab conventions will differ in naming, metadata completeness, and file layout
- Some formats may be legally or practically opaque
- Adoption depends on low-friction workflows for non-programmer users
- Department-wide governance will likely lag behind implementation, so local assumptions must be documented explicitly

## User Personas and Lab Archetypes

### Persona 1: Supported-path lab
Uses a common acquisition system already handled well by NeuroConv or GUIDE. Needs a fast UI workflow, metadata entry help, validation, and export.

### Persona 2: Semi-structured custom lab
Uses a mix of common files plus spreadsheets, JSON sidecars, or naming conventions. Needs file inspection, mapping assistance, and repeatable lab templates.

### Persona 3: Hybrid multimodal lab
Needs to combine proprietary acquisition output, derived signals, annotations, and custom metadata into one coherent NWB file. Needs staged review, provenance visibility, and explicit merge semantics.

### Persona 4: Platform maintainer
Adds adapters, normalization rules, and lab profiles. Needs stable contracts, tests, traceability, and a clear place to encode assumptions.

## Data Source Taxonomy

### By format support status
- Known supported formats with mature ecosystem tooling
- Partially supported formats requiring additional metadata or restructuring
- Unsupported proprietary formats requiring custom parsers
- Unsupported custom lab formats requiring bespoke adapters

### By data organization style
- Single recording file plus sidecar metadata
- Session folder with multiple modality files
- Multi-run experiment with separate acquisitions and derived outputs
- Mixed raw data plus spreadsheets or notebooks for annotations

### By metadata quality
- Rich embedded metadata
- Sparse metadata with recoverable conventions
- Fragmented metadata across files and human-entered records
- Ambiguous metadata requiring explicit user interpretation

## Conversion Pathway Taxonomy

### Supported pathway
Use existing ecosystem support with minimal custom logic.

Characteristics:
- Recognized source format
- Metadata model maps cleanly to NWB
- Conversion can mostly be expressed through NeuroConv and standard metadata entry

Expected system behavior:
- Guided format detection
- Pre-filled metadata forms
- Standard validation and summary

### Custom mapping pathway
Use custom adapter and explicit mapping logic.

Characteristics:
- Unsupported format or schema
- Non-standard metadata organization
- Need for manual field interpretation or local heuristics

Expected system behavior:
- Source inspection workflow
- Field-level mapping UI
- Persistent mapping configuration and review notes

### Hybrid pathway
Combine supported and custom components into one NWB file.

Characteristics:
- Multiple inputs from different systems
- Some components handled by NeuroConv, others custom
- Need to merge timelines, metadata, provenance, and descriptions

Expected system behavior:
- Multi-input session model
- Merge plan preview
- Unified validation and provenance report

## Proposed System Architecture

The architecture should preserve explicit layers and avoid format-specific logic leaking into UI or NWB assembly code.

### Layer 1: UI frontend
Responsibilities:
- Session creation
- File selection and source inspection views
- Metadata entry and review
- Mapping preview
- Validation and conversion reporting

Preferred design direction:
- Build a workflow-oriented UI, not a generic form dump
- Model conversion as stages with checkpoints
- Preserve transparency around automatic versus manual decisions

### Layer 2: Orchestration and application services
Responsibilities:
- Manage conversion sessions
- Route sessions into supported, custom, or hybrid flows
- Coordinate adapters, normalization, assembly, validation, and reporting
- Persist intermediate state and decisions

Key rule:
- Orchestration knows process state, but not format-specific parsing details

### Layer 3: Adapter and plugin layer
Responsibilities:
- Detect source systems
- Read raw files and sidecar metadata
- Expose canonical extracted records to the rest of the system

Key rule:
- Adapters translate source-specific structures into internal extraction models
- Adapters never write NWB directly

### Layer 4: Metadata normalization layer
Responsibilities:
- Normalize field names, units, identifiers, subject/session concepts, and controlled vocabularies
- Merge metadata from files, profiles, and user edits
- Track confidence, source, and override history

Key rule:
- Normalization creates internal canonical models that are independent of both raw source naming and final NWB serialization

### Layer 5: NWB mapping and assembly layer
Responsibilities:
- Map normalized models into NWB structures
- Choose between standard mappings, descriptive metadata, and extension points
- Compose hybrid outputs from multiple extracted streams

Key rule:
- This is the only layer allowed to construct NWB containers

### Layer 6: Validation, provenance, and reporting layer
Responsibilities:
- Run PyNWB validation
- Run NWB Inspector
- Build human-readable reports describing mappings, assumptions, warnings, and unresolved items

Key rule:
- Validation outcomes should inform UI review and export readiness, not just logs

## Backend Module Layout

Recommended Python package layout for implementation:

```text
src/nwbforge/
  app/
    sessions/
    services/
    workflows/
  domain/
    models/
    contracts/
    enums/
  adapters/
    base/
    registry/
    supported/
    custom/
  normalization/
    schemas/
    rules/
    resolvers/
  mapping/
    planners/
    transformers/
    assemblers/
  validation/
    schema/
    inspector/
    reports/
  provenance/
    models/
    emitters/
  lab_profiles/
  persistence/
  cli/
```

Rationale:
- `domain/` keeps canonical models and contracts stable
- `adapters/` isolates source-specific logic
- `normalization/` prevents direct source-to-NWB coupling
- `mapping/` handles assembly and merge planning
- `validation/` and `provenance/` remain explicit first-class concerns

## UI and Workflow Design

Recommended first-pass workflow:
1. Create conversion session
2. Add one or more input sources
3. Detect likely format and pathway
4. Inspect extracted structure and metadata coverage
5. Apply lab profile or mapping template if available
6. Review normalized metadata
7. Review planned NWB mapping and hybrid merge decisions
8. Run validation precheck
9. Write NWB
10. Review final report and export artifacts

Critical UX principles:
- Always show what was inferred versus explicitly supplied
- Surface missing required metadata early
- Let users preview NWB organization before final write
- Support draft sessions and re-runs

## Metadata Normalization Strategy

Normalization should be a dedicated internal contract, not an incidental helper.

Core ideas:
- Canonical internal models for subject, session, device, acquisition stream, timing, and annotations
- Field provenance on each normalized value
- Confidence and ambiguity markers for inferred mappings
- Rule-based normalization first, with room for future assisted suggestions
- Lab profiles that provide defaults, aliases, unit conventions, and required-field policies

Normalization outputs should answer:
- What concept does this source field represent?
- What source produced it?
- Was it inferred, defaulted, user-supplied, or adapter-extracted?
- Is it ready to map into NWB, or does it still require review?

## Provenance and Validation Strategy

Provenance requirements:
- Capture input file list, hashes if feasible, adapter versions, lab profile used, and user overrides
- Record pathway used: supported, custom, or hybrid
- Preserve mapping decisions and unresolved warnings
- Produce a human-readable conversion summary alongside machine-readable records

Validation requirements:
- Run schema validation with PyNWB before completion
- Run NWB Inspector for best-practice review
- Separate blocking errors from advisory warnings
- Persist validation outputs in session artifacts

Recommended report sections:
- Inputs
- Detected sources and adapters
- Metadata sources and overrides
- NWB mapping summary
- Validation results
- Manual review notes
- Known limitations and assumptions

## Plugin and Adapter Strategy for Lab-Specific Formats

Design goals:
- Add new source support without touching orchestration internals
- Distinguish core adapters from department-specific plugins
- Support lab profiles separately from source adapters

Recommended concepts:
- Adapter manifest with id, version, supported patterns, and capability flags
- Registry-based discovery for supported adapters
- Plugin package contract for lab-specific parsers and mapping presets
- Lab profile package for naming conventions, metadata aliases, defaults, and review policies

Important separation:
- Source adapter: how to parse a format or folder structure
- Lab profile: how a specific lab uses or names concepts
- Mapping template: how normalized concepts should populate NWB for a repeated experiment style

## Risk Register

### High risks
- Underestimating metadata fragmentation across labs
- Treating unsupported formats as a parser problem when they are really a semantics problem
- Leaking source-specific assumptions into core NWB assembly code
- Writing opaque NWB outputs that validate but are difficult to interpret

### Medium risks
- UI becoming a thin wrapper around backend exceptions
- Early plugin API churn causing adapter rewrites
- Unclear ownership of department-wide vocabulary normalization
- Hybrid merge logic becoming tightly coupled to a few early labs

### Mitigations
- Keep canonical domain models separate from source and NWB models
- Make provenance and review visible from the start
- Pilot with multiple lab archetypes before freezing contracts
- Record assumptions and unresolved mappings in decision logs and reports

## Phased Implementation Roadmap

### Phase 1: Research and planning
- Document ecosystem, architecture, risks, and open questions
- Establish repo conventions and agent operating rules
- Define module boundaries and workflow concepts

### Phase 2: Core backend contracts
- Create canonical domain models
- Define adapter interfaces, registry contracts, and session models
- Define normalization and mapping contracts
- Add validation and provenance service interfaces

### Phase 3: Supported-path MVP
- Implement one end-to-end supported workflow using NeuroConv-backed adapters
- Provide minimal UI or CLI workflow to prove session orchestration
- Produce validation and summary artifacts

### Phase 4: Custom-path MVP
- Implement source inspection workflow
- Support manual metadata mapping and persistent templates
- Write custom-path NWB assembly with explicit review gates

### Phase 5: Hybrid-path MVP
- Support multi-input conversion sessions
- Implement merge planning and combined provenance reporting
- Validate merged outputs with representative datasets

### Phase 6: Department rollout
- Add lab profiles
- Harden plugin contracts
- Expand adapter coverage
- Add onboarding docs, sample datasets, and governance guidance

## Open Questions

- Which 3 to 5 lab pipelines should define the initial architecture tests?
- Do we need a desktop-first UI, browser-first UI, or both?
- Where should session state live for early deployments: local files, SQLite, or service-backed storage?
- What minimum provenance record is required for auditability?
- When should the system recommend descriptive metadata versus a formal NDX?
- How should lab vocabularies be versioned and reviewed?
- Which validation findings should block export by default?

## Decisions Log

This file is the high-level planning document. Decision details and reversals should be recorded in [docs/decision-log.md](docs/decision-log.md).

Initial decisions:
- Use a layered architecture with explicit normalization and provenance layers.
- Treat supported, custom, and hybrid conversions as first-class pathways.
- Prefer NeuroConv first for supported ingestion, PyNWB for custom assembly, and NWB GUIDE as a UX reference for straightforward conversions.
- Avoid promising universal automatic conversion intelligence in early phases.

## Research References

- NWB Overview: https://nwb-overview.readthedocs.io/en/latest/
- Converting neurophysiology data to NWB: https://nwb-overview.readthedocs.io/en/latest/conversion_tutorial/user_guide.html
- NWB GUIDE docs: https://nwb-guide.readthedocs.io/en/latest/
- NeuroConv docs: https://neuroconv.readthedocs.io/en/stable/
- PyNWB docs: https://pynwb.readthedocs.io/en/stable/
- NWB Inspector docs: https://nwbinspector.readthedocs.io/
- OpenAI Codex AGENTS.md guide: https://developers.openai.com/codex/guides/agents-md
