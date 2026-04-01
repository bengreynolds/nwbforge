"""NeuroConv-backed CSV time-interval adapter."""

from __future__ import annotations

from csv import reader

from neuroconv.datainterfaces import CsvTimeIntervalsInterface

from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.adapters.neuroconv import (
    NeuroConvInterfaceAdapter,
    NeuroConvSourceConfig,
    extracted_fields_from_dataframe,
    extracted_fields_from_mapping,
)
from nwbforge.domain.enums import ConversionPathway, IssueSeverity, SourceType
from nwbforge.domain.models import ExtractedField, ReviewIssue, SourceReference


class NeuroConvCsvTimeIntervalsAdapter(NeuroConvInterfaceAdapter):
    """Inspect CSV time-interval sources through NeuroConv."""

    adapter_id = "neuroconv_csv_time_intervals"
    display_name = "NeuroConv CSV time intervals adapter"
    version = "0.1.0"
    interface_cls = CsvTimeIntervalsInterface
    record_type = "neuroconv_csv_time_intervals"
    source_types = (SourceType.FILE,)
    supported_suffixes = (".csv",)
    capabilities = AdapterCapabilities(
        supported_pathways=(ConversionPathway.SUPPORTED,),
        supports_multi_source_sessions=True,
    )

    def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
        try:
            with source.location.open("r", encoding="utf-8", newline="") as stream:
                headers = next(reader(stream))
        except (OSError, StopIteration, UnicodeDecodeError):
            return False

        separator = str(config.read_kwargs.get("sep", ","))
        if len(headers) == 1 and separator != ",":
            headers = headers[0].split(separator)
        normalized_headers = {header.strip().lower() for header in headers if header}
        return "start_time" in normalized_headers

    def extract(
        self,
        *,
        source: SourceReference,
        interface,
        config: NeuroConvSourceConfig,
    ) -> tuple[dict[str, ExtractedField], list[ReviewIssue], tuple[str, ...]]:
        metadata = interface.get_metadata()
        fields: dict[str, ExtractedField] = {}
        issues: list[ReviewIssue] = []

        intervals_metadata = metadata.get("TimeIntervals", {}).get("trials", {})
        metadata_fields = {
            field_name: intervals_metadata[field_name]
            for field_name in ("table_name", "table_description")
            if field_name in intervals_metadata
        }
        fields.update(
            extracted_fields_from_mapping(
                prefix="time_intervals.trials",
                payload=metadata_fields,
                source_id=source.source_id,
            )
        )
        fields.update(
            extracted_fields_from_dataframe(
                prefix="time_intervals.trials.rows",
                dataframe=interface.dataframe,
                source_id=source.source_id,
            )
        )

        if "stop_time" not in interface.dataframe.columns:
            issues.append(
                ReviewIssue(
                    code="csv-time-intervals-missing-stop-time",
                    message=(
                        "CSV source omitted stop_time values; downstream NWB writing will infer stop times "
                        "from the next interval start when possible."
                    ),
                    severity=IssueSeverity.WARNING,
                    field="time_intervals.trials.rows.stop_time",
                    source_ids=(source.source_id,),
                )
            )

        return fields, issues, ()
