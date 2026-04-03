"""Ecephys-category supported adapters."""

from importlib import import_module

__all__: list[str] = []


def _try_import_optional(export_name: str) -> None:
    try:
        module = import_module("nwbforge.adapters.supported.ecephys.neuroconv")
    except ImportError:
        return
    adapter_cls = getattr(module, export_name, None)
    if adapter_cls is None:
        return
    globals()[export_name] = adapter_cls
    __all__.append(export_name)


_try_import_optional("NeuroConvIntanAdapter")
_try_import_optional("NeuroConvMaxOneAdapter")
_try_import_optional("NeuroConvMEArecAdapter")
_try_import_optional("NeuroConvAlphaOmegaAdapter")
_try_import_optional("NeuroConvAxonAdapter")
_try_import_optional("NeuroConvAxonaAdapter")
_try_import_optional("NeuroConvBiocamAdapter")
_try_import_optional("NeuroConvBlackrockAdapter")
_try_import_optional("NeuroConvEdfAdapter")
_try_import_optional("NeuroConvMCSRawAdapter")
_try_import_optional("NeuroConvNeuralynxAdapter")
_try_import_optional("NeuroConvNeuroScopeAdapter")
_try_import_optional("NeuroConvOpenEphysBinaryAnalogAdapter")
_try_import_optional("NeuroConvOpenEphysBinaryAdapter")
_try_import_optional("NeuroConvOpenEphysLegacyAdapter")
_try_import_optional("NeuroConvPlexonAdapter")
_try_import_optional("NeuroConvPlexon2Adapter")
_try_import_optional("NeuroConvSpike2Adapter")
_try_import_optional("NeuroConvSpikeGadgetsAdapter")
_try_import_optional("NeuroConvSpikeGLXAdapter")
_try_import_optional("NeuroConvTdtAdapter")
_try_import_optional("NeuroConvWhiteMatterAdapter")
