"""Adapter layer exports."""

from __future__ import annotations

from importlib import import_module

from nwbforge.adapters.base import AdapterCapabilities, SourceAdapter
from nwbforge.adapters.custom import CustomJsonSessionAdapter
from nwbforge.adapters.registry import AdapterRegistry
from nwbforge.adapters.supported.session_manifest import SessionManifestAdapter

__all__ = [
    "AdapterCapabilities",
    "AdapterRegistry",
    "CustomJsonSessionAdapter",
    "SessionManifestAdapter",
    "SourceAdapter",
]

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "NeuroConvAudioAdapter": ("nwbforge.adapters.supported", "NeuroConvAudioAdapter"),
    "NeuroConvVideoAdapter": ("nwbforge.adapters.supported", "NeuroConvVideoAdapter"),
    "NeuroConvLightningPoseAdapter": ("nwbforge.adapters.supported", "NeuroConvLightningPoseAdapter"),
    "NeuroConvMedPCAdapter": ("nwbforge.adapters.supported", "NeuroConvMedPCAdapter"),
    "NeuroConvNeuralynxNvtAdapter": ("nwbforge.adapters.supported", "NeuroConvNeuralynxNvtAdapter"),
    "NeuroConvSLEAPAdapter": ("nwbforge.adapters.supported", "NeuroConvSLEAPAdapter"),
    "NeuroConvAlphaOmegaAdapter": ("nwbforge.adapters.supported", "NeuroConvAlphaOmegaAdapter"),
    "NeuroConvAxonAdapter": ("nwbforge.adapters.supported", "NeuroConvAxonAdapter"),
    "NeuroConvAxonaAdapter": ("nwbforge.adapters.supported", "NeuroConvAxonaAdapter"),
    "NeuroConvBiocamAdapter": ("nwbforge.adapters.supported", "NeuroConvBiocamAdapter"),
    "NeuroConvBlackrockAdapter": ("nwbforge.adapters.supported", "NeuroConvBlackrockAdapter"),
    "NeuroConvEdfAdapter": ("nwbforge.adapters.supported", "NeuroConvEdfAdapter"),
    "NeuroConvIntanAdapter": ("nwbforge.adapters.supported", "NeuroConvIntanAdapter"),
    "NeuroConvMaxOneAdapter": ("nwbforge.adapters.supported", "NeuroConvMaxOneAdapter"),
    "NeuroConvMCSRawAdapter": ("nwbforge.adapters.supported", "NeuroConvMCSRawAdapter"),
    "NeuroConvMEArecAdapter": ("nwbforge.adapters.supported", "NeuroConvMEArecAdapter"),
    "NeuroConvNeuralynxAdapter": ("nwbforge.adapters.supported", "NeuroConvNeuralynxAdapter"),
    "NeuroConvNeuroScopeAdapter": ("nwbforge.adapters.supported", "NeuroConvNeuroScopeAdapter"),
    "NeuroConvOpenEphysBinaryAnalogAdapter": ("nwbforge.adapters.supported", "NeuroConvOpenEphysBinaryAnalogAdapter"),
    "NeuroConvOpenEphysBinaryAdapter": ("nwbforge.adapters.supported", "NeuroConvOpenEphysBinaryAdapter"),
    "NeuroConvOpenEphysLegacyAdapter": ("nwbforge.adapters.supported", "NeuroConvOpenEphysLegacyAdapter"),
    "NeuroConvPlexonAdapter": ("nwbforge.adapters.supported", "NeuroConvPlexonAdapter"),
    "NeuroConvPlexon2Adapter": ("nwbforge.adapters.supported", "NeuroConvPlexon2Adapter"),
    "NeuroConvSpike2Adapter": ("nwbforge.adapters.supported", "NeuroConvSpike2Adapter"),
    "NeuroConvSpikeGadgetsAdapter": ("nwbforge.adapters.supported", "NeuroConvSpikeGadgetsAdapter"),
    "NeuroConvSpikeGLXAdapter": ("nwbforge.adapters.supported", "NeuroConvSpikeGLXAdapter"),
    "NeuroConvTdtAdapter": ("nwbforge.adapters.supported", "NeuroConvTdtAdapter"),
    "NeuroConvWhiteMatterAdapter": ("nwbforge.adapters.supported", "NeuroConvWhiteMatterAdapter"),
    "NeuroConvHdf5ImagingAdapter": ("nwbforge.adapters.supported", "NeuroConvHdf5ImagingAdapter"),
    "NeuroConvBrukerTiffSinglePlaneAdapter": (
        "nwbforge.adapters.supported",
        "NeuroConvBrukerTiffSinglePlaneAdapter",
    ),
    "NeuroConvBrukerTiffMultiPlaneAdapter": (
        "nwbforge.adapters.supported",
        "NeuroConvBrukerTiffMultiPlaneAdapter",
    ),
    "NeuroConvFemtonicsAdapter": ("nwbforge.adapters.supported", "NeuroConvFemtonicsAdapter"),
    "NeuroConvInscopixAdapter": ("nwbforge.adapters.supported", "NeuroConvInscopixAdapter"),
    "NeuroConvMicroManagerTiffAdapter": ("nwbforge.adapters.supported", "NeuroConvMicroManagerTiffAdapter"),
    "NeuroConvMiniscopeAdapter": ("nwbforge.adapters.supported", "NeuroConvMiniscopeAdapter"),
    "NeuroConvScanboxAdapter": ("nwbforge.adapters.supported", "NeuroConvScanboxAdapter"),
    "NeuroConvScanImageAdapter": ("nwbforge.adapters.supported", "NeuroConvScanImageAdapter"),
    "NeuroConvScanImageLegacyAdapter": ("nwbforge.adapters.supported", "NeuroConvScanImageLegacyAdapter"),
    "NeuroConvTiffImagingAdapter": ("nwbforge.adapters.supported", "NeuroConvTiffImagingAdapter"),
    "NeuroConvThorAdapter": ("nwbforge.adapters.supported", "NeuroConvThorAdapter"),
    "NeuroConvCaimanSegmentationAdapter": ("nwbforge.adapters.supported", "NeuroConvCaimanSegmentationAdapter"),
    "NeuroConvCnmfeSegmentationAdapter": ("nwbforge.adapters.supported", "NeuroConvCnmfeSegmentationAdapter"),
    "NeuroConvExtractSegmentationAdapter": ("nwbforge.adapters.supported", "NeuroConvExtractSegmentationAdapter"),
    "NeuroConvInscopixSegmentationAdapter": ("nwbforge.adapters.supported", "NeuroConvInscopixSegmentationAdapter"),
    "NeuroConvSuite2pSegmentationAdapter": ("nwbforge.adapters.supported", "NeuroConvSuite2pSegmentationAdapter"),
    "NeuroConvBlackrockSortingAdapter": ("nwbforge.adapters.supported", "NeuroConvBlackrockSortingAdapter"),
    "NeuroConvCellExplorerSortingAdapter": ("nwbforge.adapters.supported", "NeuroConvCellExplorerSortingAdapter"),
    "NeuroConvKiloSortSortingAdapter": ("nwbforge.adapters.supported", "NeuroConvKiloSortSortingAdapter"),
    "NeuroConvNeuralynxSortingAdapter": ("nwbforge.adapters.supported", "NeuroConvNeuralynxSortingAdapter"),
    "NeuroConvNeuroScopeSortingAdapter": ("nwbforge.adapters.supported", "NeuroConvNeuroScopeSortingAdapter"),
    "NeuroConvPhySortingAdapter": ("nwbforge.adapters.supported", "NeuroConvPhySortingAdapter"),
    "NeuroConvPlexonSortingAdapter": ("nwbforge.adapters.supported", "NeuroConvPlexonSortingAdapter"),
    "NeuroConvTdtFiberPhotometryAdapter": ("nwbforge.adapters.supported", "NeuroConvTdtFiberPhotometryAdapter"),
    "NeuroConvSpikeGLXPhyWorkflowAdapter": ("nwbforge.adapters.supported", "NeuroConvSpikeGLXPhyWorkflowAdapter"),
    "NeuroConvTiffSuite2pWorkflowAdapter": ("nwbforge.adapters.supported", "NeuroConvTiffSuite2pWorkflowAdapter"),
    "NeuroConvOpenEphysDeepLabCutWorkflowAdapter": (
        "nwbforge.adapters.supported",
        "NeuroConvOpenEphysDeepLabCutWorkflowAdapter",
    ),
    "NeuroConvCsvTimeIntervalsAdapter": ("nwbforge.adapters.supported", "NeuroConvCsvTimeIntervalsAdapter"),
    "NeuroConvExcelTimeIntervalsAdapter": ("nwbforge.adapters.supported", "NeuroConvExcelTimeIntervalsAdapter"),
    "NeuroConvFicTracAdapter": ("nwbforge.adapters.supported", "NeuroConvFicTracAdapter"),
    "NeuroConvDeepLabCutAdapter": ("nwbforge.adapters.supported", "NeuroConvDeepLabCutAdapter"),
    "NeuroConvImageAdapter": ("nwbforge.adapters.supported", "NeuroConvImageAdapter"),
}


def __getattr__(name: str):
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    try:
        module = import_module(target[0])
        export = getattr(module, target[1])
    except (AttributeError, ImportError):
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    globals()[name] = export
    return export
