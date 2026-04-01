"""Runtime contracts for executing conversions and installs in the background."""

from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path
from typing import Protocol

from nwbforge.app.packages import (
    PackageInstallProgressCallback,
    PackageInstallRequest,
    PackageInstallResult,
)
from nwbforge.app.runtime.models import ProgressCallback
from nwbforge.app.services.models import ConversionExecution, ConversionPreview
from nwbforge.domain.models import ConversionSession


class ConversionExecutor(Protocol):
    """Protocol for runtime executors consumable by the future UI."""

    def submit_preview(
        self,
        session: ConversionSession,
        *,
        progress_callback: ProgressCallback | None = None,
    ) -> Future[ConversionPreview]:
        """Run preview generation in the background."""

    def submit_execute(
        self,
        preview: ConversionPreview,
        output_path: Path,
        *,
        progress_callback: ProgressCallback | None = None,
    ) -> Future[ConversionExecution]:
        """Run NWB writing/validation in the background."""


class PackageInstallationExecutor(Protocol):
    """Protocol for running package-install work off the UI thread."""

    def submit_install(
        self,
        request: PackageInstallRequest,
        *,
        progress_callback: PackageInstallProgressCallback | None = None,
    ) -> Future[PackageInstallResult]:
        """Run route-based package installation in the background."""
