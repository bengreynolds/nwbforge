from __future__ import annotations

import json
from pathlib import Path

import pytest

from nwbforge.app.desktop import build_adapter_registry
from nwbforge.app.services import JsonSessionAssemblyWorkspaceStore, SessionAssemblyService
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
    assert state.groups[0].requires_confirmation is False


def test_session_assembly_screen_model_builds_hybrid_draft_and_creates_session(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")
    screen = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))

    state = screen.add_paths((manifest_path, custom_path))
    assert state.can_create_session is False
    state = screen.confirm_all_groups()
    state = screen.set_session_id("hybrid-assembled")
    session = screen.create_session()

    assert state.suggested_pathway == "hybrid"
    assert len(state.groups) == 1
    assert state.groups[0].suggested_pathway == "hybrid"
    assert {source.group_label for source in state.sources} == {tmp_path.name}
    assert session.session_id == "hybrid-assembled"
    assert session.pathway.value == "hybrid"


def test_session_assembly_screen_model_edits_roles_and_metadata_overrides(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")
    screen = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))

    screen.add_paths((manifest_path, custom_path))
    screen.set_source_role("session-manifest", "metadata")
    screen.set_source_role("custom-session", "primary")
    state = screen.set_metadata_override("subject.subject_id", "mouse-override-01")
    state = screen.confirm_all_groups()
    session = screen.create_session()

    assert state.metadata_overrides["subject.subject_id"] == "mouse-override-01"
    assert [source.role for source in state.sources] == ["metadata", "primary"]
    assert session.metadata_overrides["subject.subject_id"] == "mouse-override-01"
    assert [source.role for source in session.sources] == ["metadata", "primary"]


def test_session_assembly_screen_model_edits_source_metadata_overrides(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")
    screen = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))

    screen.add_paths((manifest_path, custom_path))
    state = screen.set_source_metadata_override("custom-session", "subject.subject_id", "source-custom-01")
    state = screen.confirm_all_groups()
    session = screen.create_session()

    assert state.source_metadata_overrides["custom-session"]["subject.subject_id"] == "source-custom-01"
    assert state.sources[1].metadata_overrides["subject.subject_id"] == "source-custom-01"
    assert session.source_metadata_overrides["custom-session"]["subject.subject_id"] == "source-custom-01"


def test_session_assembly_screen_model_edits_group_labels_and_persists_manual_override(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")
    workspace_store = JsonSessionAssemblyWorkspaceStore(tmp_path / "drafts" / "group-draft.json")

    first_screen = SessionAssemblyScreenModel(
        SessionAssemblyService(build_adapter_registry()),
        workspace_store=workspace_store,
    )
    first_screen.add_paths((manifest_path, custom_path))
    first_screen.set_source_group_label("custom-session", "Manual Custom Group")

    restored_screen = SessionAssemblyScreenModel(
        SessionAssemblyService(build_adapter_registry()),
        workspace_store=workspace_store,
    )

    assert [source.group_label for source in restored_screen.state.sources] == [tmp_path.name, "Manual Custom Group"]
    assert {group.group_label for group in restored_screen.state.groups} == {tmp_path.name, "Manual Custom Group"}


def test_session_assembly_screen_model_can_move_multiple_sources_into_named_group(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")
    notes_path = tmp_path / "notes.txt"
    notes_path.write_text("freeform notes", encoding="utf-8")
    screen = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))

    screen.add_paths((manifest_path, custom_path, notes_path))
    state = screen.set_group_label_for_sources(("custom-session", "notes"), "Merged Review Bundle")

    assert state.sources[1].group_label == "Merged Review Bundle"
    assert state.sources[2].group_label == "Merged Review Bundle"
    assert any(group.group_label == "Merged Review Bundle" for group in state.groups)


def test_session_assembly_screen_model_can_confirm_group_and_restore_it(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")
    workspace_store = JsonSessionAssemblyWorkspaceStore(tmp_path / "drafts" / "confirmed-group.json")

    first_screen = SessionAssemblyScreenModel(
        SessionAssemblyService(build_adapter_registry()),
        workspace_store=workspace_store,
    )
    first_state = first_screen.add_paths((manifest_path, custom_path))
    confirmed_state = first_screen.confirm_group(first_state.groups[0].group_key)

    restored_screen = SessionAssemblyScreenModel(
        SessionAssemblyService(build_adapter_registry()),
        workspace_store=workspace_store,
    )

    assert confirmed_state.groups[0].is_confirmed is True
    assert confirmed_state.can_create_session is True
    assert confirmed_state.groups[0].requires_confirmation is True
    assert restored_screen.state.groups[0].is_confirmed is True
    assert not any(issue.code == "session-assembly-auto-grouped-inputs" for issue in restored_screen.state.issues)


def test_session_assembly_screen_model_can_split_selected_sources_into_individual_groups(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")
    notes_path = tmp_path / "notes.txt"
    notes_path.write_text("freeform notes", encoding="utf-8")
    screen = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))

    screen.add_paths((manifest_path, custom_path, notes_path))
    state = screen.split_sources_into_individual_groups(("custom-session", "notes"))

    assert state.sources[1].group_label != state.sources[2].group_label
    assert len({source.group_label for source in state.sources}) == 3


