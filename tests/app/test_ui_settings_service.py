from __future__ import annotations

from pathlib import Path

from nwbforge.app.services import UiSettings, UiSettingsService


def test_ui_settings_service_loads_defaults_when_missing(tmp_path: Path) -> None:
    service = UiSettingsService(tmp_path / "ui-settings.json")

    settings = service.load()

    assert settings.verbose_logging_enabled is False
    assert settings.file_logging_enabled is False
    assert settings.log_file_path == Path(".nwbforge/logs/nwbforge-ui.jsonl")


def test_ui_settings_service_round_trips_saved_settings(tmp_path: Path) -> None:
    service = UiSettingsService(tmp_path / "ui-settings.json")
    saved = service.save(
        UiSettings(
            verbose_logging_enabled=True,
            file_logging_enabled=True,
            log_file_path=tmp_path / "logs" / "desktop.jsonl",
        )
    )

    loaded = service.load()

    assert loaded == saved


def test_ui_settings_service_records_recent_sessions(tmp_path: Path) -> None:
    service = UiSettingsService(tmp_path / "ui-settings.json")

    first = service.record_recent_session(tmp_path / "a" / "session_manifest.json")
    second = service.record_recent_session(tmp_path / "b" / "session_manifest.json")
    third = service.record_recent_session(tmp_path / "a" / "session_manifest.json")

    assert first.last_open_session_path is not None
    assert second.last_open_session_path == (tmp_path / "b" / "session_manifest.json").resolve()
    assert third.recent_session_paths[0] == (tmp_path / "a" / "session_manifest.json").resolve()
    assert third.recent_session_paths[1] == (tmp_path / "b" / "session_manifest.json").resolve()
