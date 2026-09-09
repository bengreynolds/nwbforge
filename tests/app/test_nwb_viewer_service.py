from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

from pynwb import NWBHDF5IO, NWBFile, TimeSeries
from pynwb.behavior import Position, SpatialSeries
from pynwb.file import Subject

from nwbforge.app.services import NwbFileController, NwbViewerError, NwbWidgetsPanelRenderer


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


def test_nwbwidgets_panel_renderer_reports_missing_optional_packages(tmp_path: Path) -> None:
    nwb_path = write_example_nwb_file(tmp_path)
    controller = NwbFileController()
    controller.open_file(nwb_path)
    renderer = NwbWidgetsPanelRenderer()

    def fake_import_modules_without_user_site(*module_names: str, purge_prefixes=()):
        if module_names == ("hdmf.utils",):
            return (ModuleType("hdmf.utils"),)
        del purge_prefixes
        raise ModuleNotFoundError(",".join(module_names))

    from pytest import MonkeyPatch

    monkeypatch = MonkeyPatch()
    monkeypatch.setattr(
        "nwbforge.app.services.nwb_viewer_rich.import_modules_without_user_site",
        fake_import_modules_without_user_site,
    )
    try:
        status = renderer.status_for_node(controller.root_nodes[0])
    finally:
        monkeypatch.undo()

    assert status.renderer_name == "nwbwidgets-panel"
    assert status.is_available is False
    assert status.is_supported is False
    assert "viewer_rich" in status.message
    assert "nwbwidgets" in status.message


def test_nwbwidgets_panel_renderer_launches_with_fake_modules(tmp_path: Path, monkeypatch) -> None:
    nwb_path = write_example_nwb_file(tmp_path)
    controller = NwbFileController()
    controller.open_file(nwb_path)
    node = controller.node_for_path("/acquisition/raw_trace")

    opened_urls: list[str] = []

    class FakeServer:
        address = "127.0.0.1"
        port = 8765

        def __init__(self) -> None:
            self.stopped = False

        def stop(self) -> None:
            self.stopped = True

    fake_server = FakeServer()
    fake_panel_calls: dict[str, object] = {}

    class FakePanelModule:
        def extension(self, *args):
            fake_panel_calls["extension_args"] = args

        def panel(self, widget):
            fake_panel_calls["widget"] = widget
            return {"wrapped": widget}

        def serve(self, panel_view, *, title, show, start, threaded, port):
            fake_panel_calls["serve"] = {
                "panel_view": panel_view,
                "title": title,
                "show": show,
                "start": start,
                "threaded": threaded,
                "port": port,
            }
            return fake_server

    class FakeNwbWidgetsModule:
        def nwb2widget(self, value):
            return {"node_type": type(value).__name__}

    def fake_import_modules_without_user_site(*module_names: str, purge_prefixes=()):
        if module_names == ("hdmf.utils",):
            return (ModuleType("hdmf.utils"),)
        del purge_prefixes
        resolved = []
        for name in module_names:
            if name == "panel":
                resolved.append(FakePanelModule())
                continue
            if name == "nwbwidgets":
                resolved.append(FakeNwbWidgetsModule())
                continue
            raise ModuleNotFoundError(name)
        return tuple(resolved)

    monkeypatch.setattr(
        "nwbforge.app.services.nwb_viewer_rich.import_modules_without_user_site",
        fake_import_modules_without_user_site,
    )
    monkeypatch.setattr("nwbforge.app.services.nwb_viewer_rich.webbrowser.open_new_tab", opened_urls.append)

    renderer = NwbWidgetsPanelRenderer()
    session = renderer.launch_for_node(node)

    assert session.url == "http://127.0.0.1:8765/"
    assert opened_urls == ["http://127.0.0.1:8765/"]
    assert fake_panel_calls["extension_args"] == ("ipywidgets",)
    assert fake_panel_calls["serve"]["title"].startswith("NWB Rich Preview")

    renderer.close()
    assert fake_server.stopped is True


