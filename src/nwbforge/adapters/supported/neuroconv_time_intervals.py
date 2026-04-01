"""Shared NeuroConv-backed adapters for tabular time-interval sources."""

from __future__ import annotations

from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.adapters.neuroconv import (
    NeuroConvInterfaceAdapter,
    NeuroConvSourceConfig,
    extracted_fields_from_dataframe,
    extracted_fields_from_mapping,
)
from nwbforge.domain.enums import ConversionPathway, IssueSeverity, SourceType
from nwbforge.domain.models import ExtractedField, ReviewIssue, SourceReference


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
