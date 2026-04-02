"""Behavior-category supported adapters."""

from importlib import import_module

from nwbforge.adapters.supported.behavior.neuroconv import (
    NeuroConvDeepLabCutAdapter,
    NeuroConvFicTracAdapter,
)

__all__ = [
    "NeuroConvDeepLabCutAdapter",
    "NeuroConvFicTracAdapter",
]


def _try_import_optional(export_name: str) -> None:
    try:
        module = import_module("nwbforge.adapters.supported.behavior.neuroconv")
    except ImportError:
        return
    adapter_cls = getattr(module, export_name, None)
    if adapter_cls is None:
        return
    globals()[export_name] = adapter_cls
    __all__.append(export_name)


_try_import_optional("NeuroConvSLEAPAdapter")
