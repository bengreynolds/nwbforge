"""Curated route catalog for optional dependency installation."""

from __future__ import annotations

from importlib.util import find_spec

from nwbforge.app.packages.models import InstallPreset, RoutePackageSpec


ROUTE_PACKAGE_CATALOG: tuple[RoutePackageSpec, ...] = (
    RoutePackageSpec(
        route_name="audio",
        display_name="Audio",
        extra_name="audio",
        description="AudioInterface plus required sound/array dependencies.",
        required_modules=("ndx_sound", "scipy"),
        implemented_in_code=True,
    ),
    RoutePackageSpec(
        route_name="deeplabcut",
        display_name="DeepLabCut",
        extra_name="deeplabcut",
        description="DeepLabCut pose-estimation support and the ndx-pose extension.",
        required_modules=("ndx_pose",),
        implemented_in_code=True,
    ),
    RoutePackageSpec(
        route_name="lightningpose",
        display_name="LightningPose",
        extra_name="lightningpose",
        description="LightningPose pose-estimation support with required video and ndx-pose dependencies.",
        required_modules=("cv2", "ndx_pose"),
        implemented_in_code=True,
    ),
    RoutePackageSpec(
        route_name="excel",
        display_name="Excel",
        extra_name="excel",
        description="Excel time-interval support through openpyxl-backed readers.",
        required_modules=("openpyxl",),
        implemented_in_code=True,
    ),
    RoutePackageSpec(
        route_name="image",
        display_name="Image",
        extra_name="image",
        description="Still-image support through Pillow-backed readers.",
        required_modules=("PIL",),
        implemented_in_code=True,
    ),
    RoutePackageSpec(
        route_name="videos",
        display_name="Videos",
        extra_name="videos",
        description="External video support through NeuroConv's video interfaces and OpenCV-backed metadata readers.",
        required_modules=("cv2",),
        implemented_in_code=True,
    ),
    RoutePackageSpec(
        route_name="sleap",
        display_name="SLEAP",
        extra_name="sleap",
        description="SLEAP pose-estimation support through NeuroConv's sleap extra and ndx-pose.",
        required_modules=("sleap_io", "ndx_pose"),
        implemented_in_code=True,
    ),
    RoutePackageSpec(
        route_name="hdf5",
        display_name="HDF5 Imaging",
        extra_name="hdf5",
        description="Extractor-backed HDF5 imaging support through NeuroConv and roiextractors.",
        required_modules=("h5py", "roiextractors"),
        implemented_in_code=True,
    ),
    RoutePackageSpec(
        route_name="micromanager",
        display_name="Micro-Manager TIFF",
        extra_name="micromanager",
        description="Micro-Manager TIFF imaging support through NeuroConv's micromanagertiff extra.",
        required_modules=("roiextractors", "tifffile"),
        implemented_in_code=True,
    ),
    RoutePackageSpec(
        route_name="miniscope",
        display_name="Miniscope",
        extra_name="miniscope",
        description="Miniscope imaging support through NeuroConv's miniscope extra and ndx-miniscope.",
        required_modules=("roiextractors", "ndx_miniscope"),
        implemented_in_code=True,
    ),
    RoutePackageSpec(
        route_name="scanimage",
        display_name="ScanImage",
        extra_name="scanimage",
        description="ScanImage imaging support through NeuroConv's scanimage extra.",
        required_modules=("roiextractors", "tifffile"),
        implemented_in_code=True,
    ),
    RoutePackageSpec(
        route_name="thor",
        display_name="Thor",
        extra_name="thor",
        description="ThorImageLS TIFF imaging support through NeuroConv's thor extra.",
        required_modules=("roiextractors", "tifffile"),
        implemented_in_code=True,
    ),
)

ROUTE_PACKAGE_BY_NAME = {spec.route_name: spec for spec in ROUTE_PACKAGE_CATALOG}

PRESET_ROUTE_NAMES: dict[InstallPreset, tuple[str, ...]] = {
    InstallPreset.MINIMAL: (),
    InstallPreset.COMMON: ("audio", "deeplabcut", "excel", "image"),
    InstallPreset.FULL: tuple(spec.route_name for spec in ROUTE_PACKAGE_CATALOG),
    InstallPreset.CUSTOM: (),
}


def route_dependencies_available(route_name: str) -> bool:
    """Return whether the current environment satisfies the curated dependency gate for a route."""

    spec = ROUTE_PACKAGE_BY_NAME[route_name]
    return all(find_spec(module_name) is not None for module_name in spec.required_modules)
