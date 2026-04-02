from pathlib import Path

from nwbforge.adapters import NeuroConvFicTracAdapter
from nwbforge.domain.enums import SourceType
from nwbforge.domain.models import SourceReference


def write_fictrac_file(path: Path) -> None:
    rows = []
    for index in range(3):
        values = [0.0] * 25
        values[0] = index
        values[14] = 0.1 * index
        values[15] = 0.2 * index
        values[16] = 0.3 * index
        values[18] = 0.4 * index
        values[19] = 0.5 * index
        values[20] = 0.6 * index
        values[21] = index * 100.0
        rows.append(",".join(str(value) for value in values))
    path.write_text("\n".join(rows), encoding="utf-8")


def test_neuroconv_fictrac_adapter_matches_dat_file(tmp_path: Path) -> None:
    fictrac_path = tmp_path / "fictrac.dat"
    write_fictrac_file(fictrac_path)

    adapter = NeuroConvFicTracAdapter()

    assert (
        adapter.can_handle(
            SourceReference(
                source_id="fictrac-1",
                location=fictrac_path,
                source_type=SourceType.FILE,
                label="FicTrac behavior",
            )
        )
        is True
    )


def test_neuroconv_fictrac_adapter_inspects_behavior_fields(tmp_path: Path) -> None:
    fictrac_path = tmp_path / "fictrac.dat"
    write_fictrac_file(fictrac_path)
    source = SourceReference(
        source_id="fictrac-1",
        location=fictrac_path,
        source_type=SourceType.FILE,
        label="FicTrac behavior",
    )

    result = NeuroConvFicTracAdapter().inspect(source)

    assert result.record_type == "neuroconv_fictrac"
    assert result.fields["behavior.fictrac.source_format"].value == "fictrac_dat"
    assert result.fields["behavior.fictrac.spatial_series_count"].value >= 1
