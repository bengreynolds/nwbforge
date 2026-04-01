"""Supported-path pilot adapters."""

from importlib import import_module

from nwbforge.adapters.supported.behavior import (
    NeuroConvDeepLabCutAdapter,
    NeuroConvFicTracAdapter,
)
from nwbforge.adapters.supported.neuroconv_images import NeuroConvImageAdapter
from nwbforge.adapters.supported.tabular import (
    EXCEL_TIME_INTERVAL_ROUTE,
    TABULAR_TIME_INTERVAL_ROUTES,
    CSV_TIME_INTERVAL_ROUTE,
    NeuroConvCsvTimeIntervalsAdapter,
    NeuroConvExcelTimeIntervalsAdapter,
)
from nwbforge.adapters.supported.session_manifest import SessionManifestAdapter

__all__ = [
    "CSV_TIME_INTERVAL_ROUTE",
    "EXCEL_TIME_INTERVAL_ROUTE",
    "NeuroConvCsvTimeIntervalsAdapter",
    "NeuroConvDeepLabCutAdapter",
    "NeuroConvExcelTimeIntervalsAdapter",
    "NeuroConvFicTracAdapter",
    "NeuroConvImageAdapter",
    "SessionManifestAdapter",
    "TABULAR_TIME_INTERVAL_ROUTES",
]


def _try_import_optional(module_name: str, export_name: str) -> None:
    try:
        module = import_module(module_name)
    except ImportError:
        return
    globals()[export_name] = getattr(module, export_name)
    __all__.append(export_name)


_try_import_optional("nwbforge.adapters.supported.neuroconv_audio", "NeuroConvAudioAdapter")
