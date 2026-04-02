# NeuroConv Supported Route Catalog

Research date: 2026-03-31

## Purpose

This note records the repository's approved NeuroConv-first route catalog for supported-path work.

Repository policy:
- when a source mentions one of the software packages, workflows, or project combinations below, investigate NeuroConv first
- prefer the documented NeuroConv interface or gallery workflow whenever feasible
- only fall back to direct PyNWB when NeuroConv does not support the exact case, the dataset is unusually custom, or the direct PyNWB path is clearly simpler and more maintainable

Important caveat:
- this catalog is a planning and implementation preference list, not a guarantee that every route is equally mature on every Python version or dependency combination
- always check the exact NeuroConv gallery page for installation notes, caveats, and current interface names before implementation

## Extracellular electrophysiology

### Recording
- AlphaOmega
- Axon
- Axona
- Biocam
- Blackrock
- European Data Format (EDF)
- Intan
- MaxOne
- MCSRaw
- MEArec
- Neuralynx
- NeuroScope
- OpenEphys
- Plexon
- Plexon2
- Spike2
- Spikegadgets
- SpikeGLX
- Tucker-Davis Technologies (TDT)
- White Matter

### Sorting
- Blackrock
- Cell Explorer
- KiloSort
- Neuralynx
- NeuroScope
- Phy
- Plexon

## Intracellular electrophysiology
- Axon Binary File (ABF)

## Optical physiology

### Imaging
- Bruker
- Femtonics
- HDF5
- Micro-Manager
- Miniscope
- Inscopix
- Scanbox
- ScanImage
- ScanImage Legacy (v3.8 and older)
- Thor
- Tiff

### Segmentation
- Caiman
- CNMFE
- EXTRACT
- Inscopix
- Suite2P

## Fiber photometry
- TDT Fiber Photometry

## Behavior
- Audio
- DeepLabCut
- FicTrac
- LightningPose
- Neuralynx NVT
- SLEAP
- Videos
- MedPC

## Image
- Image (png, jpeg, tiff, etc.)

## Text
- CSV
- Excel

## Common interface combinations
- SpikeGLX & Phy
- Tiff & Suite2p
- Electrophysiology and Behavior

## Implementation rules tied to this catalog

1. Start with the NeuroConv Conversion Gallery.
2. Identify the exact documented interface or combined workflow.
3. Use NeuroConv when the route is documented and fits the dataset.
4. Use direct PyNWB only when NeuroConv is not a good fit for the actual case.
5. If PyNWB is used, follow official PyNWB docs and high-level APIs rather than ad hoc HDF5 logic.

## Sources

- NeuroConv docs: https://neuroconv.readthedocs.io/en/stable/
- NeuroConv Conversion Gallery: https://neuroconv.readthedocs.io/en/stable/conversion_examples_gallery/index.html
