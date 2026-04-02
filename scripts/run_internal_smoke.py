"""Run a focused local smoke test over the real desktop/backend stack."""

from __future__ import annotations

import argparse
from contextlib import suppress
import logging
from pathlib import Path
import tempfile

from nwbforge.app.desktop import build_desktop_services, load_desktop_session


LOGGER = logging.getLogger("nwbforge.internal_smoke")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run NWB Forge internal local smoke checks.")
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Optional workspace directory to reuse instead of a temporary directory.",
    )
    return parser.parse_args()


def _run_conversion_case(repo_root: Path, workspace: Path, relative_session_path: str, output_name: str) -> None:
    services = build_desktop_services(workspace)
    try:
        session_path = (repo_root / relative_session_path).resolve()
        session = load_desktop_session(session_path)
        LOGGER.info("Running smoke conversion case.", extra={"nwbforge_context": {"session_id": session.session_id}})
        services.conversion_screen_model.load_session(session)
        preview = services.conversion_screen_model.start_preview().result(timeout=30)
        output_path = workspace / "outputs" / output_name
        execution = services.conversion_screen_model.start_execution(output_path).result(timeout=60)
        if not output_path.exists():
            raise RuntimeError(f"Expected smoke output to exist: {output_path}")
        if execution.session.status.value != "completed":
            raise RuntimeError(f"Smoke execution did not complete for {session.session_id}")
        LOGGER.info(
            "Completed smoke conversion case.",
            extra={
                "nwbforge_context": {
                    "session_id": session.session_id,
                    "preview_status": preview.session.status.value,
                    "execution_status": execution.session.status.value,
                    "output_path": str(output_path),
                }
            },
        )
    finally:
        services.conversion_screen_model.shutdown(wait=False)
        services.package_screen_model.shutdown(wait=False)


def _run_project_round_trip(repo_root: Path, workspace: Path) -> None:
    services = build_desktop_services(workspace)
    try:
        screen = services.session_assembly_screen_model
        supported = (repo_root / "examples" / "sessions" / "supported" / "session_manifest.json").resolve()
        custom = (repo_root / "examples" / "sessions" / "custom" / "custom_session.json").resolve()
        project_path = workspace / "projects" / "direct-ingest-smoke.nwbforge-project.json"

        screen.add_paths((supported, custom))
        screen.set_source_role("session-manifest", "metadata")
        screen.set_source_role("custom-session", "primary")
        screen.set_source_group_label("custom-session", "Custom Metadata Bundle")
        screen.set_source_metadata_override("custom-session", "subject.subject_id", "smoke-custom-source-01")
        screen.set_metadata_override("subject.species", "Mus musculus")
        saved_state = screen.save_project(project_path)
        if saved_state.project_path != project_path.resolve():
            raise RuntimeError("Project save did not record the expected project path.")

        restored_state = screen.load_project(project_path)
        if restored_state.sources[1].metadata_overrides.get("subject.subject_id") != "smoke-custom-source-01":
            raise RuntimeError("Project reload did not restore source-specific overrides.")

        session = screen.create_session()
        services.conversion_screen_model.load_session(session)
        preview = services.conversion_screen_model.start_preview().result(timeout=30)
        output_path = workspace / "outputs" / "direct-ingest-project.nwb"
        execution = services.conversion_screen_model.start_execution(output_path).result(timeout=60)
        if not output_path.exists():
            raise RuntimeError(f"Expected project smoke output to exist: {output_path}")
        LOGGER.info(
            "Completed project round-trip smoke case.",
            extra={
                "nwbforge_context": {
                    "session_id": session.session_id,
                    "preview_status": preview.session.status.value,
                    "execution_status": execution.session.status.value,
                    "project_path": str(project_path),
                }
            },
        )
    finally:
        services.conversion_screen_model.shutdown(wait=False)
        services.package_screen_model.shutdown(wait=False)


def _run_smoke_suite(repo_root: Path, workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    _run_conversion_case(
        repo_root,
        workspace / "supported-case",
        "examples/sessions/supported/session_manifest.json",
        "supported-case.nwb",
    )
    _run_conversion_case(
        repo_root,
        workspace / "custom-case",
        "examples/sessions/custom/custom_session.json",
        "custom-case.nwb",
    )
    _run_conversion_case(
        repo_root,
        workspace / "hybrid-case",
        "examples/sessions/hybrid/hybrid_session.json",
        "hybrid-case.nwb",
    )
    _run_project_round_trip(repo_root, workspace / "project-case")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    if args.workspace is not None:
        workspace = args.workspace.resolve()
        LOGGER.info("Running internal smoke suite.", extra={"nwbforge_context": {"workspace": str(workspace)}})
        _run_smoke_suite(repo_root, workspace)
        return 0

    with tempfile.TemporaryDirectory(prefix="nwbforge-smoke-") as temp_dir:
        workspace = Path(temp_dir)
        LOGGER.info("Running internal smoke suite.", extra={"nwbforge_context": {"workspace": str(workspace)}})
        _run_smoke_suite(repo_root, workspace)
        with suppress(OSError):
            LOGGER.info("Internal smoke suite finished successfully.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
