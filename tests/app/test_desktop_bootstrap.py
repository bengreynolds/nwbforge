from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess

from nwbforge.app.desktop import build_adapter_registry, build_desktop_services, ensure_demo_manifest, load_manifest_session


class FakeRunner:
    def run(self, command, *, cwd: Path):
        return CompletedProcess(args=list(command), returncode=0, stdout="ok", stderr="")


def test_build_adapter_registry_includes_manifest_adapter() -> None:
    registry = build_adapter_registry()

    assert "session_manifest" in registry.registered_ids()


def test_desktop_services_run_real_manifest_preview_and_execution(tmp_path: Path) -> None:
    manifest_path = ensure_demo_manifest(tmp_path)
    session = load_manifest_session(manifest_path)
    services = build_desktop_services(tmp_path, package_command_runner=FakeRunner())

    services.conversion_screen_model.load_session(session)
    preview = services.conversion_screen_model.start_preview().result(timeout=10)
    output_path = tmp_path / "outputs" / "session.nwb"
    execution = services.conversion_screen_model.start_execution(output_path).result(timeout=20)

    assert preview.session.status.value in {"ready_to_write", "review"}
    assert execution.session.status.value == "completed"
    assert output_path.exists() is True
    assert execution.validation_summary.is_passing() is True

    services.conversion_screen_model.shutdown(wait=False)
    services.package_screen_model.shutdown(wait=False)
