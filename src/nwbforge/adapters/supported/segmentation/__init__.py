"""Segmentation-category supported adapters."""

from importlib import import_module

__all__: list[str] = []


def _try_import_optional(export_name: str) -> None:
    try:
        module = import_module("nwbforge.adapters.supported.segmentation.neuroconv")
    except ImportError:
        return
    adapter_cls = getattr(module, export_name, None)
    if adapter_cls is None:
        return
    globals()[export_name] = adapter_cls
    __all__.append(export_name)


_try_import_optional("NeuroConvCaimanSegmentationAdapter")
_try_import_optional("NeuroConvCnmfeSegmentationAdapter")
_try_import_optional("NeuroConvExtractSegmentationAdapter")
_try_import_optional("NeuroConvInscopixSegmentationAdapter")
_try_import_optional("NeuroConvSuite2pSegmentationAdapter")
