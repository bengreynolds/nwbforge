from pathlib import Path

import pytest

from nwbforge.app.packages import (
    InstallMode,
    InstallPreset,
    PackageInstallRequest,
    PackageInstallResult,
    PackageInstallRuntimeError,
    PackageInstallStage,
    PackageInstallationService,
    PackageManagementService,
)
from nwbforge.app.runtime import ThreadedPackageInstallationExecutor


class FakeRunner:
    def run(self, command, *, cwd: Path):
        from subprocess import CompletedProcess

        return CompletedProcess(args=list(command), returncode=0, stdout="ok", stderr="")


def make_installation_service(tmp_path: Path) -> PackageInstallationService:
    return PackageInstallationService(
        PackageManagementService(selection_path=tmp_path / "selection.json"),
        env_name="nwbforge-dev",
        repo_root=tmp_path,
        command_runner=FakeRunner(),
    )


def test_threaded_package_installation_executor_emits_queue_and_completion_events(tmp_path: Path) -> None:
    executor = ThreadedPackageInstallationExecutor(make_installation_service(tmp_path))
    events = []

    future = executor.submit_install(
        PackageInstallRequest(
            mode=InstallMode.SELECTED,
            preset=InstallPreset.CUSTOM,
            routes=("deeplabcut",),
        ),
        progress_callback=events.append,
    )
    result = future.result(timeout=10)

    assert isinstance(result, PackageInstallResult)
    assert events[0].stage is PackageInstallStage.QUEUED
    assert events[1].stage is PackageInstallStage.VALIDATING
    assert events[-1].stage is PackageInstallStage.COMPLETED
    executor.shutdown()


class BrokenInstallationService:
    def execute_install(self, request, *, progress_callback=None):
        del request, progress_callback
        raise ValueError("boom")


def test_threaded_package_installation_executor_wraps_failures(tmp_path: Path) -> None:
    del tmp_path
    executor = ThreadedPackageInstallationExecutor(BrokenInstallationService())

    future = executor.submit_install(
        PackageInstallRequest(
            mode=InstallMode.SELECTED,
            preset=InstallPreset.CUSTOM,
            routes=("deeplabcut",),
        )
    )

    with pytest.raises(PackageInstallRuntimeError, match="Package installation failed"):
        future.result(timeout=10)

    executor.shutdown()
