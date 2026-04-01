"""Route-based package install planning for setup and future UI flows."""

from nwbforge.app.packages.catalog import PRESET_ROUTE_NAMES, ROUTE_PACKAGE_BY_NAME, ROUTE_PACKAGE_CATALOG
from nwbforge.app.packages.execution import (
    PackageCommandRunner,
    PackageInstallationService,
    PackageInstallProgressCallback,
    PackageInstallProgressEvent,
    PackageInstallResult,
    PackageInstallRuntimeError,
    PackageInstallStage,
    SubprocessPackageCommandRunner,
)
from nwbforge.app.packages.models import InstallMode, InstallPlan, InstallPreset, PackageSelection, RoutePackageSpec
from nwbforge.app.packages.planner import DEFAULT_SELECTION_PATH, load_package_selection, resolve_install_plan, save_install_plan
from nwbforge.app.packages.service_models import PackageCompatibilityIssue, PackageInstallPreview, PackageInstallRequest
from nwbforge.app.packages.services import PackageManagementService

__all__ = [
    "DEFAULT_SELECTION_PATH",
    "InstallMode",
    "InstallPlan",
    "InstallPreset",
    "PackageCommandRunner",
    "PackageCompatibilityIssue",
    "PackageInstallationService",
    "PackageInstallPreview",
    "PackageInstallProgressCallback",
    "PackageInstallProgressEvent",
    "PackageInstallRequest",
    "PackageInstallResult",
    "PackageInstallRuntimeError",
    "PackageInstallStage",
    "PackageManagementService",
    "PRESET_ROUTE_NAMES",
    "PackageSelection",
    "ROUTE_PACKAGE_BY_NAME",
    "ROUTE_PACKAGE_CATALOG",
    "RoutePackageSpec",
    "load_package_selection",
    "resolve_install_plan",
    "save_install_plan",
    "SubprocessPackageCommandRunner",
]
