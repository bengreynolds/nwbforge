from __future__ import annotations

import json
from pathlib import Path

import pytest

from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.adapters.registry import AdapterRegistry
from nwbforge.app.desktop import build_adapter_registry
from nwbforge.app.services import JsonSessionAssemblyWorkspaceStore, SessionAssemblyService
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import SourceReference
from nwbforge.ui import SessionAssemblyScreenModel


class _WorkflowRouteAdapter:
    version = "0.0.0"
    capabilities = AdapterCapabilities(supported_pathways=(ConversionPathway.SUPPORTED,))

    def __init__(self, adapter_id: str, *, source_type: SourceType) -> None:
        self.adapter_id = adapter_id
        self.display_name = adapter_id
        self.source_types = (source_type,)

    def can_handle(self, source: SourceReference) -> bool:
        return source.adapter_hint == self.adapter_id

    def inspect(self, source: SourceReference):  # pragma: no cover - not used in this test
        raise NotImplementedError


class _TiffSuite2pWorkflowAdapter:
    adapter_id = "workflow_tiff_suite2p"
    display_name = "TIFF + Suite2p Workflow"
    version = "0.0.0"
    capabilities = AdapterCapabilities(
        supported_pathways=(ConversionPathway.SUPPORTED,),
        supports_multi_source_sessions=True,
    )

    def can_handle_sources(self, sources: tuple[SourceReference, ...]) -> bool:
        return self.match_sources(sources) is not None

    def inspect_sources(self, sources: tuple[SourceReference, ...]):  # pragma: no cover - not used in this test
        raise NotImplementedError

    def match_sources(self, sources: tuple[SourceReference, ...]) -> dict[str, SourceReference] | None:
        imaging = [
            source
            for source in sources
            if source.adapter_hint == "neuroconv_tiff_imaging" and source.role == "primary"
        ]
        segmentation = [
            source
            for source in sources
            if source.adapter_hint == "neuroconv_suite2p_segmentation"
        ]
        if len(imaging) != 1 or len(segmentation) != 1:
            return None
        return {"imaging": imaging[0], "segmentation": segmentation[0]}


def _build_workflow_registry() -> AdapterRegistry:
    registry = AdapterRegistry()
    registry.register(_WorkflowRouteAdapter("neuroconv_tiff_imaging", source_type=SourceType.DIRECTORY))
    registry.register(_WorkflowRouteAdapter("neuroconv_suite2p_segmentation", source_type=SourceType.DIRECTORY))
    registry.register_workflow(_TiffSuite2pWorkflowAdapter())
    return registry


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


def test_session_assembly_screen_model_rejects_invalid_supported_entry_selection(
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

    assert state.selected_paths == ()
    assert state.sources == ()
    assert state.error_message is not None
    assert "DeepLabCut" in state.error_message


def test_session_assembly_screen_model_tracks_supported_entry_metadata_for_valid_selection(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    screen = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))

    state = screen.add_supported_paths(
        (manifest_path,),
        route_name="session_manifest",
        route_display_name="Session Manifest",
    )

    assert state.source_intents[str(manifest_path.resolve())]["route_name"] == "session_manifest"
    assert state.source_intents[str(manifest_path.resolve())]["entry_validation_status"] == "validated"
    assert state.sources[0].selection_label == "Session Manifest"
    assert state.sources[0].entry_role_label == "manifest file or session directory"
    assert state.sources[0].entry_validation_status == "validated"
    assert state.can_create_session is True


def test_session_assembly_screen_model_exposes_structured_bundle_summary(tmp_path: Path) -> None:
    thor_file = tmp_path / "Image_0001_0001.tif"
    thor_file.write_text("binary-placeholder", encoding="utf-8")
    (tmp_path / "Experiment.xml").write_text("<Experiment />", encoding="utf-8")
    screen = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))

    state = screen.add_supported_paths(
        (thor_file,),
        route_name="thor",
        route_display_name="Thor",
    )

    assert state.sources[0].structured_bundle_member_count == 2
    assert state.sources[0].structured_bundle_member_labels == ("Experiment.xml", "Image_0001_0001.tif")
    assert state.groups[0].canonical_bundle_member_count == 2
    assert state.groups[0].canonical_bundle_member_labels == ("Experiment.xml", "Image_0001_0001.tif")


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
        route_name="session_manifest",
        route_display_name="Session Manifest",
    )

    restored_screen = SessionAssemblyScreenModel(
        SessionAssemblyService(build_adapter_registry()),
        workspace_store=workspace_store,
    )

    assert restored_screen.state.source_intents[str(manifest_path.resolve())]["route_name"] == "session_manifest"
    assert restored_screen.state.sources[0].selection_label == "Session Manifest"


def test_session_assembly_screen_model_rejects_unsupported_custom_file_type(tmp_path: Path) -> None:
    unsupported_path = tmp_path / "unknown.exe"
    unsupported_path.write_text("not a dataset", encoding="utf-8")
    screen = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))

    state = screen.add_custom_paths((unsupported_path,))

    assert state.selected_paths == ()
    assert state.sources == ()
    assert state.error_message is not None
    assert "unknown.exe" in state.error_message


