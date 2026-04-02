"""Temporary desktop launcher for manual NWB Forge UI testing."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from nwbforge.app.logging import get_logger, log_event
from nwbforge.app.desktop import (
    build_default_log_file_path,
    build_desktop_services,
    load_desktop_session,
)
from nwbforge.ui import FileMenuAction
from nwbforge.ui.qt import MainWindow, ensure_application


LOGGER = get_logger("nwbforge.desktop")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the temporary NWB Forge desktop shell.")
    parser.add_argument(
        "--session",
        type=Path,
        default=None,
        help="Path to a session_manifest.json, custom_session.json, or hybrid_session.json file, or a directory containing one.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    services = build_desktop_services(repo_root)
    requested_session = args.session or args.manifest

    app = ensure_application()
    window = MainWindow(
        services.shell_model,
        services.settings_screen_model,
        services.package_screen_model,
        services.conversion_screen_model,
        session_assembly_screen_model=services.session_assembly_screen_model,
        log_file_path=build_default_log_file_path(repo_root),
    )
    window.show()
    if requested_session is not None:
        session_path = requested_session.resolve()
        session = load_desktop_session(session_path)
        window.conversion_widget.load_session(session)
        log_event(
            LOGGER,
            logging.INFO,
            "Temporary desktop launcher started with explicit session.",
            session_id=session.session_id,
            session_path=str(session_path),
        )
    else:
        services.shell_model.invoke_file_menu_action(FileMenuAction.NEW_SESSION)
        log_event(
            LOGGER,
            logging.INFO,
            "Temporary desktop launcher started in direct-ingest mode.",
            startup_mode="new_session",
        )
    try:
        return app.exec()
    finally:
        services.conversion_screen_model.shutdown(wait=False)
        services.package_screen_model.shutdown(wait=False)


if __name__ == "__main__":
    raise SystemExit(main())
