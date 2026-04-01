"""Tabular-category supported adapters."""

from nwbforge.adapters.supported.tabular.neuroconv import (
    CSV_TIME_INTERVAL_ROUTE,
    EXCEL_TIME_INTERVAL_ROUTE,
    TABULAR_TIME_INTERVAL_ROUTES,
    NeuroConvCsvTimeIntervalsAdapter,
    NeuroConvExcelTimeIntervalsAdapter,
)

__all__ = [
    "CSV_TIME_INTERVAL_ROUTE",
    "EXCEL_TIME_INTERVAL_ROUTE",
    "NeuroConvCsvTimeIntervalsAdapter",
    "NeuroConvExcelTimeIntervalsAdapter",
    "TABULAR_TIME_INTERVAL_ROUTES",
]