def test_nwbwidgets_panel_renderer_resolves_threaded_panel_server_url(tmp_path: Path, monkeypatch) -> None:
    nwb_path = write_example_nwb_file(tmp_path)
    controller = NwbFileController()
    controller.open_file(nwb_path)
    node = controller.node_for_path("/acquisition/raw_trace")

    opened_urls: list[str] = []

    class FakeThreadServer:
        def __init__(self) -> None:
            self.server_id = "threaded-server"
            self.stopped = False

        def stop(self) -> None:
            self.stopped = True

    class FakeResolvedServer:
        address = None
        port = 65078

    fake_thread_server = FakeThreadServer()
    fake_panel_calls: dict[str, object] = {}

    class FakePanelModule:
        def __init__(self) -> None:
            self.state = type(
                "FakePanelState",
                (),
                {"_servers": {"threaded-server": (FakeResolvedServer(), object(), [])}},
            )()

        def extension(self, *args):
            fake_panel_calls["extension_args"] = args

        def panel(self, widget):
            fake_panel_calls["widget"] = widget
            return {"wrapped": widget}

        def serve(self, panel_view, *, title, show, start, threaded, port):
            fake_panel_calls["serve"] = {
                "panel_view": panel_view,
                "title": title,
                "show": show,
                "start": start,
                "threaded": threaded,
                "port": port,
            }
            return fake_thread_server

    class FakeNwbWidgetsModule:
        def nwb2widget(self, value):
            return {"node_type": type(value).__name__}

    def fake_import_modules_without_user_site(*module_names: str, purge_prefixes=()):
        if module_names == ("hdmf.utils",):
            return (ModuleType("hdmf.utils"),)
        del purge_prefixes
        resolved = []
        for name in module_names:
            if name == "panel":
                resolved.append(FakePanelModule())
                continue
            if name == "nwbwidgets":
                resolved.append(FakeNwbWidgetsModule())
                continue
            raise ModuleNotFoundError(name)
        return tuple(resolved)

    monkeypatch.setattr(
        "nwbforge.app.services.nwb_viewer_rich.import_modules_without_user_site",
        fake_import_modules_without_user_site,
    )
    monkeypatch.setattr("nwbforge.app.services.nwb_viewer_rich.webbrowser.open_new_tab", opened_urls.append)

    renderer = NwbWidgetsPanelRenderer()
    session = renderer.launch_for_node(node)

    assert session.url == "http://127.0.0.1:65078/"
    assert opened_urls == ["http://127.0.0.1:65078/"]

    renderer.close()
    assert fake_thread_server.stopped is True


def test_nwbwidgets_panel_renderer_checks_optional_modules_with_isolated_imports(monkeypatch) -> None:
    seen_calls: list[tuple[str, ...]] = []

    def fake_import_modules_without_user_site(*module_names: str, purge_prefixes=()):
        seen_calls.append(module_names)
        if module_names == ("hdmf.utils",):
            assert purge_prefixes == ("hdmf", "pynwb")
            return (ModuleType("hdmf.utils"),)
        assert purge_prefixes == ("panel", "nwbwidgets", "ndx_icephys_meta", "hdmf", "pynwb")
        return (object(), object())

    monkeypatch.setattr(
        "nwbforge.app.services.nwb_viewer_rich.import_modules_without_user_site",
        fake_import_modules_without_user_site,
    )

    assert NwbWidgetsPanelRenderer._is_available() is True
    assert seen_calls == [("hdmf.utils",), ("panel", "nwbwidgets")]


def test_nwbwidgets_panel_renderer_adds_hdmf_docval_compat_symbols(monkeypatch) -> None:
    fake_hdmf_utils = ModuleType("hdmf.utils")

    def fake_import_modules_without_user_site(*module_names: str, purge_prefixes=()):
        del purge_prefixes
        if module_names == ("hdmf.utils",):
            return (fake_hdmf_utils,)
        if module_names == ("panel", "nwbwidgets"):
            return (object(), object())
        raise ModuleNotFoundError(",".join(module_names))

    monkeypatch.setattr(
        "nwbforge.app.services.nwb_viewer_rich.import_modules_without_user_site",
        fake_import_modules_without_user_site,
    )

    assert NwbWidgetsPanelRenderer._is_available() is True
    assert hasattr(fake_hdmf_utils, "call_docval_func")
    assert hasattr(fake_hdmf_utils, "fmt_docval_args")
