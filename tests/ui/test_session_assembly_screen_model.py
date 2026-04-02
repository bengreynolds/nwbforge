from __future__ import annotations

import json
from pathlib import Path

import pytest

from nwbforge.app.desktop import build_adapter_registry
from nwbforge.app.services import SessionAssemblyService
from nwbforge.ui import SessionAssemblyScreenModel


def test_session_assembly_screen_model_builds_supported_draft(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    screen = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))

    state = screen.add_paths((manifest_path,))

    assert state.can_create_session is True
    assert state.suggested_pathway == "supported"
    assert state.session_id.startswith("session-")
    assert state.sources[0].suggested_adapter_id == "session_manifest"


def test_session_assembly_screen_model_builds_hybrid_draft_and_creates_session(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")
    screen = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))

    screen.add_paths((manifest_path, custom_path))
    screen.set_session_id("hybrid-assembled")
    session = screen.create_session()

    assert screen.state.suggested_pathway == "hybrid"
    assert session.session_id == "hybrid-assembled"
    assert session.pathway.value == "hybrid"


def test_session_assembly_screen_model_surfaces_unmatched_input(tmp_path: Path) -> None:
    unknown_path = tmp_path / "notes.txt"
    unknown_path.write_text("freeform notes", encoding="utf-8")
    screen = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))

    state = screen.add_paths((unknown_path,))

    assert state.suggested_pathway == "custom"
    assert len(state.issues) == 1
    assert state.issues[0].code == "session-assembly-no-adapter-match"


def test_session_assembly_screen_model_remove_and_reset(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")
    screen = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))

    screen.add_paths((manifest_path, custom_path))
    remove_state = screen.remove_paths((custom_path,))
    reset_state = screen.reset()

    assert len(remove_state.sources) == 1
    assert remove_state.suggested_pathway == "supported"
    assert reset_state.sources == ()
    assert reset_state.selected_paths == ()


def test_session_assembly_screen_model_requires_draft_before_create() -> None:
    screen = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))

    with pytest.raises(ValueError, match="requires at least one selected input"):
        screen.create_session()
