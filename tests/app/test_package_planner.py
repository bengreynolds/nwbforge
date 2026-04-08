from pathlib import Path

import pytest

from nwbforge.app.packages import (
    InstallMode,
    InstallPreset,
    load_package_selection,
    resolve_install_plan,
    save_install_plan,
)


def test_resolve_install_plan_for_common_selected_mode() -> None:
    plan = resolve_install_plan(mode=InstallMode.SELECTED, preset=InstallPreset.COMMON)

    assert plan.selection.routes == ("audio", "deeplabcut", "excel", "image")
    assert plan.extras == ("audio", "deeplabcut", "excel", "image")
    assert plan.editable_requirement == ".[audio,deeplabcut,excel,image]"


def test_resolve_install_plan_for_custom_routes_is_deduplicated() -> None:
    plan = resolve_install_plan(
        mode=InstallMode.SELECTED,
        preset=InstallPreset.CUSTOM,
        routes=("ScanImage", "deeplabcut", "scanimage"),
    )

    assert plan.selection.routes == ("scanimage", "deeplabcut")
    assert plan.extras == ("scanimage", "deeplabcut")


def test_resolve_install_plan_for_rich_viewer_support_target() -> None:
    plan = resolve_install_plan(
        mode=InstallMode.SELECTED,
        preset=InstallPreset.CUSTOM,
        routes=("viewer_rich",),
    )

    assert plan.selection.routes == ("viewer_rich",)
    assert plan.extras == ("viewer_rich",)
    assert plan.editable_requirement == ".[viewer_rich]"


def test_resolve_install_plan_rejects_unknown_route() -> None:
    with pytest.raises(ValueError, match="Unknown install route"):
        resolve_install_plan(
            mode=InstallMode.SELECTED,
            preset=InstallPreset.CUSTOM,
            routes=("unknown-route",),
        )


def test_save_and_load_package_selection_round_trip(tmp_path: Path) -> None:
    plan = resolve_install_plan(mode=InstallMode.FULL)
    state_path = tmp_path / "install-selection.json"

    save_install_plan(state_path, plan)
    loaded = load_package_selection(state_path)

    assert loaded is not None
    assert loaded.mode is InstallMode.FULL
    assert loaded.preset is InstallPreset.FULL
    assert loaded.routes == plan.selection.routes
