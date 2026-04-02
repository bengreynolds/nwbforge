"""Media-category supported adapters."""

from nwbforge.adapters.supported.media.images import NeuroConvImageAdapter

__all__ = [
    "NeuroConvImageAdapter",
]


def _try_import_optional() -> None:
    try:
        from nwbforge.adapters.supported.media.audio import NeuroConvAudioAdapter
    except ImportError:
        return
    globals()["NeuroConvAudioAdapter"] = NeuroConvAudioAdapter
    __all__.append("NeuroConvAudioAdapter")


_try_import_optional()
