from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pynwb import NWBHDF5IO, NWBFile, TimeSeries
from pynwb.behavior import Position, SpatialSeries
from pynwb.file import Subject

from nwbforge.app.services import NwbFileController, NwbViewerError


def write_example_nwb_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "example.nwb"
    nwbfile = NWBFile(
        session_description="viewer test session",
        identifier="viewer-test-001",
        session_start_time=datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
        experiment_description="Standalone viewer test file",
        session_id="viewer-session",
    )
    nwbfile.subject = Subject(subject_id="mouse-01", species="Mus musculus", sex="U", age="P90D")
    nwbfile.add_acquisition(
        TimeSeries(
            name="raw_trace",
            data=[0.1, 0.2, 0.3],
            unit="a.u.",
            timestamps=[0.0, 1.0, 2.0],
            description="Example acquisition trace",
        )
    )
    behavior_module = nwbfile.create_processing_module("behavior", "Behavior outputs")
    behavior_module.add(
        Position(
            name="position",
            spatial_series=SpatialSeries(
                name="spatial_series",
                data=[[0.0, 1.0], [1.0, 2.0]],
                reference_frame="origin",
                unit="meters",
                timestamps=[0.0, 1.0],
                description="Tracked position",
            ),
        )
    )

    with NWBHDF5IO(file_path, "w") as io:
        io.write(nwbfile)
    return file_path


def test_nwb_file_controller_opens_file_and_builds_root_tree(tmp_path: Path) -> None:
    nwb_path = write_example_nwb_file(tmp_path)
    controller = NwbFileController()

    root_nodes = controller.open_file(nwb_path)

    assert controller.is_open is True
    assert controller.file_path == nwb_path.resolve()
    labels = [node.label for node in root_nodes]
    assert labels[0] == "Metadata"
    assert "Acquisition" in labels
    assert "Processing" in labels
    assert controller.default_expanded_path == "/metadata"


def test_nwb_file_controller_loads_children_and_timeseries_detail(tmp_path: Path) -> None:
    nwb_path = write_example_nwb_file(tmp_path)
    controller = NwbFileController()
    controller.open_file(nwb_path)

    metadata_children = controller.children_for_path("/metadata")
    acquisition_children = controller.children_for_path("/acquisition")
    timeseries_detail = controller.detail_for_path("/acquisition/raw_trace")

    assert any(node.label == "subject" for node in metadata_children)
    assert any(node.label == "raw_trace" for node in acquisition_children)
    assert timeseries_detail.node_type == "TimeSeries"
    assert any(row == ("unit", "a.u.") for row in timeseries_detail.summary_rows)
    assert "Time series preview" in (timeseries_detail.text_content or "")


def test_nwb_file_controller_rejects_missing_file() -> None:
    controller = NwbFileController()

    try:
        controller.open_file(Path("C:/missing/example.nwb"))
    except NwbViewerError as exc:
        assert exc.message == "The selected NWB file does not exist."
    else:  # pragma: no cover - defensive failure branch
        raise AssertionError("Expected NwbViewerError for a missing NWB file.")