def test_session_assembly_screen_model_keeps_supported_custom_input_and_reports_rejected_one(tmp_path: Path) -> None:
    notes_path = tmp_path / "notes.txt"
    notes_path.write_text("operator notes", encoding="utf-8")
    unsupported_path = tmp_path / "unknown.exe"
    unsupported_path.write_text("not a dataset", encoding="utf-8")
    screen = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))

    state = screen.add_custom_paths((notes_path, unsupported_path))

    assert state.selected_paths == (notes_path.resolve(),)
    assert len(state.sources) == 1
    assert state.sources[0].selection_label == "Custom"
    assert state.error_message is not None
    assert "unknown.exe" in state.error_message


def test_session_assembly_screen_model_groups_custom_input_under_single_supported_source(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    notes_path = tmp_path / "notes.txt"
    notes_path.write_text("operator notes", encoding="utf-8")
    screen = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))

    screen.add_supported_paths(
        (manifest_path,),
        route_name="session_manifest",
        route_display_name="Session Manifest",
    )
    state = screen.add_custom_paths((notes_path,))

    notes_source = next(source for source in state.sources if source.location == notes_path.resolve())
    manifest_source = next(source for source in state.sources if source.location == manifest_path.resolve())

    assert notes_source.group_key == manifest_source.group_key
    assert notes_source.group_label == manifest_source.group_label
    assert state.groups[0].canonical_source_id == manifest_source.source_id
    assert state.groups[0].canonical_source_label == "session_manifest.json"
    assert state.groups[0].canonical_entry_role_label == "manifest file or session directory"
    assert state.groups[0].canonical_selection_label == "Session Manifest"
    assert any(issue.code == "session-assembly-custom-context-association" for issue in state.issues)


def test_session_assembly_screen_model_flags_ambiguous_custom_context_between_supported_sources(
    tmp_path: Path,
) -> None:
    first_manifest_path = tmp_path / "session_manifest.json"
    first_manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    second_manifest_path = tmp_path / "custom_session.json"
    second_manifest_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")
    notes_path = tmp_path / "notes.txt"
    notes_path.write_text("operator notes", encoding="utf-8")
    screen = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))

    screen.add_supported_paths(
        (first_manifest_path,),
        route_name="session_manifest",
        route_display_name="Session Manifest",
    )
    screen.add_supported_paths(
        (second_manifest_path,),
        route_name="custom_session",
        route_display_name="Custom Session",
    )
    state = screen.add_custom_paths((notes_path,))

    notes_source = next(source for source in state.sources if source.location == notes_path.resolve())

    assert notes_source.context_source_id is None
    assert any(issue.code == "session-assembly-ambiguous-custom-context" for issue in state.issues)


def test_session_assembly_screen_model_surfaces_matched_combined_workflow_group(tmp_path: Path) -> None:
    imaging_dir = tmp_path / "imaging"
    imaging_dir.mkdir()
    (imaging_dir / "plane-01.tif").write_text("binary-placeholder", encoding="utf-8")
    suite2p_dir = tmp_path / "suite2p"
    suite2p_dir.mkdir()
    notes_path = tmp_path / "notes.txt"
    notes_path.write_text("operator notes", encoding="utf-8")
    screen = SessionAssemblyScreenModel(SessionAssemblyService(_build_workflow_registry()))

    screen.add_supported_paths(
        (imaging_dir,),
        route_name="tiff",
        route_display_name="TIFF Imaging",
    )
    screen.add_supported_paths(
        (suite2p_dir,),
        route_name="suite2p",
        route_display_name="Suite2p",
    )
    state = screen.add_custom_paths((notes_path,))

    assert len(state.groups) == 1
    assert state.groups[0].group_kind == "workflow_bundle"
    assert state.groups[0].workflow_adapter_id == "workflow_tiff_suite2p"
    assert state.groups[0].workflow_display_name == "TIFF + Suite2p Workflow"
    assert state.sources[0].workflow_display_name == "TIFF + Suite2p Workflow"
    assert state.sources[1].workflow_display_name == "TIFF + Suite2p Workflow"
    assert state.sources[2].context_label == "TIFF + Suite2p Workflow"


def test_session_assembly_screen_model_absorbs_selected_structured_bundle_member(tmp_path: Path) -> None:
    thor_file = tmp_path / "Image_0001_0001.tif"
    thor_file.write_text("binary-placeholder", encoding="utf-8")
    experiment_xml = tmp_path / "Experiment.xml"
    experiment_xml.write_text("<Experiment />", encoding="utf-8")
    screen = SessionAssemblyScreenModel(SessionAssemblyService(build_adapter_registry()))

    screen.add_supported_paths(
        (thor_file,),
        route_name="thor",
        route_display_name="Thor",
    )
    state = screen.add_custom_paths((experiment_xml,))

    assert state.selected_paths == (thor_file.resolve(), experiment_xml.resolve())
    assert len(state.sources) == 1
    assert state.sources[0].structured_bundle_member_count == 2
    assert any(issue.code == "session-assembly-structured-member-absorbed" for issue in state.issues)
