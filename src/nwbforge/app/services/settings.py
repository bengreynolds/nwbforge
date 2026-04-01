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
    last_open_session_path: Path | None = None
    recent_session_paths: tuple[Path, ...] = ()


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
        recent_paths = tuple(Path(value) for value in payload.get("recent_session_paths", ()))
        last_path = payload.get("last_open_session_path")
        return UiSettings(
            verbose_logging_enabled=bool(payload.get("verbose_logging_enabled", False)),
            file_logging_enabled=bool(payload.get("file_logging_enabled", False)),
            log_file_path=Path(payload.get("log_file_path", UiSettings().log_file_path)),
            last_open_session_path=Path(last_path) if last_path else None,
            recent_session_paths=recent_paths,
        )

    def save(self, settings: UiSettings) -> UiSettings:
        payload = asdict(settings)
        payload["log_file_path"] = str(settings.log_file_path)
        payload["last_open_session_path"] = (
            str(settings.last_open_session_path) if settings.last_open_session_path is not None else None
        )
        payload["recent_session_paths"] = [str(path) for path in settings.recent_session_paths]
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        self._settings_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return settings

    def record_recent_session(self, session_path: Path, *, limit: int = 5) -> UiSettings:
        current = self.load()
        normalized = session_path.resolve()
        recent = [path for path in current.recent_session_paths if path != normalized]
        recent.insert(0, normalized)
        return self.save(
            UiSettings(
                verbose_logging_enabled=current.verbose_logging_enabled,
                file_logging_enabled=current.file_logging_enabled,
                log_file_path=current.log_file_path,
                last_open_session_path=normalized,
                recent_session_paths=tuple(recent[:limit]),
            )
        )
