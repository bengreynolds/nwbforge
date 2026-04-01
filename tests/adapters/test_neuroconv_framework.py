from pathlib import Path

import pytest

from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.adapters.neuroconv import NeuroConvInterfaceAdapter, extracted_fields_from_mapping
from nwbforge.adapters.supported import NeuroConvCsvTimeIntervalsAdapter
from nwbforge.domain.enums import SourceType
from nwbforge.domain.models import ReviewIssue, SourceReference


class MinimalNeuroConvAdapter(NeuroConvInterfaceAdapter):
    adapter_id = "minimal_neuroconv"
    display_name = "Minimal NeuroConv adapter"
    version = "0.1.0"
    interface_cls = object
    record_type = "minimal"
    source_types = (SourceType.FILE,)
    capabilities = AdapterCapabilities()

    def extract(
        self,
        *,
        source: SourceReference,
        interface,
        config,
    ) -> tuple[dict[str, object], tuple[ReviewIssue, ...], tuple[str, ...]]:
        return {}, (), ()


def test_neuroconv_framework_parses_json_source_metadata() -> None:
    source = SourceReference(
        source_id="source-1",
        location=Path("data/trials.csv"),
        source_type=SourceType.FILE,
        label="trial csv",
        metadata={
            "neuroconv.read_kwargs_json": '{"sep":";","encoding":"utf-8"}',
            "neuroconv.metadata_overrides_json": '{"TimeIntervals":{"trials":{"table_name":"trials"}}}',
            "neuroconv.column_name_mapping_json": '{"condition":"trial_type"}',
        },
    )

    config = MinimalNeuroConvAdapter().build_source_config(source)

    assert config.read_kwargs == {"sep": ";", "encoding": "utf-8"}
    assert config.metadata_overrides == {"TimeIntervals": {"trials": {"table_name": "trials"}}}
    assert config.column_name_mapping == {"condition": "trial_type"}


def test_neuroconv_framework_rejects_invalid_json_config() -> None:
    source = SourceReference(
        source_id="source-1",
        location=Path("data/trials.csv"),
        source_type=SourceType.FILE,
        label="trial csv",
        metadata={"neuroconv.read_kwargs_json": "not-json"},
    )

    with pytest.raises(ValueError, match="read_kwargs_json"):
        MinimalNeuroConvAdapter().build_source_config(source)


def test_extracted_fields_from_mapping_flattens_payload() -> None:
    fields = extracted_fields_from_mapping(
        prefix="time_intervals.trials",
        payload={"table_name": "trials", "table_description": "Example"},
        source_id="source-1",
    )

    assert fields["time_intervals.trials.table_name"].value == "trials"
    assert fields["time_intervals.trials.table_description"].value == "Example"


def test_neuroconv_csv_adapter_uses_metadata_read_kwargs_for_source_matching(tmp_path: Path) -> None:
    csv_path = tmp_path / "trials.csv"
    csv_path.write_text("start_time;condition\n0.5;left\n", encoding="utf-8")

    source = SourceReference(
        source_id="source-1",
        location=csv_path,
        source_type=SourceType.FILE,
        label="trial csv",
        metadata={"neuroconv.read_kwargs_json": '{"sep":";"}'},
    )

    assert NeuroConvCsvTimeIntervalsAdapter().can_handle(source) is True
