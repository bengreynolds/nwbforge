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
_try_import_optional("nwbforge.adapters.supported", "NeuroConvMedPCAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvNeuralynxNvtAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvSLEAPAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvAlphaOmegaAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvAxonAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvAxonaAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvBiocamAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvBlackrockAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvEdfAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvIntanAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvMCSRawAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvNeuralynxAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvNeuroScopeAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvOpenEphysBinaryAnalogAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvOpenEphysBinaryAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvOpenEphysLegacyAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvPlexonAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvSpikeGadgetsAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvSpikeGLXAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvTdtAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvWhiteMatterAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvHdf5ImagingAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvBrukerTiffSinglePlaneAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvBrukerTiffMultiPlaneAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvFemtonicsAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvInscopixAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvMicroManagerTiffAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvMiniscopeAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvScanImageAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvScanImageLegacyAdapter")
_try_import_optional("nwbforge.adapters.supported", "NeuroConvThorAdapter")
