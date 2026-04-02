from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess

from nwbforge.app.desktop import (
    build_adapter_registry,
    build_desktop_services,
    ensure_demo_manifest,
    load_custom_session,
    load_desktop_session,
    load_hybrid_session,
    load_manifest_session,
    resolve_startup_session_path,
)
from nwbforge.app.services import UiSettings


class FakeRunner:
    def run(self, command, *, cwd: Path):
        return CompletedProcess(args=list(command), returncode=0, stdout="ok", stderr="")


def test_build_adapter_registry_includes_manifest_adapter() -> None:
    registry = build_adapter_registry()

    assert "session_manifest" in registry.registered_ids()
    assert "custom_json_session" in registry.registered_ids()


def test_build_adapter_registry_applies_route_dependency_gates(monkeypatch) -> None:
    monkeypatch.setattr(
        "nwbforge.app.desktop.route_dependencies_available",
        lambda route_name: route_name == "excel",
    )

    registry = build_adapter_registry()
    registered = set(registry.registered_ids())

    assert "neuroconv_excel_time_intervals" in registered
    assert "neuroconv_deeplabcut" not in registered
    assert "neuroconv_lightningpose" not in registered
    assert "neuroconv_audio" not in registered
    assert "neuroconv_image" not in registered
    assert "neuroconv_video" not in registered
    assert "neuroconv_sleap" not in registered
    assert "neuroconv_hdf5_imaging" not in registered
    assert "neuroconv_scanimage" not in registered


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
    assert (
        tmp_path
        / ".nwbforge"
        / "session-state"
        / execution.session.session_id
        / "session-state.json"
    ).exists() is True

    services.conversion_screen_model.shutdown(wait=False)
    services.package_screen_model.shutdown(wait=False)

    recovered_services = build_desktop_services(tmp_path, package_command_runner=FakeRunner())
    recovered_services.conversion_screen_model.load_session(session)

    assert recovered_services.conversion_screen_model.state.recovery_message == "Recovered latest saved session state."
    assert recovered_services.conversion_screen_model.state.generated_artifacts
    assert recovered_services.conversion_screen_model.state.output_path == output_path

    recovered_services.conversion_screen_model.shutdown(wait=False)
    recovered_services.package_screen_model.shutdown(wait=False)


def test_desktop_services_run_real_custom_preview_and_execution(tmp_path: Path) -> None:
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(
        """
        {
          "recording_context": {
            "recording_id": "custom-desktop-01",
            "summary": "Custom desktop workflow test",
            "study_description": "Custom-path desktop test",
            "started_at": "2026-04-01T09:00:00-06:00",
            "operator_name": "NWB Forge Demo",
            "institute_name": "Test Lab"
          },
          "animal_profile": {
            "identifier": "custom-mouse-01",
            "species_name": "Mus musculus",
            "sex_code": "U",
            "life_stage": "P90D",
            "birth_date": "2025-12-31T00:00:00-07:00",
            "notes": "Custom desktop subject"
          },
          "signal_sets": [
            {
              "stream_key": "wheel-velocity",
              "name": "Wheel Velocity",
              "modality": "behavior",
              "description": "Custom wheel trace",
              "data": [0.0, 0.3, 0.1],
              "unit": "cm/s",
              "rate": 20.0
            }
          ],
          "annotations": {
            "keywords": ["custom", "desktop"],
            "operator_note": "Review the custom acquisition context."
          }
        }
        """,
        encoding="utf-8",
    )
    session = load_custom_session(custom_path)
    services = build_desktop_services(tmp_path, package_command_runner=FakeRunner())

    services.conversion_screen_model.load_session(session)
    preview = services.conversion_screen_model.start_preview().result(timeout=10)
    output_path = tmp_path / "outputs" / "custom-session.nwb"
    execution = services.conversion_screen_model.start_execution(output_path).result(timeout=20)

    assert preview.session.status.value == "review"
    assert preview.provenance_record.adapter_ids == ("custom_json_session",)
    assert execution.session.status.value == "completed"
    assert output_path.exists() is True
    assert execution.validation_summary.is_passing() is True

    services.conversion_screen_model.shutdown(wait=False)
    services.package_screen_model.shutdown(wait=False)


