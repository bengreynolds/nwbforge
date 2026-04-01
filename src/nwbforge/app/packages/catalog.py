"""Curated route catalog for optional dependency installation."""

from __future__ import annotations

from nwbforge.app.packages.models import InstallPreset, RoutePackageSpec


ROUTE_PACKAGE_CATALOG: tuple[RoutePackageSpec, ...] = (
    RoutePackageSpec(
        route_name="audio",
        display_name="Audio",
        extra_name="audio",
        description="AudioInterface plus required sound/array dependencies.",
        implemented_in_code=True,
    ),
    RoutePackageSpec(
        route_name="deeplabcut",
        display_name="DeepLabCut",
        extra_name="deeplabcut",
        description="DeepLabCut pose-estimation support and the ndx-pose extension.",
        implemented_in_code=True,
    ),
    RoutePackageSpec(
        route_name="excel",
        display_name="Excel",
        extra_name="excel",
        description="Excel time-interval support through openpyxl-backed readers.",
        implemented_in_code=True,
    ),
    RoutePackageSpec(
        route_name="image",
        display_name="Image",
        extra_name="image",
        description="Still-image support through Pillow-backed readers.",
        implemented_in_code=True,
    ),
    RoutePackageSpec(
        route_name="scanimage",
        display_name="ScanImage",
        extra_name="scanimage",
        description="ScanImage imaging support through NeuroConv's scanimage extra.",
        implemented_in_code=False,
    ),
)

ROUTE_PACKAGE_BY_NAME = {spec.route_name: spec for spec in ROUTE_PACKAGE_CATALOG}

PRESET_ROUTE_NAMES: dict[InstallPreset, tuple[str, ...]] = {
    InstallPreset.MINIMAL: (),
    InstallPreset.COMMON: ("audio", "deeplabcut", "excel", "image"),
    InstallPreset.FULL: tuple(spec.route_name for spec in ROUTE_PACKAGE_CATALOG),
    InstallPreset.CUSTOM: (),
}
