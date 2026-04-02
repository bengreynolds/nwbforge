from concurrent.futures import Future
from pathlib import Path

from nwbforge.app.packages import (
    InstallMode,
    InstallPreset,
    PackageInstallRequest,
    PackageInstallResult,
    PackageInstallationService,
    PackageManagementService,
)
from nwbforge.app.runtime import ThreadedPackageInstallationExecutor
from nwbforge.app.services import PackageManagementController


class FakeRunner:
    def run(self, command, *, cwd: Path):
        from subprocess import CompletedProcess

        return CompletedProcess(args=list(command), returncode=0, stdout="ok", stderr="")


def make_controller(tmp_path: Path) -> PackageManagementController:
    package_service = PackageManagementService(selection_path=tmp_path / "selection.json")
    installation_service = PackageInstallationService(
        package_service,
        repo_root=tmp_path,
        command_runner=FakeRunner(),
    )
    executor = ThreadedPackageInstallationExecutor(installation_service)
    return PackageManagementController(package_service, executor)


def test_package_management_controller_exposes_preview_and_routes(tmp_path: Path) -> None:
    controller = make_controller(tmp_path)

    routes = controller.list_available_routes()
    preview = controller.preview_install(
        PackageInstallRequest(
            mode=InstallMode.SELECTED,
            preset=InstallPreset.CUSTOM,
            routes=("deeplabcut",),
        )
    )

    assert any(route.route_name == "deeplabcut" for route in routes)
    assert preview.plan.selection.routes == ("deeplabcut",)
    controller.shutdown()


def test_package_management_controller_starts_background_install(tmp_path: Path) -> None:
    controller = make_controller(tmp_path)
    events = []

    future = controller.start_install(
        PackageInstallRequest(
            mode=InstallMode.SELECTED,
            preset=InstallPreset.CUSTOM,
            routes=("deeplabcut",),
        ),
        progress_callback=events.append,
    )

    assert isinstance(future, Future)
    result = future.result(timeout=10)
    assert isinstance(result, PackageInstallResult)
    assert events[0].message == "Package installation queued."
    controller.shutdown()
