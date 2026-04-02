"""Adapter layer exports."""

from importlib import import_module

from nwbforge.adapters.base import AdapterCapabilities, SourceAdapter
from nwbforge.adapters.custom import CustomJsonSessionAdapter
from nwbforge.adapters.registry import AdapterRegistry
from nwbforge.adapters.supported import (
    NeuroConvCsvTimeIntervalsAdapter,
    NeuroConvDeepLabCutAdapter,
    NeuroConvExcelTimeIntervalsAdapter,
    NeuroConvFicTracAdapter,
    NeuroConvImageAdapter,
    SessionManifestAdapter,
)

__all__ = [
    "AdapterCapabilities",
    "AdapterRegistry",
    "CustomJsonSessionAdapter",
    "NeuroConvCsvTimeIntervalsAdapter",
    "NeuroConvDeepLabCutAdapter",
    "NeuroConvExcelTimeIntervalsAdapter",
    "NeuroConvFicTracAdapter",
    "NeuroConvImageAdapter",
    "SessionManifestAdapter",
    "SourceAdapter",
]


def _try_import_optional(module_name: str, export_name: str) -> None:
    try:
        module = import_module(module_name)
    except ImportError:
        return
    globals()[export_name] = getattr(module, export_name)
    __all__.append(export_name)


_try_import_optional("nwbforge.adapters.supported", "NeuroConvAudioAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvVideoAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvLightningPoseAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvSLEAPAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvHdf5ImagingAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvScanImageAdapter")
