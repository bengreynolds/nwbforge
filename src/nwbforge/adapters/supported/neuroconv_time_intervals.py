"""Shared NeuroConv-backed adapters for tabular time-interval sources."""

from __future__ import annotations

from csv import reader
from dataclasses import dataclass
from typing import Literal

from neuroconv.datainterfaces import CsvTimeIntervalsInterface, ExcelTimeIntervalsInterface

from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.adapters.neuroconv import (
    NeuroConvInterfaceAdapter,
    NeuroConvSourceConfig,
    extracted_fields_from_dataframe,
    extracted_fields_from_mapping,
)
from nwbforge.domain.enums import ConversionPathway, IssueSeverity, SourceType
from nwbforge.domain.models import ExtractedField, ReviewIssue, SourceReference


@dataclass(frozen=True, slots=True)
class TabularTimeIntervalsRouteConfig:
    """Declarative route config for text/tabular time-interval adapters."""

    adapter_id: str
    display_name: str
    record_type: str
    interface_cls: type
    supported_suffixes: tuple[str, ...]
    match_strategy: Literal["csv_header", "interface_columns"]
    version: str = "0.1.0"


class NeuroConvTabularTimeIntervalsAdapter(NeuroConvInterfaceAdapter):
    """Shared extraction path for NeuroConv tabular interval interfaces."""

    source_types = (SourceType.FILE,)
    capabilities = AdapterCapabilities(
        supported_pathways=(ConversionPathway.SUPPORTED,),
        supports_multi_source_sessions=True,
    )

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

        normalized_columns = {str(column).strip().lower() for column in interface.dataframe.columns}
        if "stop_time" not in normalized_columns:
            issues.append(
                ReviewIssue(
                    code="time-intervals-missing-stop-time",
                    message=(
                        "Tabular interval source omitted stop_time values; downstream NWB writing will infer "
                        "stop times from the next interval start when possible."
                    ),
                    severity=IssueSeverity.WARNING,
                    field="time_intervals.trials.rows.stop_time",
                    source_ids=(source.source_id,),
                )
            )

        return fields, issues, ()

    @staticmethod
    def _has_start_time_column(columns) -> bool:
        normalized_headers = {str(column).strip().lower() for column in columns if column}
        return "start_time" in normalized_headers


class ConfiguredTabularTimeIntervalsAdapter(NeuroConvTabularTimeIntervalsAdapter):
    """Configured text/tabular NeuroConv adapter driven by route declarations."""

    route_config: TabularTimeIntervalsRouteConfig

    def __init__(self) -> None:
        self.adapter_id = self.route_config.adapter_id
        self.display_name = self.route_config.display_name
        self.version = self.route_config.version
        self.interface_cls = self.route_config.interface_cls
        self.record_type = self.route_config.record_type
        self.supported_suffixes = self.route_config.supported_suffixes

    def matches_source(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
        if self.route_config.match_strategy == "csv_header":
            return self._matches_csv_header(source, config)
        if self.route_config.match_strategy == "interface_columns":
            return self._matches_interface_columns(source, config)
        raise ValueError(f"Unsupported route match strategy '{self.route_config.match_strategy}'.")

    def _matches_csv_header(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
        try:
            with source.location.open("r", encoding="utf-8", newline="") as stream:
                headers = next(reader(stream))
        except (OSError, StopIteration, UnicodeDecodeError):
            return False

        separator = str(config.read_kwargs.get("sep", ","))
        if len(headers) == 1 and separator != ",":
            headers = headers[0].split(separator)
        return self._has_start_time_column(headers)

    def _matches_interface_columns(self, source: SourceReference, config: NeuroConvSourceConfig) -> bool:
        try:
            interface = self.build_interface(source, config)
        except Exception:
            return False
        return self._has_start_time_column(interface.dataframe.columns)


CSV_TIME_INTERVAL_ROUTE = TabularTimeIntervalsRouteConfig(
    adapter_id="neuroconv_csv_time_intervals",
    display_name="NeuroConv CSV time intervals adapter",
    record_type="neuroconv_csv_time_intervals",
    interface_cls=CsvTimeIntervalsInterface,
    supported_suffixes=(".csv",),
    match_strategy="csv_header",
)


EXCEL_TIME_INTERVAL_ROUTE = TabularTimeIntervalsRouteConfig(
    adapter_id="neuroconv_excel_time_intervals",
    display_name="NeuroConv Excel time intervals adapter",
    record_type="neuroconv_excel_time_intervals",
    interface_cls=ExcelTimeIntervalsInterface,
    supported_suffixes=(".xlsx", ".xlsm"),
    match_strategy="interface_columns",
)


TABULAR_TIME_INTERVAL_ROUTES = (
    CSV_TIME_INTERVAL_ROUTE,
    EXCEL_TIME_INTERVAL_ROUTE,
)


class NeuroConvCsvTimeIntervalsAdapter(ConfiguredTabularTimeIntervalsAdapter):
    """Inspect CSV time-interval sources through NeuroConv."""

    route_config = CSV_TIME_INTERVAL_ROUTE


class NeuroConvExcelTimeIntervalsAdapter(ConfiguredTabularTimeIntervalsAdapter):
    """Inspect Excel time-interval sources through NeuroConv."""

    route_config = EXCEL_TIME_INTERVAL_ROUTE
