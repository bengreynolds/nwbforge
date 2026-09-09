from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess
import logging

import pytest

from nwbforge.app.packages import (
    InstallMode,
    InstallPreset,
    PackageInstallRequest,
    PackageInstallationService,
    PackageInstallRuntimeError,
    PackageInstallStage,
    PackageManagementService,
)


class FakeRunner:
    def __init__(self, result: CompletedProcess[str] | None = None, error: Exception | None = None) -> None:
        self.result = result or CompletedProcess(args=["python"], returncode=0, stdout="ok", stderr="")
        self.error = error
        self.commands: list[tuple[tuple[str, ...], Path]] = []

    def run(self, command, *, cwd: Path) -> CompletedProcess[str]:
        self.commands.append((tuple(command), cwd))
        if self.error is not None:
            raise self.error
        return self.result


def make_service(tmp_path: Path, runner: FakeRunner) -> PackageInstallationService:
    package_service = PackageManagementService(selection_path=tmp_path / "selection.json")
    return PackageInstallationService(
        package_service,
        env_name="nwbforge-dev",
        repo_root=tmp_path,
        command_runner=runner,
    )


def test_package_installation_service_executes_install_command(tmp_path: Path) -> None:
    runner = FakeRunner()
    service = make_service(tmp_path, runner)
    events = []

    result = service.execute_install(
        PackageInstallRequest(
            mode=InstallMode.SELECTED,
            preset=InstallPreset.CUSTOM,
            routes=("deeplabcut", "image"),
        ),
        progress_callback=events.append,
    )

    assert result.command == (
        "conda",
        "run",
        "-n",
        "nwbforge-dev",
        "python",
        "-s",
        "-m",
        "pip",
        "install",
        "-e",
        ".[deeplabcut,image]",
    )
    assert events[0].stage is PackageInstallStage.VALIDATING
    assert events[1].stage is PackageInstallStage.INSTALLING
    assert events[-1].stage is PackageInstallStage.COMPLETED


def test_package_installation_service_executes_rich_viewer_install_command(tmp_path: Path) -> None:
    runner = FakeRunner()
    service = make_service(tmp_path, runner)

    result = service.execute_install(
        PackageInstallRequest(
            mode=InstallMode.SELECTED,
            preset=InstallPreset.CUSTOM,
            routes=("viewer_rich",),
        )
    )

    assert result.command == (
        "conda",
        "run",
        "-n",
        "nwbforge-dev",
        "python",
        "-s",
        "-m",
        "pip",
        "install",
        "-e",
        ".[viewer_rich]",
    )


def test_package_installation_service_blocks_invalid_selection(tmp_path: Path) -> None:
    runner = FakeRunner()
    service = make_service(tmp_path, runner)

    with pytest.raises(PackageInstallRuntimeError) as excinfo:
        service.execute_install(
            PackageInstallRequest(
                mode=InstallMode.SELECTED,
                preset=InstallPreset.CUSTOM,
                routes=(),
            )
        )

    assert excinfo.value.stage is PackageInstallStage.VALIDATING
    assert runner.commands == []


def test_package_installation_service_wraps_runner_failure(tmp_path: Path) -> None:
    runner = FakeRunner(
        error=CalledProcessError(
            returncode=1,
            cmd=["conda", "run"],
            stderr="pip install failed",
        )
    )
    service = make_service(tmp_path, runner)
    events = []

    with pytest.raises(PackageInstallRuntimeError) as excinfo:
        service.execute_install(
            PackageInstallRequest(
                mode=InstallMode.SELECTED,
                preset=InstallPreset.CUSTOM,
                routes=("deeplabcut",),
            ),
            progress_callback=events.append,
        )

    assert excinfo.value.stage is PackageInstallStage.FAILED
    assert "pip install failed" in (excinfo.value.detail or "")
    assert events[-1].stage is PackageInstallStage.FAILED


def test_package_installation_service_logs_structured_failure_context(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.ERROR)
    runner = FakeRunner(
        error=CalledProcessError(
            returncode=1,
            cmd=["conda", "run"],
            stderr="install exploded",
        )
    )
    service = make_service(tmp_path, runner)

    with pytest.raises(PackageInstallRuntimeError):
        service.execute_install(
            PackageInstallRequest(
                mode=InstallMode.SELECTED,
                preset=InstallPreset.CUSTOM,
                routes=("deeplabcut",),
            )
        )

    records = [record for record in caplog.records if hasattr(record, "nwbforge_context")]
    failure_record = next(record for record in records if record.message == "Package install execution failed.")
    assert failure_record.nwbforge_context["route_names"] == ("deeplabcut",)
    assert "install exploded" in failure_record.nwbforge_context["detail"]
