from pathlib import Path

from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ConversionSession, ExtractedField, ExtractionResult, SourceReference
from nwbforge.normalization import RuleBasedNormalizationService


def make_session() -> ConversionSession:
    return ConversionSession(
        session_id="sess-intervals",
        pathway=ConversionPathway.SUPPORTED,
        sources=(
            SourceReference(
                source_id="source-1",
                location=Path("data/trials.csv"),
                source_type=SourceType.FILE,
                label="trial csv",
            ),
        ),
    )


def test_rule_based_normalizer_maps_time_interval_rows() -> None:
    extraction = ExtractionResult(
        source_id="source-1",
        adapter_id="neuroconv_csv_time_intervals",
        record_type="neuroconv_csv_time_intervals",
        fields={
            "time_intervals.trials.table_name": ExtractedField(
                "time_intervals.trials.table_name", "trials", "source-1"
            ),
            "time_intervals.trials.table_description": ExtractedField(
                "time_intervals.trials.table_description",
                "Experimental trials",
                "source-1",
            ),
            "time_intervals.trials.rows.0.start_time": ExtractedField(
                "time_intervals.trials.rows.0.start_time", 0.5, "source-1"
            ),
            "time_intervals.trials.rows.0.condition": ExtractedField(
                "time_intervals.trials.rows.0.condition", "left", "source-1"
            ),
            "time_intervals.trials.rows.1.start_time": ExtractedField(
                "time_intervals.trials.rows.1.start_time", 1.2, "source-1"
            ),
            "time_intervals.trials.rows.1.stop_time": ExtractedField(
                "time_intervals.trials.rows.1.stop_time", 1.8, "source-1"
            ),
        },
    )

    bundle = RuleBasedNormalizationService().normalize(make_session(), (extraction,))

    assert len(bundle.time_interval_tables) == 1
    table = bundle.time_interval_tables[0]
    assert table.table_id == "trials"
    assert table.table_name.value == "trials"
    assert table.table_description is not None
    assert len(table.rows) == 2
    assert table.rows[0].start_time is not None
    assert table.rows[0].start_time.value == 0.5
    assert table.rows[0].metadata["condition"].value == "left"
    assert table.rows[1].stop_time is not None
    assert table.rows[1].stop_time.value == 1.8