def test_load_desktop_session_dispatches_between_supported_and_custom(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text('{"session": {"session_id": "supported-01"}}', encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text('{"recording_context": {"recording_id": "custom-01"}}', encoding="utf-8")
    hybrid_path = tmp_path / "hybrid_session.json"
    hybrid_path.write_text(
        """
        {
          "session_id": "desktop-hybrid-01",
          "sources": [
            {"source_id": "manifest", "location": "session_manifest.json", "label": "Session manifest"},
            {"source_id": "custom", "location": "custom_session.json", "label": "Custom session JSON", "adapter_hint": "custom_json_session", "role": "supplemental"}
          ]
        }
        """,
        encoding="utf-8",
    )

    supported_session = load_desktop_session(manifest_path)
    custom_session = load_desktop_session(custom_path)
    hybrid_session = load_desktop_session(hybrid_path)

    assert supported_session.pathway.value == "supported"
    assert custom_session.pathway.value == "custom"
    assert hybrid_session.pathway.value == "hybrid"


def test_desktop_services_run_real_hybrid_preview_and_execution(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(
        """
        {
          "session": {
            "session_id": "desktop-hybrid-manifest-01",
            "description": "Hybrid desktop manifest metadata",
            "experiment_description": "Hybrid desktop workflow test",
            "start_time": "2026-04-01T09:00:00-06:00",
            "experimenter": "NWB Forge Demo",
            "institution": "Test Lab"
          },
          "subject": {
            "subject_id": "desktop-hybrid-mouse-01",
            "species": "Mus musculus",
            "sex": "U",
            "age": "P90D",
            "description": "Hybrid desktop subject"
          },
          "acquisition_streams": [
            {
              "stream_id": "lick-trace",
              "name": "Lick Trace",
              "modality": "behavior",
              "description": "Example lick signal",
              "data": [0.1, 0.2, 0.3],
              "unit": "a.u.",
              "rate": 10.0
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(
        """
        {
          "signal_sets": [
            {
              "stream_key": "wheel-velocity",
              "name": "Wheel Velocity",
              "modality": "behavior",
              "description": "Custom wheel trace",
              "data": [0.0, 0.3, 0.1],
              "unit": "cm/s",
              "rate": 20.0
            }
          ],
          "annotations": {
            "operator_note": "Review the custom hybrid context."
          }
        }
        """,
        encoding="utf-8",
    )
    hybrid_path = tmp_path / "hybrid_session.json"
    hybrid_path.write_text(
        """
        {
          "session_id": "desktop-hybrid-01",
          "title": "Hybrid desktop workflow test",
          "sources": [
            {"source_id": "manifest", "location": "session_manifest.json", "label": "Session manifest"},
            {"source_id": "custom", "location": "custom_session.json", "label": "Custom supplemental source", "adapter_hint": "custom_json_session", "role": "supplemental"}
          ]
        }
        """,
        encoding="utf-8",
    )
    session = load_hybrid_session(hybrid_path)
    services = build_desktop_services(tmp_path, package_command_runner=FakeRunner())

    services.conversion_screen_model.load_session(session)
    preview = services.conversion_screen_model.start_preview().result(timeout=10)
    output_path = tmp_path / "outputs" / "hybrid-session.nwb"
    execution = services.conversion_screen_model.start_execution(output_path).result(timeout=20)

    assert preview.session.pathway.value == "hybrid"
    assert preview.session.status.value == "review"
    assert preview.provenance_record.adapter_ids == ("custom_json_session", "session_manifest")
    assert execution.session.status.value == "completed"
    assert output_path.exists() is True
    assert execution.validation_summary.is_passing() is True

    services.conversion_screen_model.shutdown(wait=False)
    services.package_screen_model.shutdown(wait=False)


def test_resolve_startup_session_path_prefers_requested_then_saved_then_demo(tmp_path: Path) -> None:
    requested = tmp_path / "requested" / "session_manifest.json"
    requested.parent.mkdir(parents=True)
    requested.write_text("{}", encoding="utf-8")

    saved = tmp_path / "saved" / "session_manifest.json"
    saved.parent.mkdir(parents=True)
    saved.write_text("{}", encoding="utf-8")

    result_requested = resolve_startup_session_path(
        tmp_path,
        UiSettings(last_open_session_path=saved),
        requested_manifest=requested,
    )
    result_saved = resolve_startup_session_path(tmp_path, UiSettings(last_open_session_path=saved))
    result_demo = resolve_startup_session_path(tmp_path, UiSettings())

    assert result_requested == requested.resolve()
    assert result_saved == saved
    assert result_demo.name == "session_manifest.json"


def test_checked_in_example_sessions_load() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    supported = load_desktop_session(repo_root / "examples" / "sessions" / "supported" / "session_manifest.json")
    custom = load_desktop_session(repo_root / "examples" / "sessions" / "custom" / "custom_session.json")
    hybrid = load_desktop_session(repo_root / "examples" / "sessions" / "hybrid" / "hybrid_session.json")

    assert supported.pathway.value == "supported"
    assert custom.pathway.value == "custom"
    assert hybrid.pathway.value == "hybrid"
    assert len(hybrid.sources) == 2
