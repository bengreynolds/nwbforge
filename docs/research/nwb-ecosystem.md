# NWB Ecosystem Research

Research date: 2026-03-31

## Summary

The current NWB ecosystem already provides a strong split between:
- user-friendly supported conversion workflows
- reusable conversion interfaces for known formats
- low-level APIs and extension mechanisms for custom cases
- separate validation tools for structural and best-practice review

That split maps well onto this repository's planned supported, custom, and hybrid pathways.

## Tool roles

### NWB
NWB is the target data standard for packaging neurophysiology data with the metadata needed to interpret it. The standard is designed to support consistent storage, reading, sharing, and downstream analysis.

### NWB GUIDE
NWB GUIDE is a desktop application for guided conversion and DANDI-oriented workflows. It is best treated as the ecosystem reference for straightforward conversion UX and metadata-entry guidance.

### NeuroConv
NeuroConv provides reusable interfaces for converting many common acquisition formats into NWB. It is the strongest default backend candidate for supported-path conversions.

Current planning guidance:
- start with the NeuroConv Conversion Gallery when evaluating whether a supported-path format already has an interface
- prefer documented NeuroConv interfaces and combined workflows before designing a low-level converter
- treat direct PyNWB writing as the fallback for unsupported or unusually custom datasets
- use [neuroconv-supported-routes.md](neuroconv-supported-routes.md) as the repository's approved NeuroConv-first route catalog

### PyNWB
PyNWB is the lower-level Python API for creating, reading, validating, and extending NWB files. It is the foundation for custom assembly and cases that need more control than standard conversion interfaces provide.

Current planning guidance:
- use official PyNWB docs as the source of truth for API usage and container placement
- prefer the simplest documented high-level container available, especially in `pynwb.file` and the standard domain modules

### NWB Inspector
NWB Inspector complements schema validation by checking for best-practice issues and likely conversion mistakes that may still pass formal validation.

## Implications for this project

- Reuse NeuroConv wherever format support is mature enough
- Use PyNWB behind a dedicated assembly layer for unsupported and hybrid workflows
- Keep validation separate from conversion so both schema and best-practice checks are explicit
- Treat extensions as a deliberate design choice, not a default response to every custom field

## Notes on custom data and metadata

Official NWB documentation points to multiple mechanisms for handling lab-specific information:
- fitting data into existing NWB structures where semantics already align
- lab-specific metadata patterns such as `LabMetaData`
- structured extensions via Neurodata Extensions when the data model genuinely requires new types

Planning implication:
- the product should guide users toward the least-complex valid representation that preserves meaning
- custom information should remain interpretable even when a formal extension is not yet warranted

## Sources

- NWB Overview: https://nwb-overview.readthedocs.io/en/latest/
- Converting neurophysiology data to NWB: https://nwb-overview.readthedocs.io/en/latest/conversion_tutorial/user_guide.html
- Validation of NWB files: https://nwb-overview.readthedocs.io/en/latest/conversion_tutorial/05_validation.html
- Extending NWB: https://nwb-overview.readthedocs.io/en/latest/extensions_tutorial/extensions_tutorial_home.html
- NWB GUIDE docs: https://nwb-guide.readthedocs.io/en/latest/
- NeuroConv docs: https://neuroconv.readthedocs.io/en/stable/
- NeuroConv Conversion Gallery: https://neuroconv.readthedocs.io/en/stable/conversion_examples_gallery/index.html
- PyNWB docs: https://pynwb.readthedocs.io/en/stable/
- PyNWB file module: https://pynwb.readthedocs.io/en/stable/pynwb.file.html
- PyNWB behavior module: https://pynwb.readthedocs.io/en/stable/pynwb.behavior.html
- NWB Inspector docs: https://nwbinspector.readthedocs.io/
