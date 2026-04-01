"""Desktop UI settings persistence services."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(frozen=True, slots=True)
class UiSettings:
    """Persisted desktop shell settings."""

    verbose_logging_enabled: bool = False
    file_logging_enabled: bool = False
    log_file_path: Path = Path(".nwbforge/logs/nwbforge-ui.jsonl")


class UiSettingsService:
    """Load and save desktop UI settings from a JSON file."""

    def __init__(self, settings_path: Path) -> None:
        self._settings_path = settings_path

    @property
    def settings_path(self) -> Path:
        return self._settings_path

    def load(self) -> UiSettings:
        if not self._settings_path.exists():
            return UiSettings()

        payload = json.loads(self._settings_path.read_text(encoding="utf-8"))
        return UiSettings(
            verbose_logging_enabled=bool(payload.get("verbose_logging_enabled", False)),
            file_logging_enabled=bool(payload.get("file_logging_enabled", False)),
            log_file_path=Path(payload.get("log_file_path", UiSettings().log_file_path)),
        )

    def save(self, settings: UiSettings) -> UiSettings:
        payload = asdict(settings)
        payload["log_file_path"] = str(settings.log_file_path)
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        self._settings_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return settings
