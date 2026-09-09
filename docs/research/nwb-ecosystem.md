# NWB Ecosystem Research

Research date: 2026-03-31

NWB is the target format, NWB GUIDE is the guided-conversion UX reference, NeuroConv is the supported-route backend, PyNWB is the custom/hybrid writer base, and NWB Inspector is the best-practice check layer.

Project implications:
- Supported routes should start with NeuroConv
- Custom and hybrid paths should use PyNWB behind a dedicated assembly layer
- Validation should stay separate from conversion
- Extensions should be deliberate, not default

Sources:
- NWB Overview: https://nwb-overview.readthedocs.io/en/latest/
- Converting neurophysiology data to NWB: https://nwb-overview.readthedocs.io/en/latest/conversion_tutorial/user_guide.html
- Validation of NWB files: https://nwb-overview.readthedocs.io/en/latest/conversion_tutorial/05_validation.html
- Extending NWB: https://nwb-overview.readthedocs.io/en/latest/extensions_tutorial/extensions_tutorial_home.html
- NWB GUIDE docs: https://nwb-guide.readthedocs.io/en/latest/
- NeuroConv docs: https://neuroconv.readthedocs.io/en/stable/
- NeuroConv Conversion Gallery: https://neuroconv.readthedocs.io/en/stable/conversion_examples_gallery/index.html
- PyNWB docs: https://pynwb.readthedocs.io/en/stable/
- NWB Inspector docs: https://nwbinspector.readthedocs.io/
