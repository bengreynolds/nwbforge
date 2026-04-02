"""Imaging-category supported adapters."""

from importlib import import_module

__all__: list[str] = []


def _try_import_optional(export_name: str) -> None:
    try:
        module = import_module("nwbforge.adapters.supported.imaging.neuroconv")
    except ImportError:
        return
    adapter_cls = getattr(module, export_name, None)
    if adapter_cls is None:
        return
    globals()[export_name] = adapter_cls
    __all__.append(export_name)


_try_import_optional("NeuroConvScanImageAdapter")
_try_import_optional("NeuroConvScanImageLegacyAdapter")
_try_import_optional("NeuroConvBrukerTiffSinglePlaneAdapter")
_try_import_optional("NeuroConvBrukerTiffMultiPlaneAdapter")
_try_import_optional("NeuroConvFemtonicsAdapter")
_try_import_optional("NeuroConvHdf5ImagingAdapter")
_try_import_optional("NeuroConvInscopixAdapter")
_try_import_optional("NeuroConvMicroManagerTiffAdapter")
_try_import_optional("NeuroConvMiniscopeAdapter")
_try_import_optional("NeuroConvThorAdapter")
