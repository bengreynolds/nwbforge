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
