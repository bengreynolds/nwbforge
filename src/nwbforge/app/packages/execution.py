"""Execution services for route-based package installation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess, run
from typing import Callable, Protocol, Sequence

from nwbforge.app.logging import get_logger, log_event
from nwbforge.app.packages.service_models import PackageInstallPreview, PackageInstallRequest
from nwbforge.app.packages.services import PackageManagementService


def package_utc_now() -> datetime:
    return datetime.now(tz=UTC)


class PackageInstallStage(StrEnum):
    """High-level stages for package-management execution."""

    VALIDATING = "validating"
    INSTALLING = "installing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class PackageInstallProgressEvent:
    """A progress event emitted from real install workflow stages."""

    stage: PackageInstallStage
    percent_complete: int
    message: str
    route_names: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=package_utc_now)


class PackageInstallRuntimeError(RuntimeError):
    """A user-facing package-install error with stage and detail context."""

    def __init__(
        self,
        *,
        stage: PackageInstallStage,
        user_message: str,
        detail: str | None = None,
        route_names: tuple[str, ...] = (),
    ) -> None:
        super().__init__(user_message)
        self.stage = stage
        self.user_message = user_message
        self.detail = detail
        self.route_names = route_names


@dataclass(frozen=True, slots=True)
class PackageInstallResult:
    """Result of a completed package-install execution."""

    preview: PackageInstallPreview
    command: tuple[str, ...]
    completed_process: CompletedProcess[str]


PackageInstallProgressCallback = Callable[[PackageInstallProgressEvent], None]


class PackageCommandRunner(Protocol):
    """Protocol for running package-install commands."""

    def run(self, command: Sequence[str], *, cwd: Path) -> CompletedProcess[str]:
        """Execute the given command."""


class SubprocessPackageCommandRunner:
    """Run install commands through subprocess."""

    def run(self, command: Sequence[str], *, cwd: Path) -> CompletedProcess[str]:
        return run(
            list(command),
            cwd=str(cwd),
            check=True,
            capture_output=True,
            text=True,
        )


class PackageInstallationService:
    """Validate and execute route-based package installation commands."""

    def __init__(
        self,
        package_management_service: PackageManagementService,
        *,
        env_name: str = "nwbforge-dev",
        repo_root: Path | None = None,
        command_runner: PackageCommandRunner | None = None,
    ) -> None:
        self._package_management_service = package_management_service
        self._env_name = env_name
        self._repo_root = repo_root or Path.cwd()
        self._runner = command_runner or SubprocessPackageCommandRunner()
        self._logger = get_logger(__name__)

    def execute_install(
        self,
        request: PackageInstallRequest,
        *,
        progress_callback: PackageInstallProgressCallback | None = None,
    ) -> PackageInstallResult:
        """Validate and execute a route-based package install."""

        preview = self._package_management_service.preview_install(request)
        route_names = preview.plan.selection.routes

        self._emit_progress(
            progress_callback,
            stage=PackageInstallStage.VALIDATING,
            percent_complete=10,
            message="Validating package selection.",
            route_names=route_names,
        )
        log_event(
            self._logger,
            20,
            "Starting package install execution.",
            install_mode=preview.plan.selection.mode.value,
            preset=preview.plan.selection.preset.value,
            route_names=route_names,
            env_name=self._env_name,
        )

        blocking_issues = tuple(issue for issue in preview.issues if issue.blocking)
        if blocking_issues:
            detail = "; ".join(issue.message for issue in blocking_issues)
            log_event(
                self._logger,
                40,
                "Package install validation failed.",
                route_names=route_names,
                detail=detail,
            )
            raise PackageInstallRuntimeError(
                stage=PackageInstallStage.VALIDATING,
                user_message="Package selection needs to be corrected before install can start.",
                detail=detail,
                route_names=route_names,
            )

        command = self._build_command(preview)
        self._emit_progress(
            progress_callback,
            stage=PackageInstallStage.INSTALLING,
            percent_complete=50,
            message="Installing selected route packages.",
            route_names=route_names,
        )

        try:
            completed = self._runner.run(command, cwd=self._repo_root)
        except CalledProcessError as exc:
            detail = exc.stderr or exc.stdout or str(exc)
            log_event(
                self._logger,
                40,
                "Package install execution failed.",
                route_names=route_names,
                command=tuple(command),
                detail=detail,
            )
            self._emit_progress(
                progress_callback,
                stage=PackageInstallStage.FAILED,
                percent_complete=100,
                message="Package installation failed.",
                route_names=route_names,
            )
            raise PackageInstallRuntimeError(
                stage=PackageInstallStage.FAILED,
                user_message="Package installation failed. See logs for details.",
                detail=detail,
                route_names=route_names,
            ) from exc

        log_event(
            self._logger,
            20,
            "Package install execution completed.",
            route_names=route_names,
            command=tuple(command),
        )
        self._emit_progress(
            progress_callback,
            stage=PackageInstallStage.COMPLETED,
            percent_complete=100,
            message="Package installation completed.",
            route_names=route_names,
        )
        return PackageInstallResult(
            preview=preview,
            command=tuple(command),
            completed_process=completed,
        )

    def _build_command(self, preview: PackageInstallPreview) -> tuple[str, ...]:
        return (
            "conda",
            "run",
            "-n",
            self._env_name,
            "python",
            "-m",
            "pip",
            "install",
            "-e",
            preview.plan.editable_requirement,
        )

    @staticmethod
    def _emit_progress(
        progress_callback: PackageInstallProgressCallback | None,
        *,
        stage: PackageInstallStage,
        percent_complete: int,
        message: str,
        route_names: tuple[str, ...],
    ) -> None:
        if progress_callback is None:
            return
        progress_callback(
            PackageInstallProgressEvent(
                stage=stage,
                percent_complete=percent_complete,
                message=message,
                route_names=route_names,
            )
        )
