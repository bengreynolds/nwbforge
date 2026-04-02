import json
from pathlib import Path

from nwbforge.adapters import (
    NeuroConvBlackrockSortingAdapter,
    NeuroConvCellExplorerSortingAdapter,
    NeuroConvKiloSortSortingAdapter,
    NeuroConvNeuralynxSortingAdapter,
    NeuroConvNeuroScopeSortingAdapter,
    NeuroConvPhySortingAdapter,
    NeuroConvPlexonSortingAdapter,
)
from nwbforge.domain.enums import SourceType
from nwbforge.domain.models import SourceReference


def test_blackrock_sorting_adapter_matches_nev_and_extracts_config(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "recording.nev"
    source_path.write_bytes(b"fake-nev")
    source = SourceReference(
        source_id="blackrock-sorting-1",
        location=source_path,
        source_type=SourceType.FILE,
        label="Blackrock sorting",
        metadata={"neuroconv.interface_kwargs_json": json.dumps({"sampling_frequency": 30000.0, "nsx_to_load": 5})},
    )

    class FakeInterface:
        def get_metadata(self):
            return {"Ecephys": {"Device": [{"name": "Blackrock"}], "UnitProperties": [{"name": "snr"}]}}

    adapter = NeuroConvBlackrockSortingAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert adapter.can_handle(source) is True
    assert result.fields["sorting.blackrock.nsx_to_load"].value == 5


def test_cellexplorer_sorting_adapter_matches_spikes_cellinfo_mat(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "example.spikes.cellinfo.mat"
    source_path.write_bytes(b"fake-mat")
    source = SourceReference(
        source_id="cellexplorer-1",
        location=source_path,
        source_type=SourceType.FILE,
        label="Cell Explorer sorting",
    )

    class FakeInterface:
        def get_metadata(self):
            return {"Ecephys": {"Device": [{"name": "CellExplorer"}], "UnitProperties": [{"name": "depth"}]}}

    adapter = NeuroConvCellExplorerSortingAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert adapter.can_handle(source) is True
    assert result.fields["sorting.cellexplorer.unit_property_count"].value == 1


def test_kilosort_and_phy_routes_do_not_overlap(tmp_path: Path, monkeypatch) -> None:
    kilosort_dir = tmp_path / "kilosort"
    kilosort_dir.mkdir()
    (kilosort_dir / "params.py").write_text("sample_rate = 30000", encoding="utf-8")
    (kilosort_dir / "ops.npy").write_bytes(b"ops")

    phy_dir = tmp_path / "phy"
    phy_dir.mkdir()
    (phy_dir / "params.py").write_text("sample_rate = 30000", encoding="utf-8")
    (phy_dir / "cluster_info.tsv").write_text("cluster_id\tgroup\n", encoding="utf-8")

    kilosort_source = SourceReference(
        source_id="kilosort-1",
        location=kilosort_dir,
        source_type=SourceType.DIRECTORY,
        label="KiloSort folder",
    )
    phy_source = SourceReference(
        source_id="phy-1",
        location=phy_dir,
        source_type=SourceType.DIRECTORY,
        label="Phy folder",
    )

    class FakeInterface:
        def get_metadata(self):
            return {"Ecephys": {"Device": [{"name": "Sorter"}], "UnitProperties": [{"name": "quality"}]}}

    kilosort_adapter = NeuroConvKiloSortSortingAdapter()
    phy_adapter = NeuroConvPhySortingAdapter()
    monkeypatch.setattr(kilosort_adapter, "build_interface", lambda source, config: FakeInterface())
    monkeypatch.setattr(phy_adapter, "build_interface", lambda source, config: FakeInterface())

    assert kilosort_adapter.can_handle(kilosort_source) is True
    assert phy_adapter.can_handle(kilosort_source) is False
    assert phy_adapter.can_handle(phy_source) is True
    assert kilosort_adapter.can_handle(phy_source) is False


def test_neuralynx_sorting_adapter_is_hint_driven(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "neuralynx-sorting"
    source_dir.mkdir()
    (source_dir / "TT1.ntt").write_bytes(b"fake-ntt")

    source_without_hint = SourceReference(
        source_id="neuralynx-sorting-1",
        location=source_dir,
        source_type=SourceType.DIRECTORY,
        label="Neuralynx sorting",
    )
    source_with_hint = SourceReference(
        source_id="neuralynx-sorting-2",
        location=source_dir,
        source_type=SourceType.DIRECTORY,
        label="Neuralynx sorting",
        adapter_hint="neuroconv_neuralynx_sorting",
    )

    class FakeInterface:
        def get_metadata(self):
            return {"Ecephys": {"Device": [{"name": "Neuralynx"}], "UnitProperties": [{"name": "firing_rate"}]}}

    adapter = NeuroConvNeuralynxSortingAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    assert adapter.can_handle(source_without_hint) is False
    result = adapter.inspect(source_with_hint)
    assert result.fields["sorting.neuralynx.device_name"].value == "Neuralynx"


def test_neuroscope_sorting_adapter_matches_res_clu_folder(tmp_path: Path, monkeypatch) -> None:
    source_dir = tmp_path / "neuroscope-sorting"
    source_dir.mkdir()
    (source_dir / "spikes.res.1").write_text("1\n2\n", encoding="utf-8")
    (source_dir / "spikes.clu.1").write_text("2\n1\n1\n", encoding="utf-8")

    source = SourceReference(
        source_id="neuroscope-sorting-1",
        location=source_dir,
        source_type=SourceType.DIRECTORY,
        label="NeuroScope sorting",
        metadata={"neuroconv.interface_kwargs_json": json.dumps({"exclude_shanks": [2]})},
    )

    class FakeInterface:
        def get_metadata(self):
            return {"Ecephys": {"Device": [{"name": "NeuroScope"}], "UnitProperties": [{"name": "shank"}]}}

    adapter = NeuroConvNeuroScopeSortingAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    result = adapter.inspect(source)

    assert adapter.can_handle(source) is True
    assert result.fields["sorting.neuroscope.exclude_shank_count"].value == 1


def test_plexon_sorting_adapter_is_hint_driven(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "recording.plx"
    source_path.write_bytes(b"fake-plx")

    source_without_hint = SourceReference(
        source_id="plexon-sorting-1",
        location=source_path,
        source_type=SourceType.FILE,
        label="Plexon sorting",
    )
    source_with_hint = SourceReference(
        source_id="plexon-sorting-2",
        location=source_path,
        source_type=SourceType.FILE,
        label="Plexon sorting",
        adapter_hint="neuroconv_plexon_sorting",
    )

    class FakeInterface:
        def get_metadata(self):
            return {"Ecephys": {"Device": [{"name": "Plexon"}], "UnitProperties": [{"name": "snr"}]}}

    adapter = NeuroConvPlexonSortingAdapter()
    monkeypatch.setattr(adapter, "build_interface", lambda source, config: FakeInterface())

    assert adapter.can_handle(source_without_hint) is False
    result = adapter.inspect(source_with_hint)
    assert result.fields["sorting.plexon.device_name"].value == "Plexon"
