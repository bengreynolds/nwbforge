from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import nwbforge.ui.qt.main_window as main_window_module
from PySide6.QtWidgets import QFileDialog
from pynwb import NWBHDF5IO, NWBFile, TimeSeries
from pynwb.file import Subject

from nwbforge.app.packages import PackageInstallationService, PackageManagementService
from nwbforge.app.runtime import ThreadedPackageInstallationExecutor
from nwbforge.app.services import PackageManagementController, UiSettingsService
from nwbforge.app.services.nwb_viewer_rich import BaseRichNodeRenderer, NwbRichRendererStatus
from nwbforge.ui import DesktopShellModel, PackageInstallerScreenModel, SettingsScreenModel
from nwbforge.ui.conversion_session import ConversionSessionScreenModel
from nwbforge.ui.qt import MainWindow, NwbViewerWindow


class FakeRunner:
    def run(self, command, *, cwd: Path):
        from subprocess import CompletedProcess

        return CompletedProcess(args=list(command), returncode=0, stdout="ok", stderr="")


class FakeConversionExecutor:
    def submit_preview(self, session, *, progress_callback=None):
        from concurrent.futures import Future

        future = Future()
        future.set_result(None)
        return future


class FakeRichSession:
    def __init__(self, url: str) -> None:
        self.url = url
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeRichRenderer(BaseRichNodeRenderer):
    renderer_name = "fake-rich"

    def __init__(self) -> None:
        self.launched_paths: list[str] = []
        self.closed = False

    def status_for_node(self, node):
        if node is None:
            return NwbRichRendererStatus(
                renderer_name=self.renderer_name,
                is_available=True,
                is_supported=False,
                message="Select a node.",
            )
        return NwbRichRendererStatus(
            renderer_name=self.renderer_name,
            is_available=True,
            is_supported=True,
            message="Open fake rich preview.",
        )

    def launch_for_node(self, node):
        self.launched_paths.append(node.path)
        return FakeRichSession("http://127.0.0.1:9000/")

    def close(self) -> None:
        self.closed = True

    def submit_execute(self, preview, output_path: Path, *, progress_callback=None):
        from concurrent.futures import Future

        future = Future()
        future.set_result(None)
        return future


def make_package_screen(tmp_path: Path) -> PackageInstallerScreenModel:
    package_service = PackageManagementService(selection_path=tmp_path / "selection.json")
    installation_service = PackageInstallationService(
        package_service,
        repo_root=tmp_path,
        command_runner=FakeRunner(),
    )
    executor = ThreadedPackageInstallationExecutor(installation_service)
    controller = PackageManagementController(package_service, executor)
    return PackageInstallerScreenModel(controller)


def make_settings_screen(tmp_path: Path) -> SettingsScreenModel:
    return SettingsScreenModel(UiSettingsService(tmp_path / "ui-settings.json"))


def write_example_nwb_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "viewer-example.nwb"
    nwbfile = NWBFile(
        session_description="viewer qt session",
        identifier="viewer-qt-001",
        session_start_time=datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
        session_id="viewer-qt",
    )
    nwbfile.subject = Subject(subject_id="mouse-qt", species="Mus musculus", sex="U")
    nwbfile.add_acquisition(
        TimeSeries(
            name="raw_trace",
            data=[0.1, 0.2, 0.3],
            unit="a.u.",
            timestamps=[0.0, 1.0, 2.0],
            description="qt viewer acquisition",
        )
    )
    with NWBHDF5IO(file_path, "w") as io:
        io.write(nwbfile)
    return file_path


def test_nwb_viewer_window_loads_read_only_tree_and_expands_metadata(qapp, tmp_path: Path) -> None:
    nwb_path = write_example_nwb_file(tmp_path)

    window = NwbViewerWindow(file_path=nwb_path)
    window.show()
    qapp.processEvents()

    assert window.windowTitle().endswith(nwb_path.name)
    assert window.tree_widget.topLevelItemCount() >= 2
    assert window.tree_widget.topLevelItem(0).text(0) == "Metadata"
    assert window.tree_widget.topLevelItem(0).isExpanded() is True
    assert window.tree_widget.topLevelItem(1).isExpanded() is False
    assert "read-only" in window.statusBar().currentMessage().lower()

    metadata_item = window.tree_widget.topLevelItem(0)
    window.tree_widget.setCurrentItem(metadata_item)
    qapp.processEvents()
    assert "Type:" in window.detail_pane._type_label.text()
    window.close()


def test_nwb_viewer_window_can_open_from_file_menu(qapp, tmp_path: Path, monkeypatch) -> None:
    nwb_path = write_example_nwb_file(tmp_path)
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(nwb_path), "NWB files (*.nwb)"),
    )

    window = NwbViewerWindow()
    window.show()
    qapp.processEvents()

    window._open_action.trigger()
    qapp.processEvents()

    assert window.controller.file_path == nwb_path.resolve()
    assert window.tree_widget.topLevelItemCount() > 0
    window.close()


def test_nwb_viewer_window_can_launch_optional_rich_preview(qapp, tmp_path: Path) -> None:
    nwb_path = write_example_nwb_file(tmp_path)
    rich_renderer = FakeRichRenderer()

    window = NwbViewerWindow(file_path=nwb_path, rich_renderer=rich_renderer)
    window.show()
    qapp.processEvents()

    acquisition_item = window.tree_widget.topLevelItem(1)
    acquisition_item.setExpanded(True)
    qapp.processEvents()
    trace_item = acquisition_item.child(0)
    window.tree_widget.setCurrentItem(trace_item)
    qapp.processEvents()
    window._open_rich_preview_action.trigger()
    qapp.processEvents()

    assert rich_renderer.launched_paths == ["/acquisition/raw_trace"]
    assert "http://127.0.0.1:9000/" in window.statusBar().currentMessage()
    window.close()
    assert rich_renderer.closed is True


def test_main_window_opens_nwb_artifact_in_viewer_window(qapp, tmp_path: Path) -> None:
    nwb_path = write_example_nwb_file(tmp_path)
    window = MainWindow(
        DesktopShellModel(),
        make_settings_screen(tmp_path),
        make_package_screen(tmp_path),
        ConversionSessionScreenModel(FakeConversionExecutor()),
    )
    window.show()
    qapp.processEvents()

    opened = window._open_artifact_path(nwb_path)
    qapp.processEvents()

    assert opened is True
    assert len(window._viewer_windows) == 1
    assert window._viewer_windows[0].controller.file_path == nwb_path.resolve()
    window._viewer_windows[0].close()
    window.close()
