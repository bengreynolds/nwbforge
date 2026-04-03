from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_internal_smoke_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "run_internal_smoke.py"
    spec = importlib.util.spec_from_file_location("run_internal_smoke", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_internal_smoke_writes_json_report(tmp_path: Path) -> None:
    module = _load_internal_smoke_module()
    report_path = tmp_path / "reports" / "smoke-report.json"
    workspace = tmp_path / "workspace"
    cases = [
        {
            "case_type": "conversion",
            "session_id": "supported-01",
            "result": "passed",
            "workspace": str(workspace / "supported"),
        },
        {
            "case_type": "direct_ingest_project_round_trip",
            "session_id": "project-01",
            "result": "passed",
            "workspace": str(workspace / "project"),
        },
    ]

    module._write_report(report_path, workspace=workspace, cases=cases)

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["workspace"] == str(workspace)
    assert payload["case_count"] == 2
    assert payload["result"] == "passed"
    assert payload["cases"] == cases


def test_internal_smoke_parse_args_accepts_repeated_cases() -> None:
    module = _load_internal_smoke_module()

    args = module.parse_args(["--case", "supported", "--case", "project"])

    assert args.case == ["supported", "project"]


def test_internal_smoke_runs_only_requested_cases(tmp_path: Path, monkeypatch) -> None:
    module = _load_internal_smoke_module()
    invoked: list[str] = []

    def fake_conversion_case(repo_root: Path, workspace: Path, relative_session_path: str, output_name: str):
        invoked.append(output_name)
        return {"case_type": "conversion", "output_path": output_name, "result": "passed"}

    def fake_project_case(repo_root: Path, workspace: Path):
        invoked.append("project")
        return {"case_type": "project", "output_path": "project", "result": "passed"}

    monkeypatch.setattr(module, "_run_conversion_case", fake_conversion_case)
    monkeypatch.setattr(module, "_run_project_round_trip", fake_project_case)

    cases = module._run_smoke_suite(tmp_path, tmp_path / "workspace", case_names=("custom", "project"))

    assert invoked == ["custom-case.nwb", "project"]
    assert len(cases) == 2
