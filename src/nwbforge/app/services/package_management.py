"""Thin UI-facing package-management controller services."""

from __future__ import annotations

from concurrent.futures import Future

from nwbforge.app.packages import (
    PackageInstallPreview,
    PackageInstallProgressCallback,
    PackageInstallRequest,
    PackageInstallResult,
    PackageManagementService,
)
from nwbforge.app.runtime.contracts import PackageInstallationExecutor


class PackageManagementController:
    """Bind package preview and install execution into a UI-facing service shape."""

    def __init__(
        self,
        package_management_service: PackageManagementService,
        installation_executor: PackageInstallationExecutor,
    ) -> None:
        self._package_management_service = package_management_service
        self._installation_executor = installation_executor

    def list_available_routes(self):
        """Return curated route package options for setup/package screens."""

        return self._package_management_service.list_available_routes()

    def list_preset_routes(self):
        """Return route specs grouped by preset."""

        return self._package_management_service.get_preset_routes()

    def load_saved_selection(self):
        """Return the last saved selection, if present."""

        return self._package_management_service.load_saved_selection()

    def preview_install(self, request: PackageInstallRequest) -> PackageInstallPreview:
        """Preview a package install request for UI confirmation."""

        return self._package_management_service.preview_install(request)

    def start_install(
        self,
        request: PackageInstallRequest,
        *,
        progress_callback: PackageInstallProgressCallback | None = None,
    ) -> Future[PackageInstallResult]:
        """Run route-based package installation off the UI thread."""

        return self._installation_executor.submit_install(
            request,
            progress_callback=progress_callback,
        )

    def shutdown(self, wait: bool = True) -> None:
        """Shut down the underlying background executor if it supports shutdown."""

        shutdown = getattr(self._installation_executor, "shutdown", None)
        if shutdown is not None:
            shutdown(wait=wait)
