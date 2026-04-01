"""Planning helpers for route-based package installation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from nwbforge.app.packages.catalog import PRESET_ROUTE_NAMES, ROUTE_PACKAGE_BY_NAME
from nwbforge.app.packages.models import InstallMode, InstallPlan, InstallPreset, PackageSelection


DEFAULT_SELECTION_PATH = Path(".nwbforge/install-selection.json")


def resolve_install_plan(
    *,
    mode: InstallMode | str,
    preset: InstallPreset | str | None = None,
    routes: Iterable[str] = (),
) -> InstallPlan:
    """Resolve a validated install plan from mode, preset, and route names."""

    normalized_mode = InstallMode(mode)
    normalized_routes = _normalize_routes(routes)

    if normalized_mode is InstallMode.MINIMAL:
        selection = PackageSelection(
            mode=InstallMode.MINIMAL,
            preset=InstallPreset.MINIMAL,
            routes=(),
        )
        return InstallPlan(selection=selection, extras=())

    if normalized_mode is InstallMode.FULL:
        full_routes = PRESET_ROUTE_NAMES[InstallPreset.FULL]
        selection = PackageSelection(
            mode=InstallMode.FULL,
            preset=InstallPreset.FULL,
            routes=full_routes,
        )
        return InstallPlan(selection=selection, extras=_extras_for_routes(full_routes))

    normalized_preset = InstallPreset(preset or (InstallPreset.CUSTOM if normalized_routes else InstallPreset.COMMON))
    if normalized_routes and normalized_preset is not InstallPreset.CUSTOM:
        raise ValueError("Explicit route selection can only be combined with the custom preset.")

    if normalized_preset is InstallPreset.CUSTOM:
        selected_routes = normalized_routes
    else:
        selected_routes = PRESET_ROUTE_NAMES[normalized_preset]

    selection = PackageSelection(
        mode=InstallMode.SELECTED,
        preset=normalized_preset,
        routes=selected_routes,
    )
    return InstallPlan(selection=selection, extras=_extras_for_routes(selected_routes))


def save_install_plan(path: Path, plan: InstallPlan) -> None:
    """Persist the last selected install plan to disk."""

    payload = {
        "mode": plan.selection.mode.value,
        "preset": plan.selection.preset.value,
        "routes": list(plan.selection.routes),
        "extras": list(plan.extras),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_package_selection(path: Path) -> PackageSelection | None:
    """Load a previously saved selection, if present."""

    if not path.is_file():
        return None

    payload = json.loads(path.read_text(encoding="utf-8"))
    return PackageSelection(
        mode=InstallMode(payload["mode"]),
        preset=InstallPreset(payload["preset"]),
        routes=tuple(payload["routes"]),
    )


def _normalize_routes(routes: Iterable[str]) -> tuple[str, ...]:
    cleaned = []
    seen: set[str] = set()
    for route_name in routes:
        normalized = route_name.strip().lower()
        if not normalized:
            continue
        if normalized not in ROUTE_PACKAGE_BY_NAME:
            raise ValueError(f"Unknown install route '{route_name}'.")
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
    return tuple(cleaned)


def _extras_for_routes(routes: Iterable[str]) -> tuple[str, ...]:
    extras = []
    seen: set[str] = set()
    for route_name in routes:
        extra_name = ROUTE_PACKAGE_BY_NAME[route_name].extra_name
        if extra_name in seen:
            continue
        seen.add(extra_name)
        extras.append(extra_name)
    return tuple(extras)
