from __future__ import annotations

from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess

from nwbforge.app.packages import (
    InstallMode,
    InstallPreset,
    PackageInstallationService,
    PackageManagementService,
)
from nwbforge.app.runtime import ThreadedPackageInstallationExecutor
from nwbforge.app.services import PackageManagementController
from nwbforge.ui import PackageInstallerScreenModel


class FakeRunner:
    def run(self, command, *, cwd: Path):
        return CompletedProcess(args=list(command), returncode=0, stdout="ok", stderr="")


class FailingRunner:
    def run(self, command, *, cwd: Path):
        raise CalledProcessError(returncode=1, cmd=list(command), stderr="install failed")


def make_screen_model(tmp_path: Path) -> PackageInstallerScreenModel:
    package_service = PackageManagementService(selection_path=tmp_path / "selection.json")
    installation_service = PackageInstallationService(
        package_service,
        repo_root=tmp_path,
        command_runner=FakeRunner(),
    )
    executor = ThreadedPackageInstallationExecutor(installation_service)
    controller = PackageManagementController(package_service, executor)
    return PackageInstallerScreenModel(controller)


def make_failing_screen_model(tmp_path: Path) -> PackageInstallerScreenModel:
    package_service = PackageManagementService(selection_path=tmp_path / "selection.json")
    installation_service = PackageInstallationService(
        package_service,
        repo_root=tmp_path,
        command_runner=FailingRunner(),
    )
    executor = ThreadedPackageInstallationExecutor(installation_service)
    controller = PackageManagementController(package_service, executor)
    return PackageInstallerScreenModel(controller)


def test_package_installer_screen_model_loads_default_preview(tmp_path: Path) -> None:
    screen = make_screen_model(tmp_path)

    state = screen.load()

    assert state.install_mode is InstallMode.SELECTED
    assert state.install_preset is InstallPreset.COMMON
    assert "deeplabcut" in state.selected_routes
    assert state.preview is not None
    assert state.is_installable is True
    screen.shutdown()


def test_package_installer_screen_model_updates_custom_routes(tmp_path: Path) -> None:
    screen = make_screen_model(tmp_path)
    screen.load()

    state = screen.set_custom_routes(("image", "scanimage", "image", "missing"))

    assert state.install_preset is InstallPreset.CUSTOM
    assert state.selected_routes == ("image", "scanimage")
    assert state.preview is not None
    assert any(issue.route_names == ("scanimage",) for issue in state.issues)
    screen.shutdown()


def test_package_installer_screen_model_runs_background_install(tmp_path: Path) -> None:
    screen = make_screen_model(tmp_path)
    screen.load()
    state_updates = []
    screen.subscribe(state_updates.append, emit_initial=False)

    future = screen.start_install()
    result = future.result(timeout=10)

    assert result.preview.plan.selection.routes == screen.state.last_completed_routes
    assert screen.state.is_install_running is False
    assert screen.state.progress_event is not None
    assert screen.state.progress_event.message == "Package installation completed."
    assert any(update.progress_event is not None for update in state_updates)
    screen.shutdown()


def test_package_installer_screen_model_surfaces_user_facing_error(tmp_path: Path) -> None:
    screen = make_failing_screen_model(tmp_path)
    screen.load()

    future = screen.start_install()

    try:
        future.result(timeout=10)
    except Exception:
        pass

    assert screen.state.user_error is not None
    assert screen.state.user_error.category == "packages"
    assert screen.state.error_message == "Package installation failed. See logs for details."
    screen.shutdown()
