from __future__ import annotations

from nwbforge.app.packages import PackageInstallProgressEvent, PackageInstallRuntimeError, PackageInstallStage
from nwbforge.app.runtime import PipelineProgressEvent, PipelineRuntimeError, PipelineStage
from nwbforge.ui import DesktopShellModel, FileMenuAction


def test_desktop_shell_model_handles_file_menu_actions() -> None:
    shell = DesktopShellModel()

    shell.invoke_file_menu_action(FileMenuAction.INSTALL_PACKAGES)
    assert shell.state.active_dialog == "install_packages"

    shell.invoke_file_menu_action(FileMenuAction.TOGGLE_LOG_VIEWER)
    assert shell.state.is_log_viewer_visible is True
    assert shell.state.active_dialog is None

    shell.invoke_file_menu_action(FileMenuAction.SETTINGS)
    assert shell.state.active_dialog == "settings"


def test_desktop_shell_model_applies_pipeline_progress_and_errors() -> None:
    shell = DesktopShellModel()

    shell.apply_pipeline_progress(
        PipelineProgressEvent(
            session_id="session-1",
            stage=PipelineStage.MAPPING,
            percent_complete=55,
            message="Building NWB mapping plan.",
        )
    )
    assert shell.state.status_bar.stage_key == "mapping"
    assert shell.state.status_bar.is_busy is True

    shell.apply_pipeline_error(
        PipelineRuntimeError(
            stage=PipelineStage.FAILED,
            user_message="Conversion failed.",
            session_id="session-1",
        )
    )
    assert shell.state.status_bar.is_error is True
    assert shell.state.status_bar.message == "Conversion failed."


def test_desktop_shell_model_applies_package_progress_and_errors() -> None:
    shell = DesktopShellModel()

    shell.apply_package_progress(
        PackageInstallProgressEvent(
            stage=PackageInstallStage.INSTALLING,
            percent_complete=50,
            message="Installing selected route packages.",
            route_names=("deeplabcut",),
        )
    )
    assert shell.state.status_bar.stage_key == "packages:installing"
    assert shell.state.status_bar.is_busy is True

    shell.apply_package_error(
        PackageInstallRuntimeError(
            stage=PackageInstallStage.FAILED,
            user_message="Package installation failed.",
            route_names=("deeplabcut",),
        )
    )
    assert shell.state.status_bar.is_error is True
    assert shell.state.status_bar.message == "Package installation failed."
