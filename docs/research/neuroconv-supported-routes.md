# NeuroConv Supported Route Catalog

Research date: 2026-03-31
Last implementation sync: 2026-04-02

## Purpose

This note records the repository's approved NeuroConv-first route catalog for supported-path work.

Repository policy:
- when a source mentions one of the software packages, workflows, or project combinations below, investigate NeuroConv first
- prefer the documented NeuroConv interface or gallery workflow whenever feasible
- only fall back to direct PyNWB when NeuroConv does not support the exact case, the dataset is unusually custom, or the direct PyNWB path is clearly simpler and more maintainable

Important caveat:
- this catalog is a planning and implementation preference list, not a guarantee that every route is equally mature on every Python version or dependency combination
- always check the exact NeuroConv gallery page for installation notes, caveats, and current interface names before implementation

Checklist meaning:
- `[x]` adapter backbone implemented in this repository
- `[ ]` approved NeuroConv-first route not yet implemented here

## Extracellular electrophysiology

### Recording
- [x] AlphaOmega
- [x] Axon
- [x] Axona
- [x] Biocam
- [x] Blackrock
- [x] European Data Format (EDF)
- [x] Intan
- [x] MaxOne
- [x] MCSRaw
- [x] MEArec
- [x] Neuralynx
- [x] NeuroScope
- [x] OpenEphys
- [x] Plexon
- [x] Plexon2
- [x] Spike2
- [x] Spikegadgets
- [x] SpikeGLX
- [x] Tucker-Davis Technologies (TDT)
- [x] White Matter

### Sorting
- [x] Blackrock
- [x] Cell Explorer
- [x] KiloSort
- [x] Neuralynx
- [x] NeuroScope
- [x] Phy
- [x] Plexon

## Intracellular electrophysiology
- [x] Axon Binary File (ABF)

## Optical physiology

### Imaging
- [x] Bruker
- [x] Femtonics
- [x] HDF5
- [x] Micro-Manager
- [x] Miniscope
- [x] Inscopix
- [x] Scanbox
- [x] ScanImage
- [x] ScanImage Legacy (v3.8 and older)
- [x] Thor
- [x] Tiff

### Segmentation
- [x] Caiman
- [x] CNMFE
- [x] EXTRACT
- [x] Inscopix
- [x] Suite2P

## Fiber photometry
- [x] TDT Fiber Photometry

## Behavior
- [x] Audio
- [x] DeepLabCut
- [x] FicTrac
- [x] LightningPose
- [x] Neuralynx NVT
- [x] SLEAP
- [x] Videos
- [x] MedPC

## Image
- [x] Image (png, jpeg, tiff, etc.)

## Text
- [x] CSV
- [x] Excel

## Common interface combinations
- [ ] SpikeGLX & Phy
- [ ] Tiff & Suite2p
- [ ] Electrophysiology and Behavior

## Implementation rules tied to this catalog

1. Start with the NeuroConv Conversion Gallery.
2. Identify the exact documented interface or combined workflow.
3. Use NeuroConv when the route is documented and fits the dataset.
4. Use direct PyNWB only when NeuroConv is not a good fit for the actual case.
5. If PyNWB is used, follow official PyNWB docs and high-level APIs rather than ad hoc HDF5 logic.

## Sources

- NeuroConv docs: https://neuroconv.readthedocs.io/en/stable/
- NeuroConv Conversion Gallery: https://neuroconv.readthedocs.io/en/stable/conversion_examples_gallery/index.html
