"""Sorting-category supported adapters."""

from importlib import import_module

__all__: list[str] = []


def _try_import_optional(export_name: str) -> None:
    try:
        module = import_module("nwbforge.adapters.supported.sorting.neuroconv")
    except ImportError:
        return
    adapter_cls = getattr(module, export_name, None)
    if adapter_cls is None:
        return
    globals()[export_name] = adapter_cls
    __all__.append(export_name)


_try_import_optional("NeuroConvBlackrockSortingAdapter")
_try_import_optional("NeuroConvCellExplorerSortingAdapter")
_try_import_optional("NeuroConvKiloSortSortingAdapter")
_try_import_optional("NeuroConvNeuralynxSortingAdapter")
_try_import_optional("NeuroConvNeuroScopeSortingAdapter")
_try_import_optional("NeuroConvPhySortingAdapter")
_try_import_optional("NeuroConvPlexonSortingAdapter")
