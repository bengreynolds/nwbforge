"""Models for route-based package installation planning."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class InstallMode(StrEnum):
    """Supported bootstrap modes for development and future UI setup."""

    MINIMAL = "minimal"
    SELECTED = "selected"
    FULL = "full"


class InstallPreset(StrEnum):
    """Named route-selection presets for install planning."""

    MINIMAL = "minimal"
    COMMON = "common"
    FULL = "full"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class RoutePackageSpec:
    """Curated install target mapped to a user-facing route name."""

    route_name: str
    display_name: str
    extra_name: str
    description: str
    required_modules: tuple[str, ...] = ()
    implemented_in_code: bool = False


@dataclass(frozen=True, slots=True)
class PackageSelection:
    """A normalized route-selection request."""

    mode: InstallMode
    preset: InstallPreset
    routes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class InstallPlan:
    """Resolved install plan consumable by setup scripts and future UI."""

    selection: PackageSelection
    extras: tuple[str, ...]

    @property
    def editable_requirement(self) -> str:
        """Return the editable install target for pip."""

        if not self.extras:
            return "."
        return f'.[{",".join(self.extras)}]'
