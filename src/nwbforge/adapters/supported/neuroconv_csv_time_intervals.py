"""NeuroConv-backed CSV time-interval adapter."""

from __future__ import annotations

from csv import reader

from neuroconv.datainterfaces import CsvTimeIntervalsInterface

from nwbforge.adapters.neuroconv import NeuroConvSourceConfig
from nwbforge.adapters.supported.neuroconv_time_intervals import NeuroConvTabularTimeIntervalsAdapter
from nwbforge.domain.models import SourceReference


class NeuroConvCsvTimeIntervalsAdapter(NeuroConvTabularTimeIntervalsAdapter):
    """Inspect CSV time-interval sources through NeuroConv."""

    adapter_id = "neuroconv_csv_time_intervals"
    display_name = "NeuroConv CSV time intervals adapter"
    version = "0.1.0"
    interface_cls = CsvTimeIntervalsInterface
    record_type = "neuroconv_csv_time_intervals"
    supported_suffixes = (".csv",)

    def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
        try:
            with source.location.open("r", encoding="utf-8", newline="") as stream:
                headers = next(reader(stream))
        except (OSError, StopIteration, UnicodeDecodeError):
            return False

        separator = str(config.read_kwargs.get("sep", ","))
        if len(headers) == 1 and separator != ",":
            headers = headers[0].split(separator)
        return self._has_start_time_column(headers)