def test_session_assembly_screen_model_can_split_selected_group(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")
    screen = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))

    initial_state = screen.add_paths((manifest_path, custom_path))
    split_state = screen.split_group(initial_state.groups[0].group_key)

    assert len(split_state.groups) == 2
    assert len({source.group_label for source in split_state.sources}) == 2
    assert all(group.group_kind == "manual" for group in split_state.groups)


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


def test_session_assembly_screen_model_restores_persisted_workspace(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    workspace_store = JsonSessionAssemblyWorkspaceStore(tmp_path / "drafts" / "session-draft.json")

    first_screen = SessionAssemblyScreenModel(
        SessionAssemblyService(build_adapter_registry()),
        workspace_store=workspace_store,
    )
    first_screen.add_paths((manifest_path,))
    first_screen.set_source_role("session-manifest", "metadata")
    first_screen.set_metadata_override("subject.subject_id", "persisted-mouse-01")

    restored_screen = SessionAssemblyScreenModel(
        SessionAssemblyService(build_adapter_registry()),
        workspace_store=workspace_store,
    )

    assert restored_screen.state.selected_paths == (manifest_path.resolve(),)
    assert restored_screen.state.sources[0].role == "metadata"
    assert restored_screen.state.metadata_overrides["subject.subject_id"] == "persisted-mouse-01"


def test_session_assembly_screen_model_saves_and_loads_explicit_project(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")
    project_path = tmp_path / "projects" / "session.nwbforge-project.json"

    first_screen = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))
    first_screen.add_paths((manifest_path, custom_path))
    first_screen.set_source_group_label("custom-session", "Manual Custom Group")
    first_screen.set_source_metadata_override("custom-session", "subject.subject_id", "custom-source-01")
    first_screen.confirm_all_groups()
    saved_state = first_screen.save_project(project_path)

    restored_screen = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))
    restored_state = restored_screen.load_project(project_path)

    assert saved_state.project_path == project_path.resolve()
    assert saved_state.has_unsaved_changes is False
    assert restored_state.project_path == project_path.resolve()
    assert restored_state.has_unsaved_changes is False
    assert restored_state.sources[1].group_label == "Manual Custom Group"
    assert restored_state.sources[1].metadata_overrides["subject.subject_id"] == "custom-source-01"
    assert all(group.is_confirmed for group in restored_state.groups)


def test_session_assembly_screen_model_restores_project_path_from_workspace(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    project_path = tmp_path / "projects" / "restored.nwbforge-project.json"
    workspace_store = JsonSessionAssemblyWorkspaceStore(tmp_path / "drafts" / "session-draft.json")

    first_screen = SessionAssemblyScreenModel(
        SessionAssemblyService(build_adapter_registry()),
        workspace_store=workspace_store,
    )
    first_screen.add_paths((manifest_path,))
    first_screen.save_project(project_path)

    restored_screen = SessionAssemblyScreenModel(
        SessionAssemblyService(build_adapter_registry()),
        workspace_store=workspace_store,
    )

    assert restored_screen.state.project_path == project_path.resolve()
    assert restored_screen.state.has_unsaved_changes is False


def test_session_assembly_screen_model_exposes_custom_source_option() -> None:
    screen = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))

    assert screen.state.source_type_options
    assert screen.state.source_type_options[0].ingest_kind == "custom"
    assert screen.state.source_type_options[0].label == "Custom"


def test_session_assembly_screen_model_tracks_supported_source_intent_and_blocks_route_mismatch(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    screen = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))

    state = screen.add_supported_paths(
        (manifest_path,),
        route_name="deeplabcut",
        route_display_name="DeepLabCut",
    )

    assert state.source_intents[str(manifest_path.resolve())]["route_name"] == "deeplabcut"
    assert state.sources[0].selection_label == "DeepLabCut"
    assert state.can_create_session is False
    assert any(issue.code == "session-assembly-selected-route-mismatch" for issue in state.issues)


def test_session_assembly_screen_model_persists_supported_source_intent_in_workspace(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    workspace_store = JsonSessionAssemblyWorkspaceStore(tmp_path / "drafts" / "route-draft.json")

    first_screen = SessionAssemblyScreenModel(
        SessionAssemblyService(build_adapter_registry()),
        workspace_store=workspace_store,
    )
    first_screen.add_supported_paths(
        (manifest_path,),
        route_name="deeplabcut",
        route_display_name="DeepLabCut",
    )

    restored_screen = SessionAssemblyScreenModel(
        SessionAssemblyService(build_adapter_registry()),
        workspace_store=workspace_store,
    )

    assert restored_screen.state.source_intents[str(manifest_path.resolve())]["route_name"] == "deeplabcut"
    assert restored_screen.state.sources[0].selection_label == "DeepLabCut"
