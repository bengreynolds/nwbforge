"""Tabular-category supported adapters."""

from __future__ import annotations

from importlib import import_module

__all__: list[str] = []

_LAZY_EXPORTS = {
    "CSV_TIME_INTERVAL_ROUTE": ("nwbforge.adapters.supported.tabular.neuroconv", "CSV_TIME_INTERVAL_ROUTE"),
    "EXCEL_TIME_INTERVAL_ROUTE": ("nwbforge.adapters.supported.tabular.neuroconv", "EXCEL_TIME_INTERVAL_ROUTE"),
    "TABULAR_TIME_INTERVAL_ROUTES": ("nwbforge.adapters.supported.tabular.neuroconv", "TABULAR_TIME_INTERVAL_ROUTES"),
    "NeuroConvCsvTimeIntervalsAdapter": (
        "nwbforge.adapters.supported.tabular.neuroconv",
        "NeuroConvCsvTimeIntervalsAdapter",
    ),
    "NeuroConvExcelTimeIntervalsAdapter": (
        "nwbforge.adapters.supported.tabular.neuroconv",
        "NeuroConvExcelTimeIntervalsAdapter",
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
