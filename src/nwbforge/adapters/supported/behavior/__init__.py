"""Behavior-category supported adapters."""

from __future__ import annotations

from importlib import import_module

__all__: list[str] = []

_LAZY_EXPORTS = {
    "NeuroConvDeepLabCutAdapter": "NeuroConvDeepLabCutAdapter",
    "NeuroConvFicTracAdapter": "NeuroConvFicTracAdapter",
    "NeuroConvLightningPoseAdapter": "NeuroConvLightningPoseAdapter",
    "NeuroConvMedPCAdapter": "NeuroConvMedPCAdapter",
    "NeuroConvNeuralynxNvtAdapter": "NeuroConvNeuralynxNvtAdapter",
    "NeuroConvSLEAPAdapter": "NeuroConvSLEAPAdapter",
}


def __getattr__(name: str):
    export_name = _LAZY_EXPORTS.get(name)
    if export_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    try:
        module = import_module("nwbforge.adapters.supported.behavior.neuroconv")
        export = getattr(module, export_name)
    except (AttributeError, ImportError):
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    globals()[export_name] = export
    return export
