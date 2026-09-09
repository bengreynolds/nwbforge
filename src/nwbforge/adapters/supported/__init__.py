"""Supported-path pilot adapters."""

from __future__ import annotations

from importlib import import_module

from nwbforge.adapters.supported.session_manifest import SessionManifestAdapter

__all__ = ["SessionManifestAdapter"]

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "CSV_TIME_INTERVAL_ROUTE": ("nwbforge.adapters.supported.tabular", "CSV_TIME_INTERVAL_ROUTE"),
    "EXCEL_TIME_INTERVAL_ROUTE": ("nwbforge.adapters.supported.tabular", "EXCEL_TIME_INTERVAL_ROUTE"),
    "TABULAR_TIME_INTERVAL_ROUTES": ("nwbforge.adapters.supported.tabular", "TABULAR_TIME_INTERVAL_ROUTES"),
    "NeuroConvCsvTimeIntervalsAdapter": ("nwbforge.adapters.supported.tabular", "NeuroConvCsvTimeIntervalsAdapter"),
    "NeuroConvExcelTimeIntervalsAdapter": ("nwbforge.adapters.supported.tabular", "NeuroConvExcelTimeIntervalsAdapter"),
    "NeuroConvImageAdapter": ("nwbforge.adapters.supported.media", "NeuroConvImageAdapter"),
    "NeuroConvAudioAdapter": ("nwbforge.adapters.supported.media", "NeuroConvAudioAdapter"),
    "NeuroConvVideoAdapter": ("nwbforge.adapters.supported.media", "NeuroConvVideoAdapter"),
    "NeuroConvDeepLabCutAdapter": ("nwbforge.adapters.supported.behavior", "NeuroConvDeepLabCutAdapter"),
    "NeuroConvFicTracAdapter": ("nwbforge.adapters.supported.behavior", "NeuroConvFicTracAdapter"),
    "NeuroConvLightningPoseAdapter": ("nwbforge.adapters.supported.behavior", "NeuroConvLightningPoseAdapter"),
    "NeuroConvMedPCAdapter": ("nwbforge.adapters.supported.behavior", "NeuroConvMedPCAdapter"),
    "NeuroConvNeuralynxNvtAdapter": ("nwbforge.adapters.supported.behavior", "NeuroConvNeuralynxNvtAdapter"),
    "NeuroConvSLEAPAdapter": ("nwbforge.adapters.supported.behavior", "NeuroConvSLEAPAdapter"),
    "NeuroConvAlphaOmegaAdapter": ("nwbforge.adapters.supported.ecephys", "NeuroConvAlphaOmegaAdapter"),
    "NeuroConvAxonAdapter": ("nwbforge.adapters.supported.ecephys", "NeuroConvAxonAdapter"),
    "NeuroConvAxonaAdapter": ("nwbforge.adapters.supported.ecephys", "NeuroConvAxonaAdapter"),
    "NeuroConvBiocamAdapter": ("nwbforge.adapters.supported.ecephys", "NeuroConvBiocamAdapter"),
    "NeuroConvBlackrockAdapter": ("nwbforge.adapters.supported.ecephys", "NeuroConvBlackrockAdapter"),
    "NeuroConvEdfAdapter": ("nwbforge.adapters.supported.ecephys", "NeuroConvEdfAdapter"),
    "NeuroConvIntanAdapter": ("nwbforge.adapters.supported.ecephys", "NeuroConvIntanAdapter"),
    "NeuroConvMaxOneAdapter": ("nwbforge.adapters.supported.ecephys", "NeuroConvMaxOneAdapter"),
    "NeuroConvMCSRawAdapter": ("nwbforge.adapters.supported.ecephys", "NeuroConvMCSRawAdapter"),
    "NeuroConvMEArecAdapter": ("nwbforge.adapters.supported.ecephys", "NeuroConvMEArecAdapter"),
    "NeuroConvNeuralynxAdapter": ("nwbforge.adapters.supported.ecephys", "NeuroConvNeuralynxAdapter"),
    "NeuroConvNeuroScopeAdapter": ("nwbforge.adapters.supported.ecephys", "NeuroConvNeuroScopeAdapter"),
    "NeuroConvOpenEphysBinaryAnalogAdapter": (
        "nwbforge.adapters.supported.ecephys",
        "NeuroConvOpenEphysBinaryAnalogAdapter",
    ),
    "NeuroConvOpenEphysBinaryAdapter": ("nwbforge.adapters.supported.ecephys", "NeuroConvOpenEphysBinaryAdapter"),
    "NeuroConvOpenEphysLegacyAdapter": ("nwbforge.adapters.supported.ecephys", "NeuroConvOpenEphysLegacyAdapter"),
    "NeuroConvPlexonAdapter": ("nwbforge.adapters.supported.ecephys", "NeuroConvPlexonAdapter"),
    "NeuroConvPlexon2Adapter": ("nwbforge.adapters.supported.ecephys", "NeuroConvPlexon2Adapter"),
    "NeuroConvSpike2Adapter": ("nwbforge.adapters.supported.ecephys", "NeuroConvSpike2Adapter"),
    "NeuroConvSpikeGadgetsAdapter": ("nwbforge.adapters.supported.ecephys", "NeuroConvSpikeGadgetsAdapter"),
    "NeuroConvSpikeGLXAdapter": ("nwbforge.adapters.supported.ecephys", "NeuroConvSpikeGLXAdapter"),
    "NeuroConvTdtAdapter": ("nwbforge.adapters.supported.ecephys", "NeuroConvTdtAdapter"),
    "NeuroConvWhiteMatterAdapter": ("nwbforge.adapters.supported.ecephys", "NeuroConvWhiteMatterAdapter"),
    "NeuroConvHdf5ImagingAdapter": ("nwbforge.adapters.supported.imaging", "NeuroConvHdf5ImagingAdapter"),
    "NeuroConvBrukerTiffSinglePlaneAdapter": (
        "nwbforge.adapters.supported.imaging",
        "NeuroConvBrukerTiffSinglePlaneAdapter",
    ),
    "NeuroConvBrukerTiffMultiPlaneAdapter": (
        "nwbforge.adapters.supported.imaging",
        "NeuroConvBrukerTiffMultiPlaneAdapter",
    ),
    "NeuroConvFemtonicsAdapter": ("nwbforge.adapters.supported.imaging", "NeuroConvFemtonicsAdapter"),
    "NeuroConvInscopixAdapter": ("nwbforge.adapters.supported.imaging", "NeuroConvInscopixAdapter"),
    "NeuroConvMicroManagerTiffAdapter": ("nwbforge.adapters.supported.imaging", "NeuroConvMicroManagerTiffAdapter"),
    "NeuroConvMiniscopeAdapter": ("nwbforge.adapters.supported.imaging", "NeuroConvMiniscopeAdapter"),
    "NeuroConvScanboxAdapter": ("nwbforge.adapters.supported.imaging", "NeuroConvScanboxAdapter"),
    "NeuroConvScanImageAdapter": ("nwbforge.adapters.supported.imaging", "NeuroConvScanImageAdapter"),
    "NeuroConvScanImageLegacyAdapter": ("nwbforge.adapters.supported.imaging", "NeuroConvScanImageLegacyAdapter"),
    "NeuroConvTiffImagingAdapter": ("nwbforge.adapters.supported.imaging", "NeuroConvTiffImagingAdapter"),
    "NeuroConvThorAdapter": ("nwbforge.adapters.supported.imaging", "NeuroConvThorAdapter"),
    "NeuroConvCaimanSegmentationAdapter": ("nwbforge.adapters.supported.segmentation", "NeuroConvCaimanSegmentationAdapter"),
    "NeuroConvCnmfeSegmentationAdapter": ("nwbforge.adapters.supported.segmentation", "NeuroConvCnmfeSegmentationAdapter"),
    "NeuroConvExtractSegmentationAdapter": ("nwbforge.adapters.supported.segmentation", "NeuroConvExtractSegmentationAdapter"),
    "NeuroConvInscopixSegmentationAdapter": (
        "nwbforge.adapters.supported.segmentation",
        "NeuroConvInscopixSegmentationAdapter",
    ),
    "NeuroConvSuite2pSegmentationAdapter": ("nwbforge.adapters.supported.segmentation", "NeuroConvSuite2pSegmentationAdapter"),
    "NeuroConvBlackrockSortingAdapter": ("nwbforge.adapters.supported.sorting", "NeuroConvBlackrockSortingAdapter"),
    "NeuroConvCellExplorerSortingAdapter": ("nwbforge.adapters.supported.sorting", "NeuroConvCellExplorerSortingAdapter"),
    "NeuroConvKiloSortSortingAdapter": ("nwbforge.adapters.supported.sorting", "NeuroConvKiloSortSortingAdapter"),
    "NeuroConvNeuralynxSortingAdapter": ("nwbforge.adapters.supported.sorting", "NeuroConvNeuralynxSortingAdapter"),
    "NeuroConvNeuroScopeSortingAdapter": ("nwbforge.adapters.supported.sorting", "NeuroConvNeuroScopeSortingAdapter"),
    "NeuroConvPhySortingAdapter": ("nwbforge.adapters.supported.sorting", "NeuroConvPhySortingAdapter"),
    "NeuroConvPlexonSortingAdapter": ("nwbforge.adapters.supported.sorting", "NeuroConvPlexonSortingAdapter"),
    "NeuroConvTdtFiberPhotometryAdapter": (
        "nwbforge.adapters.supported.fiber_photometry",
        "NeuroConvTdtFiberPhotometryAdapter",
    ),
    "NeuroConvSpikeGLXPhyWorkflowAdapter": ("nwbforge.adapters.supported.workflows", "NeuroConvSpikeGLXPhyWorkflowAdapter"),
    "NeuroConvTiffSuite2pWorkflowAdapter": ("nwbforge.adapters.supported.workflows", "NeuroConvTiffSuite2pWorkflowAdapter"),
    "NeuroConvOpenEphysDeepLabCutWorkflowAdapter": (
        "nwbforge.adapters.supported.workflows",
        "NeuroConvOpenEphysDeepLabCutWorkflowAdapter",
    ),
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
