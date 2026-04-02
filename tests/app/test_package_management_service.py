from pathlib import Path

from nwbforge.app.packages import (
    InstallMode,
    InstallPreset,
    PackageInstallRequest,
    PackageManagementService,
)


def test_package_management_service_lists_available_routes() -> None:
    service = PackageManagementService()

    route_names = {route.route_name for route in service.list_available_routes()}

    assert "alphaomega" in route_names
    assert "axon" in route_names
    assert "axona" in route_names
    assert "biocam" in route_names
    assert "blackrock" in route_names
    assert "brukertiff" in route_names
    assert "deeplabcut" in route_names
    assert "edf" in route_names
    assert "femtonics" in route_names
    assert "lightningpose" in route_names
    assert "inscopix" in route_names
    assert "mcsraw" in route_names
    assert "maxone" in route_names
    assert "mearec" in route_names
    assert "medpc" in route_names
    assert "sleap" in route_names
    assert "intan" in route_names
    assert "neuralynx" in route_names
    assert "neuroscope" in route_names
    assert "openephys_binary" in route_names
    assert "openephys_legacy" in route_names
    assert "plexon" in route_names
    assert "plexon2" in route_names
    assert "scanbox" in route_names
    assert "spikegadgets" in route_names
    assert "spike2" in route_names
    assert "spikeglx" in route_names
    assert "tdt" in route_names
    assert "tiff" in route_names
    assert "whitematter" in route_names
    assert "videos" in route_names
    assert "hdf5" in route_names
    assert "micromanager" in route_names
    assert "miniscope" in route_names
    assert "scanimage" in route_names
    assert "scanimage_legacy" in route_names
    assert "thor" in route_names


def test_package_management_service_preview_accepts_implemented_optional_route(tmp_path: Path) -> None:
    service = PackageManagementService(selection_path=tmp_path / "selection.json")

    preview = service.preview_install(
        PackageInstallRequest(
            mode=InstallMode.SELECTED,
            preset=InstallPreset.CUSTOM,
            routes=("scanimage",),
        )
    )

    assert preview.is_installable is True
    assert not any(issue.code == "package-route-not-yet-implemented" for issue in preview.issues)


def test_package_management_service_blocks_empty_custom_selection(tmp_path: Path) -> None:
    service = PackageManagementService(selection_path=tmp_path / "selection.json")

    preview = service.preview_install(
        PackageInstallRequest(
            mode=InstallMode.SELECTED,
            preset=InstallPreset.CUSTOM,
            routes=(),
        )
    )

    assert preview.is_installable is False
    assert any(issue.code == "package-selection-empty-custom" for issue in preview.issues)


def test_package_management_service_persists_valid_selection(tmp_path: Path) -> None:
    selection_path = tmp_path / "selection.json"
    service = PackageManagementService(selection_path=selection_path)

    preview = service.preview_install(
        PackageInstallRequest(
            mode=InstallMode.SELECTED,
            preset=InstallPreset.CUSTOM,
            routes=("deeplabcut", "image"),
            persist_selection=True,
        )
    )

    assert preview.is_installable is True
    assert selection_path.is_file() is True
    saved = service.load_saved_selection()
    assert saved is not None
    assert saved.routes == ("deeplabcut", "image")
