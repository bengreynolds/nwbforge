from __future__ import annotations

from pathlib import Path

from nwbforge.app.services import UiSettingsService
from nwbforge.ui import SettingsScreenModel


def make_screen_model(tmp_path: Path) -> SettingsScreenModel:
    return SettingsScreenModel(UiSettingsService(tmp_path / "ui-settings.json"))


def test_settings_screen_model_loads_defaults(tmp_path: Path) -> None:
    screen = make_screen_model(tmp_path)

    state = screen.load()

    assert state.verbose_logging_enabled is False
    assert state.file_logging_enabled is False
    assert state.has_unsaved_changes is False


def test_settings_screen_model_saves_updated_settings(tmp_path: Path) -> None:
    screen = make_screen_model(tmp_path)
    screen.load()
    screen.set_verbose_logging_enabled(True)
    screen.set_file_logging_enabled(True)
    screen.set_log_file_path(str(tmp_path / "logs" / "ui.jsonl"))
    screen.set_restore_latest_snapshot_on_load(False)
    screen.set_recent_item_limit(7)
    screen.set_snapshot_history_limit(12)

    state = screen.save()

    assert state.applied_settings.verbose_logging_enabled is True
    assert state.applied_settings.file_logging_enabled is True
    assert state.applied_settings.log_file_path == tmp_path / "logs" / "ui.jsonl"
    assert state.applied_settings.restore_latest_snapshot_on_load is False
    assert state.applied_settings.recent_item_limit == 7
    assert state.applied_settings.snapshot_history_limit == 12
    assert state.has_unsaved_changes is False


def test_settings_screen_model_surfaces_validation_error(tmp_path: Path) -> None:
    screen = make_screen_model(tmp_path)
    screen.load()
    screen.set_file_logging_enabled(True)
    screen.set_log_file_path("")

    state = screen.save()

    assert state.user_error is not None
    assert state.user_error.category == "validation"
    assert "Log file path is required" in state.user_error.message


def test_settings_screen_model_records_recent_session(tmp_path: Path) -> None:
    screen = make_screen_model(tmp_path)
    screen.load()

    state = screen.record_recent_session(tmp_path / "demo" / "session_manifest.json")

    assert state.last_open_session_path.endswith("session_manifest.json")
    assert len(state.recent_session_paths) == 1


def test_settings_screen_model_records_recent_project(tmp_path: Path) -> None:
    screen = make_screen_model(tmp_path)
    screen.load()

    state = screen.record_recent_project(tmp_path / "projects" / "saved.nwbforge-project.json")

    assert state.last_open_project_path.endswith("saved.nwbforge-project.json")
    assert len(state.recent_project_paths) == 1


def test_settings_screen_model_records_output_directory(tmp_path: Path) -> None:
    screen = make_screen_model(tmp_path)
    screen.load()

    state = screen.record_output_directory(tmp_path / "outputs" / "result.nwb")

    assert state.last_output_directory.endswith("outputs")
