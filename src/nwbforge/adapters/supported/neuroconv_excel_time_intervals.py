"""NeuroConv-backed Excel time-interval adapter."""

from __future__ import annotations

from neuroconv.datainterfaces import ExcelTimeIntervalsInterface

from nwbforge.adapters.neuroconv import NeuroConvSourceConfig
from nwbforge.adapters.supported.neuroconv_time_intervals import NeuroConvTabularTimeIntervalsAdapter
from nwbforge.domain.models import SourceReference


class NeuroConvExcelTimeIntervalsAdapter(NeuroConvTabularTimeIntervalsAdapter):
    """Inspect Excel time-interval sources through NeuroConv."""

    adapter_id = "neuroconv_excel_time_intervals"
    display_name = "NeuroConv Excel time intervals adapter"
    version = "0.1.0"
    interface_cls = ExcelTimeIntervalsInterface
    record_type = "neuroconv_excel_time_intervals"
    supported_suffixes = (".xlsx", ".xlsm")

    def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
        try:
            interface = self.build_interface(source, config)
        except Exception:
            return False
        return self._has_start_time_column(interface.dataframe.columns)
