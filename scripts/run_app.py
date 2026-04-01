"""Temporary desktop launcher for manual NWB Forge UI testing."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from nwbforge.app.desktop import (
    build_default_log_file_path,
    build_desktop_services,
    ensure_demo_manifest,
    load_manifest_session,
)
from nwbforge.ui.qt import MainWindow, ensure_application


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the temporary NWB Forge desktop shell.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Path to a session_manifest.json file or a directory containing it.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    services = build_desktop_services(repo_root)

    manifest_path = args.manifest.resolve() if args.manifest is not None else ensure_demo_manifest(repo_root)
    session = load_manifest_session(manifest_path)

    app = ensure_application()
    window = MainWindow(
        services.shell_model,
        services.settings_screen_model,
        services.package_screen_model,
        services.conversion_screen_model,
        log_file_path=build_default_log_file_path(repo_root),
    )
    window.show()
    window.conversion_widget.load_session(session)
    logging.getLogger("nwbforge.desktop").info(
        "Temporary desktop launcher started.",
        extra={"nwbforge_context": {"session_id": session.session_id, "manifest": str(manifest_path)}},
    )
    try:
        return app.exec()
    finally:
        services.conversion_screen_model.shutdown(wait=False)
        services.package_screen_model.shutdown(wait=False)


if __name__ == "__main__":
    raise SystemExit(main())
