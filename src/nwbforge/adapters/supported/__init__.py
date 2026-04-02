"""Supported-path pilot adapters."""

from importlib import import_module

from nwbforge.adapters.supported.behavior import (
    NeuroConvDeepLabCutAdapter,
    NeuroConvFicTracAdapter,
)
from nwbforge.adapters.supported.media import NeuroConvImageAdapter
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


_try_import_optional("nwbforge.adapters.supported.media", "NeuroConvAudioAdapter")
_try_import_optional("nwbforge.adapters.supported.media", "NeuroConvVideoAdapter")
_try_import_optional("nwbforge.adapters.supported.behavior", "NeuroConvLightningPoseAdapter")
_try_import_optional("nwbforge.adapters.supported.behavior", "NeuroConvMedPCAdapter")
_try_import_optional("nwbforge.adapters.supported.behavior", "NeuroConvNeuralynxNvtAdapter")
_try_import_optional("nwbforge.adapters.supported.behavior", "NeuroConvSLEAPAdapter")
_try_import_optional("nwbforge.adapters.supported.ecephys", "NeuroConvAlphaOmegaAdapter")
_try_import_optional("nwbforge.adapters.supported.ecephys", "NeuroConvAxonAdapter")
_try_import_optional("nwbforge.adapters.supported.ecephys", "NeuroConvAxonaAdapter")
_try_import_optional("nwbforge.adapters.supported.ecephys", "NeuroConvBiocamAdapter")
_try_import_optional("nwbforge.adapters.supported.ecephys", "NeuroConvBlackrockAdapter")
_try_import_optional("nwbforge.adapters.supported.ecephys", "NeuroConvEdfAdapter")
_try_import_optional("nwbforge.adapters.supported.ecephys", "NeuroConvIntanAdapter")
_try_import_optional("nwbforge.adapters.supported.ecephys", "NeuroConvMaxOneAdapter")
_try_import_optional("nwbforge.adapters.supported.ecephys", "NeuroConvMCSRawAdapter")
_try_import_optional("nwbforge.adapters.supported.ecephys", "NeuroConvMEArecAdapter")
_try_import_optional("nwbforge.adapters.supported.ecephys", "NeuroConvNeuralynxAdapter")
_try_import_optional("nwbforge.adapters.supported.ecephys", "NeuroConvNeuroScopeAdapter")
_try_import_optional("nwbforge.adapters.supported.ecephys", "NeuroConvOpenEphysBinaryAnalogAdapter")
_try_import_optional("nwbforge.adapters.supported.ecephys", "NeuroConvOpenEphysBinaryAdapter")
_try_import_optional("nwbforge.adapters.supported.ecephys", "NeuroConvOpenEphysLegacyAdapter")
_try_import_optional("nwbforge.adapters.supported.ecephys", "NeuroConvPlexonAdapter")
_try_import_optional("nwbforge.adapters.supported.ecephys", "NeuroConvPlexon2Adapter")
_try_import_optional("nwbforge.adapters.supported.ecephys", "NeuroConvSpike2Adapter")
_try_import_optional("nwbforge.adapters.supported.ecephys", "NeuroConvSpikeGadgetsAdapter")
_try_import_optional("nwbforge.adapters.supported.ecephys", "NeuroConvSpikeGLXAdapter")
_try_import_optional("nwbforge.adapters.supported.ecephys", "NeuroConvTdtAdapter")
_try_import_optional("nwbforge.adapters.supported.ecephys", "NeuroConvWhiteMatterAdapter")
_try_import_optional("nwbforge.adapters.supported.imaging", "NeuroConvHdf5ImagingAdapter")
_try_import_optional("nwbforge.adapters.supported.imaging", "NeuroConvBrukerTiffSinglePlaneAdapter")
_try_import_optional("nwbforge.adapters.supported.imaging", "NeuroConvBrukerTiffMultiPlaneAdapter")
_try_import_optional("nwbforge.adapters.supported.imaging", "NeuroConvFemtonicsAdapter")
_try_import_optional("nwbforge.adapters.supported.imaging", "NeuroConvInscopixAdapter")
_try_import_optional("nwbforge.adapters.supported.imaging", "NeuroConvMicroManagerTiffAdapter")
_try_import_optional("nwbforge.adapters.supported.imaging", "NeuroConvMiniscopeAdapter")
_try_import_optional("nwbforge.adapters.supported.imaging", "NeuroConvScanboxAdapter")
_try_import_optional("nwbforge.adapters.supported.imaging", "NeuroConvScanImageAdapter")
_try_import_optional("nwbforge.adapters.supported.imaging", "NeuroConvScanImageLegacyAdapter")
_try_import_optional("nwbforge.adapters.supported.imaging", "NeuroConvTiffImagingAdapter")
_try_import_optional("nwbforge.adapters.supported.imaging", "NeuroConvThorAdapter")
_try_import_optional("nwbforge.adapters.supported.sorting", "NeuroConvBlackrockSortingAdapter")
_try_import_optional("nwbforge.adapters.supported.sorting", "NeuroConvCellExplorerSortingAdapter")
_try_import_optional("nwbforge.adapters.supported.sorting", "NeuroConvKiloSortSortingAdapter")
_try_import_optional("nwbforge.adapters.supported.sorting", "NeuroConvNeuralynxSortingAdapter")
_try_import_optional("nwbforge.adapters.supported.sorting", "NeuroConvNeuroScopeSortingAdapter")
_try_import_optional("nwbforge.adapters.supported.sorting", "NeuroConvPhySortingAdapter")
_try_import_optional("nwbforge.adapters.supported.sorting", "NeuroConvPlexonSortingAdapter")
