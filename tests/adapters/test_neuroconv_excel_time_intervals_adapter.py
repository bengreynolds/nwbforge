from pathlib import Path

import pandas as pd

from nwbforge.adapters import NeuroConvExcelTimeIntervalsAdapter
from nwbforge.domain.enums import SourceType
from nwbforge.domain.models import SourceReference


def test_neuroconv_excel_time_intervals_adapter_matches_excel_with_start_time(tmp_path: Path) -> None:
    excel_path = tmp_path / "trials.xlsx"
    pd.DataFrame([{"start_time": 0.5, "stop_time": 1.0, "condition": "left"}]).to_excel(
        excel_path,
        index=False,
    )

    adapter = NeuroConvExcelTimeIntervalsAdapter()

    assert (
        adapter.can_handle(
            SourceReference(
                source_id="source-1",
                location=excel_path,
                source_type=SourceType.FILE,
                label="trial excel",
            )
        )
        is True
    )


def test_neuroconv_excel_time_intervals_adapter_inspects_rows_and_table_metadata(tmp_path: Path) -> None:
    excel_path = tmp_path / "trials.xlsx"
    pd.DataFrame(
        [
            {"start_time": 0.5, "stop_time": 1.0, "condition": "left", "correct": True},
            {"start_time": 1.2, "stop_time": 1.8, "condition": "right", "correct": False},
        ]
    ).to_excel(excel_path, index=False)
    source = SourceReference(
        source_id="source-1",
        location=excel_path,
        source_type=SourceType.FILE,
        label="trial excel",
    )

    result = NeuroConvExcelTimeIntervalsAdapter().inspect(source)

    assert result.record_type == "neuroconv_excel_time_intervals"
    assert result.fields["time_intervals.trials.table_name"].value == "trials"
    assert result.fields["time_intervals.trials.rows.0.start_time"].value == 0.5
    assert result.fields["time_intervals.trials.rows.0.condition"].value == "left"
    assert result.fields["time_intervals.trials.rows.1.correct"].value is False
    assert not result.issues
