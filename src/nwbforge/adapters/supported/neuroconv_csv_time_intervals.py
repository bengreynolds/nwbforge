"""NeuroConv-backed CSV time-interval adapter."""

from __future__ import annotations

from csv import reader
from math import isnan
from pathlib import Path

from neuroconv.datainterfaces import CsvTimeIntervalsInterface

from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.domain.enums import ConversionPathway, IssueSeverity, SourceType
from nwbforge.domain.models import ExtractedField, ExtractionResult, ReviewIssue, SourceReference


class NeuroConvCsvTimeIntervalsAdapter:
    """Inspect CSV time-interval sources through NeuroConv."""

    adapter_id = "neuroconv_csv_time_intervals"
    display_name = "NeuroConv CSV time intervals adapter"
    version = "0.1.0"
    source_types = (SourceType.FILE,)
    capabilities = AdapterCapabilities(
        supported_pathways=(ConversionPathway.SUPPORTED,),
        supports_multi_source_sessions=True,
    )

    def can_handle(self, source: SourceReference) -> bool:
        if source.source_type != SourceType.FILE:
            return False
        if source.location.suffix.lower() != ".csv":
            return False

        try:
            with source.location.open("r", encoding="utf-8", newline="") as stream:
                headers = next(reader(stream))
        except (OSError, StopIteration, UnicodeDecodeError):
            return False

        normalized_headers = {header.strip().lower() for header in headers if header}
        return "start_time" in normalized_headers

    def inspect(self, source: SourceReference) -> ExtractionResult:
        interface = CsvTimeIntervalsInterface(file_path=source.location, verbose=False)
        metadata = interface.get_metadata()
        dataframe = interface.dataframe.where(interface.dataframe.notna(), None)
        fields: dict[str, ExtractedField] = {}
        issues: list[ReviewIssue] = []

        intervals_metadata = metadata.get("TimeIntervals", {}).get("trials", {})
        for field_name in ("table_name", "table_description"):
            value = intervals_metadata.get(field_name)
            if value is None:
                continue
            field_key = f"time_intervals.trials.{field_name}"
            fields[field_key] = ExtractedField(
                key=field_key,
                value=value,
                source_id=source.source_id,
                path=field_key,
            )

        for row_index, row in dataframe.iterrows():
            for column_name, value in row.to_dict().items():
                field_key = f"time_intervals.trials.rows.{row_index}.{column_name}"
                fields[field_key] = ExtractedField(
                    key=field_key,
                    value=self._coerce_value(value),
                    source_id=source.source_id,
                    path=field_key,
                )

        if "stop_time" not in dataframe.columns:
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

        return ExtractionResult(
            source_id=source.source_id,
            adapter_id=self.adapter_id,
            record_type="neuroconv_csv_time_intervals",
            fields=fields,
            issues=tuple(issues),
            notes=(
                f"Inspected with NeuroConv CsvTimeIntervalsInterface from {Path(source.location).name}.",
            ),
        )

    @staticmethod
    def _coerce_value(value: object) -> object:
        coerced = value.item() if hasattr(value, "item") else value
        if isinstance(coerced, float) and isnan(coerced):
            return None
        return coerced
