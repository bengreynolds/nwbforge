"""Run a focused local smoke test over the real desktop/backend stack."""

from __future__ import annotations

import argparse
from contextlib import suppress
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import shutil
import tempfile

from nwbforge.app.desktop import build_desktop_services, load_desktop_session


LOGGER = logging.getLogger("nwbforge.internal_smoke")
CASE_NAMES = ("supported", "custom", "hybrid", "project")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run NWB Forge internal local smoke checks.")
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Optional workspace directory to reuse instead of a temporary directory.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=None,
        help="Optional path for a JSON smoke summary report.",
    )
    parser.add_argument(
        "--report-markdown",
        type=Path,
        default=None,
        help="Optional path for a Markdown triage summary.",
    )
    parser.add_argument(
        "--case",
        action="append",
        choices=CASE_NAMES,
        default=None,
        help="Run only the named smoke case. Repeat to run multiple focused cases.",
    )
    return parser.parse_args(argv)


def _run_conversion_case(repo_root: Path, workspace: Path, relative_session_path: str, output_name: str) -> dict[str, str]:
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
        return {
            "case_type": "conversion",
            "session_id": session.session_id,
            "session_path": str(session_path),
            "workspace": str(workspace),
            "preview_status": preview.session.status.value,
            "execution_status": execution.session.status.value,
            "output_path": str(output_path),
            "result": "passed",
        }
    finally:
        services.conversion_screen_model.shutdown(wait=False)
        services.package_screen_model.shutdown(wait=False)


def _run_project_round_trip(repo_root: Path, workspace: Path) -> dict[str, str]:
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
        return {
            "case_type": "direct_ingest_project_round_trip",
            "session_id": session.session_id,
            "supported_input": str(supported),
            "custom_input": str(custom),
            "project_path": str(project_path),
            "workspace": str(workspace),
            "preview_status": preview.session.status.value,
            "execution_status": execution.session.status.value,
            "output_path": str(output_path),
            "result": "passed",
        }
    finally:
        services.conversion_screen_model.shutdown(wait=False)
        services.package_screen_model.shutdown(wait=False)


def _run_smoke_suite(
    repo_root: Path,
    workspace: Path,
    *,
    case_names: tuple[str, ...] | None = None,
) -> list[dict[str, str]]:
    workspace.mkdir(parents=True, exist_ok=True)
    requested = case_names or CASE_NAMES
    cases: list[dict[str, str]] = []
    for case_name in requested:
        if case_name == "supported":
            cases.append(
                _run_conversion_case(
                    repo_root,
                    workspace / "supported-case",
                    "examples/sessions/supported/session_manifest.json",
                    "supported-case.nwb",
                )
            )
        elif case_name == "custom":
            cases.append(
                _run_conversion_case(
                    repo_root,
                    workspace / "custom-case",
                    "examples/sessions/custom/custom_session.json",
                    "custom-case.nwb",
                )
            )
        elif case_name == "hybrid":
            cases.append(
                _run_conversion_case(
                    repo_root,
                    workspace / "hybrid-case",
                    "examples/sessions/hybrid/hybrid_session.json",
                    "hybrid-case.nwb",
                )
            )
        elif case_name == "project":
            cases.append(_run_project_round_trip(repo_root, workspace / "project-case"))
    return cases


def _write_report(report_path: Path, *, workspace: Path, cases: list[dict[str, str]]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "workspace": str(workspace),
        "case_count": len(cases),
        "result": "passed",
        "cases": cases,
    }
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_markdown_report(report_path: Path, *, workspace: Path, cases: list[dict[str, str]]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Internal Smoke Triage Record",
        "",
        f"- Generated at: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- Workspace: `{workspace}`",
        f"- Case count: {len(cases)}",
        "- Overall result: `passed`",
        "",
        "## Cases",
        "",
    ]
    for case in cases:
        case_name = case.get("session_id") or case.get("case_type") or "unknown"
        case_result = case.get("result", "unknown")
        case_workspace = case.get("workspace", "")
        output_path = case.get("output_path", "")
        lines.extend(
            [
                f"### {case_name}",
                f"- Result: `{case_result}`",
                f"- Type: `{case.get('case_type', 'unknown')}`",
                f"- Workspace: `{case_workspace}`" if case_workspace else "- Workspace: n/a",
                f"- Output: `{output_path}`" if output_path else "- Output: n/a",
                "",
            ]
        )
    lines.extend(
        [
            "## Triage",
            "",
            "Blocking:",
            "- None recorded yet.",
            "",
            "Non-blocking:",
            "- None recorded yet.",
            "",
            "Follow-up:",
            "- Representative local datasets still need to be run outside the checked-in smoke fixtures.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def _cleanup_temporary_workspace(workspace: Path) -> None:
    try:
        shutil.rmtree(workspace)
    except OSError:
        LOGGER.warning("Could not fully remove temporary smoke workspace.", extra={"nwbforge_context": {"workspace": str(workspace)}})


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    if args.workspace is not None:
        workspace = args.workspace.resolve()
        LOGGER.info("Running internal smoke suite.", extra={"nwbforge_context": {"workspace": str(workspace)}})
        cases = _run_smoke_suite(repo_root, workspace, case_names=tuple(args.case) if args.case else None)
        if args.report_json is not None:
            _write_report(args.report_json.resolve(), workspace=workspace, cases=cases)
        if args.report_markdown is not None:
            _write_markdown_report(args.report_markdown.resolve(), workspace=workspace, cases=cases)
        return 0

    workspace = Path(tempfile.mkdtemp(prefix="nwbforge-smoke-"))
    try:
        LOGGER.info("Running internal smoke suite.", extra={"nwbforge_context": {"workspace": str(workspace)}})
        cases = _run_smoke_suite(repo_root, workspace, case_names=tuple(args.case) if args.case else None)
        if args.report_json is not None:
            _write_report(args.report_json.resolve(), workspace=workspace, cases=cases)
        if args.report_markdown is not None:
            _write_markdown_report(args.report_markdown.resolve(), workspace=workspace, cases=cases)
        with suppress(OSError):
            LOGGER.info("Internal smoke suite finished successfully.")
        return 0
    finally:
        _cleanup_temporary_workspace(workspace)


if __name__ == "__main__":
    raise SystemExit(main())
