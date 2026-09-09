"""Media-category supported adapters."""

from __future__ import annotations

from importlib import import_module

__all__: list[str] = []

_LAZY_EXPORTS = {
    "NeuroConvImageAdapter": ("nwbforge.adapters.supported.media.images", "NeuroConvImageAdapter"),
    "NeuroConvAudioAdapter": ("nwbforge.adapters.supported.media.audio", "NeuroConvAudioAdapter"),
    "NeuroConvVideoAdapter": ("nwbforge.adapters.supported.media.videos", "NeuroConvVideoAdapter"),
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
