"""Application-facing services for route-based package management."""

from __future__ import annotations

from pathlib import Path

from nwbforge.app.packages.catalog import PRESET_ROUTE_NAMES, ROUTE_PACKAGE_BY_NAME, ROUTE_PACKAGE_CATALOG
from nwbforge.app.packages.models import InstallMode, InstallPreset, PackageSelection, RoutePackageSpec
from nwbforge.app.packages.planner import DEFAULT_SELECTION_PATH, load_package_selection, resolve_install_plan, save_install_plan
from nwbforge.app.packages.service_models import (
    PackageCompatibilityIssue,
    PackageInstallPreview,
    PackageInstallRequest,
)


class PackageManagementService:
    """Resolve, validate, and persist package-install selections."""

    def __init__(self, *, selection_path: Path = DEFAULT_SELECTION_PATH) -> None:
        self._selection_path = selection_path

    def list_available_routes(self) -> tuple[RoutePackageSpec, ...]:
        """Return the curated route catalog."""

        return ROUTE_PACKAGE_CATALOG

    def get_preset_routes(self) -> dict[InstallPreset, tuple[RoutePackageSpec, ...]]:
        """Return route specs grouped by preset."""

        return {
            preset: tuple(ROUTE_PACKAGE_BY_NAME[route_name] for route_name in route_names)
            for preset, route_names in PRESET_ROUTE_NAMES.items()
        }

    def load_saved_selection(self) -> PackageSelection | None:
        """Return the last saved install selection, if present."""

        return load_package_selection(self._selection_path)

    def preview_install(self, request: PackageInstallRequest) -> PackageInstallPreview:
        """Resolve and validate an install request without executing it."""

        saved_selection = self.load_saved_selection()
        if request.use_saved_selection and saved_selection is not None:
            plan = resolve_install_plan(
                mode=saved_selection.mode,
                preset=saved_selection.preset,
                routes=saved_selection.routes,
            )
        else:
            plan = resolve_install_plan(
                mode=request.mode,
                preset=request.preset,
                routes=request.routes,
            )

        issues = self._build_issues(request, plan)
        preview = PackageInstallPreview(
            request=request,
            plan=plan,
            available_routes=self.list_available_routes(),
            saved_selection=saved_selection,
            issues=issues,
        )

        if request.persist_selection and preview.is_installable:
            save_install_plan(self._selection_path, plan)

        return preview

    def _build_issues(
        self,
        request: PackageInstallRequest,
        plan,
    ) -> tuple[PackageCompatibilityIssue, ...]:
        issues: list[PackageCompatibilityIssue] = []
        request_mode = InstallMode(request.mode)

        if request_mode is InstallMode.SELECTED and plan.selection.preset is InstallPreset.CUSTOM and not plan.selection.routes:
            issues.append(
                PackageCompatibilityIssue(
                    code="package-selection-empty-custom",
                    message="Custom package selection requires at least one route.",
                    blocking=True,
                )
            )

        for route_name in plan.selection.routes:
            route_spec = ROUTE_PACKAGE_BY_NAME[route_name]
            if not route_spec.implemented_in_code:
                issues.append(
                    PackageCompatibilityIssue(
                        code="package-route-not-yet-implemented",
                        message=(
                            f"Route '{route_spec.display_name}' has a curated install target, "
                            "but repository conversion support is not implemented yet."
                        ),
                        blocking=False,
                        route_names=(route_spec.route_name,),
                    )
                )

        return tuple(issues)
