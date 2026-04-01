from pathlib import Path

from nwbforge.adapters import NeuroConvCsvTimeIntervalsAdapter
from nwbforge.domain.enums import SourceType
from nwbforge.domain.models import SourceReference


def test_neuroconv_csv_time_intervals_adapter_matches_csv_with_start_time(tmp_path: Path) -> None:
    csv_path = tmp_path / "trials.csv"
    csv_path.write_text("start_time,condition\n0.5,left\n", encoding="utf-8")

    adapter = NeuroConvCsvTimeIntervalsAdapter()

    assert (
        adapter.can_handle(
            SourceReference(
                source_id="source-1",
                location=csv_path,
                source_type=SourceType.FILE,
                label="trial csv",
            )
        )
        is True
    )


def test_neuroconv_csv_time_intervals_adapter_inspects_rows_and_table_metadata(tmp_path: Path) -> None:
    csv_path = tmp_path / "trials.csv"
    csv_path.write_text(
        "start_time,condition,correct\n0.5,left,True\n1.2,right,False\n",
        encoding="utf-8",
    )
    source = SourceReference(
        source_id="source-1",
        location=csv_path,
        source_type=SourceType.FILE,
        label="trial csv",
    )

    result = NeuroConvCsvTimeIntervalsAdapter().inspect(source)

    assert result.record_type == "neuroconv_csv_time_intervals"
    assert result.fields["time_intervals.trials.table_name"].value == "trials"
    assert result.fields["time_intervals.trials.rows.0.start_time"].value == 0.5
    assert result.fields["time_intervals.trials.rows.0.condition"].value == "left"
    assert result.fields["time_intervals.trials.rows.1.correct"].value is False
    assert any(issue.code == "time-intervals-missing-stop-time" for issue in result.issues)
