"""Service-facing models for package-management flows."""

from __future__ import annotations

from dataclasses import dataclass

from nwbforge.app.packages.models import InstallPlan, InstallPreset, InstallMode, PackageSelection, RoutePackageSpec


@dataclass(frozen=True, slots=True)
class PackageInstallRequest:
    """A UI- or setup-facing request to prepare a package install plan."""

    mode: InstallMode
    preset: InstallPreset | None = None
    routes: tuple[str, ...] = ()
    use_saved_selection: bool = False
    persist_selection: bool = False


@dataclass(frozen=True, slots=True)
class PackageCompatibilityIssue:
    """A package-management compatibility or readiness issue."""

    code: str
    message: str
    blocking: bool
    route_names: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PackageInstallPreview:
    """Resolved install preview suitable for setup screens or future dialogs."""

    request: PackageInstallRequest
    plan: InstallPlan
    available_routes: tuple[RoutePackageSpec, ...]
    saved_selection: PackageSelection | None
    issues: tuple[PackageCompatibilityIssue, ...]

    @property
    def is_installable(self) -> bool:
        """Return whether no blocking issues remain."""

        return not any(issue.blocking for issue in self.issues)
