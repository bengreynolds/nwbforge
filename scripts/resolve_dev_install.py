"""Resolve a route-based install plan for the development Conda environment."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nwbforge.app.packages import DEFAULT_SELECTION_PATH, load_package_selection, resolve_install_plan, save_install_plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["minimal", "selected", "full"], default="selected")
    parser.add_argument("--preset", choices=["minimal", "common", "full", "custom"], default="common")
    parser.add_argument("--route", action="append", dest="routes", default=[])
    parser.add_argument("--state-path", default=str(DEFAULT_SELECTION_PATH))
    parser.add_argument("--use-persisted", action="store_true")
    parser.add_argument("--persist", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    state_path = Path(args.state_path)
    if args.use_persisted:
        saved = load_package_selection(state_path)
        if saved is not None:
            plan = resolve_install_plan(
                mode=saved.mode,
                preset=saved.preset,
                routes=saved.routes,
            )
        else:
            plan = resolve_install_plan(mode=args.mode, preset=args.preset, routes=args.routes)
    else:
        plan = resolve_install_plan(mode=args.mode, preset=args.preset, routes=args.routes)

    if args.persist:
        save_install_plan(state_path, plan)

    payload = {
        "mode": plan.selection.mode.value,
        "preset": plan.selection.preset.value,
        "routes": list(plan.selection.routes),
        "extras": list(plan.extras),
        "editable_requirement": plan.editable_requirement,
        "state_path": str(state_path),
    }
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
