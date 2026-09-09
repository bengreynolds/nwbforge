from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("neuroconv")

from nwbforge.adapters.base import AdapterCapabilities
from nwbforge.adapters.registry import AdapterRegistry
from nwbforge.app.desktop import build_adapter_registry
from nwbforge.app.services import SessionAssemblyService
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import SourceReference


class _AlwaysMatchingAdapter:
    adapter_id = "neuroconv_brukertiff_singleplane"
    display_name = "Test Bruker Adapter"
    version = "0.0.0"
    source_types = (SourceType.FILE,)
    capabilities = AdapterCapabilities(supported_pathways=(ConversionPathway.SUPPORTED,))

    def can_handle(self, source: SourceReference) -> bool:
        return source.source_type is SourceType.FILE and source.location.suffix.lower() == ".tif"

    def inspect(self, source: SourceReference):  # pragma: no cover - not used in this test
        raise NotImplementedError


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
        return {
            "imaging": imaging[0],
            "segmentation": segmentation[0],
        }


def _build_workflow_registry() -> AdapterRegistry:
    registry = AdapterRegistry()
    registry.register(_WorkflowRouteAdapter("neuroconv_tiff_imaging", source_type=SourceType.DIRECTORY))
    registry.register(_WorkflowRouteAdapter("neuroconv_suite2p_segmentation", source_type=SourceType.DIRECTORY))
    registry.register_workflow(_TiffSuite2pWorkflowAdapter())
    return registry


def test_session_assembly_service_builds_supported_manifest_session(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")

    service = SessionAssemblyService(build_adapter_registry())
    draft = service.assemble_draft((manifest_path,))
    session = service.create_session(draft)

    assert draft.pathway.value == "supported"
    assert draft.can_create_session is True
    assert len(draft.sources) == 1
    assert draft.sources[0].suggested_adapter_id == "session_manifest"
    assert session.pathway.value == "supported"
    assert session.sources[0].adapter_hint == "session_manifest"
    assert session.status.value == "sources_added"


def test_session_assembly_service_builds_hybrid_session_from_supported_and_custom(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")

    service = SessionAssemblyService(build_adapter_registry())
    unconfirmed_draft = service.assemble_draft((manifest_path, custom_path), session_id="hybrid-test")
    draft = service.assemble_draft(
        (manifest_path, custom_path),
        session_id="hybrid-test",
        confirmed_group_keys=(unconfirmed_draft.groups[0].group_key,),
    )
    session = service.create_session(draft)

    assert unconfirmed_draft.can_create_session is False
    assert draft.pathway.value == "hybrid"
    assert len(draft.groups) == 1
    assert draft.groups[0].suggested_pathway.value == "hybrid"
    assert draft.groups[0].source_count == 2
    assert draft.groups[0].requires_confirmation is True
    assert session.pathway.value == "hybrid"
    assert len(session.sources) == 2
    assert {source.adapter_hint for source in session.sources} == {"session_manifest", "custom_json_session"}
    assert {source.metadata["session_assembly.group_label"] for source in session.sources} == {tmp_path.name}


def test_session_assembly_service_preserves_roles_and_metadata_overrides(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")

    service = SessionAssemblyService(build_adapter_registry())
    initial_draft = service.assemble_draft(
        (manifest_path, custom_path),
        source_roles={
            "session-manifest": "metadata",
            "custom-session": "primary",
        },
        metadata_overrides={
            "subject.subject_id": "override-mouse-01",
            "subject.species": "Mus musculus",
        },
    )
    draft = service.assemble_draft(
        (manifest_path, custom_path),
        source_roles={
            "session-manifest": "metadata",
            "custom-session": "primary",
        },
        metadata_overrides={
            "subject.subject_id": "override-mouse-01",
            "subject.species": "Mus musculus",
        },
        confirmed_group_keys=(initial_draft.groups[0].group_key,),
    )
    session = service.create_session(draft)

    assert [source.role for source in draft.sources] == ["metadata", "primary"]
    assert [source.role for source in session.sources] == ["metadata", "primary"]
    assert session.metadata_overrides == {
        "subject.subject_id": "override-mouse-01",
        "subject.species": "Mus musculus",
    }


def test_session_assembly_service_preserves_source_metadata_overrides(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")

    service = SessionAssemblyService(build_adapter_registry())
    initial_draft = service.assemble_draft(
        (manifest_path, custom_path),
        source_metadata_overrides={
            "session-manifest": {"subject.subject_id": "manifest-mouse-01"},
            "custom-session": {"subject.subject_id": "custom-mouse-01"},
        },
    )
    draft = service.assemble_draft(
        (manifest_path, custom_path),
        source_metadata_overrides={
            "session-manifest": {"subject.subject_id": "manifest-mouse-01"},
            "custom-session": {"subject.subject_id": "custom-mouse-01"},
        },
        confirmed_group_keys=(initial_draft.groups[0].group_key,),
    )
    session = service.create_session(draft)

    assert draft.source_metadata_overrides["session-manifest"]["subject.subject_id"] == "manifest-mouse-01"
    assert draft.sources[0].metadata_overrides["subject.subject_id"] == "manifest-mouse-01"
    assert session.source_metadata_overrides["custom-session"]["subject.subject_id"] == "custom-mouse-01"


def test_session_assembly_service_treats_unmatched_source_as_custom_review(tmp_path: Path) -> None:
    unknown_path = tmp_path / "notes.txt"
    unknown_path.write_text("freeform operator notes", encoding="utf-8")

    service = SessionAssemblyService(build_adapter_registry())
    draft = service.assemble_draft((unknown_path,))
    session = service.create_session(draft)

    assert draft.pathway.value == "custom"
    assert len(draft.issues) == 1
    assert draft.issues[0].code == "session-assembly-no-adapter-match"
    assert draft.sources[0].suggested_adapter_id is None
    assert draft.sources[0].needs_review is True
    assert session.pathway.value == "custom"


def test_session_assembly_service_emits_auto_grouping_issue_for_shared_folder(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")

    draft = SessionAssemblyService(build_adapter_registry()).assemble_draft((manifest_path, custom_path))

    assert all(source.group_label == tmp_path.name for source in draft.sources)
    assert any(issue.code == "session-assembly-auto-grouped-inputs" for issue in draft.issues)
    assert any(issue.code == "session-assembly-mixed-group-pathways" for issue in draft.issues)
    assert any(issue.code == "session-assembly-unconfirmed-group" for issue in draft.issues)
    assert draft.groups[0].needs_review is True
    assert draft.groups[0].requires_confirmation is True


def test_session_assembly_service_builds_group_summary_for_same_stem_sidecar_bundle(tmp_path: Path) -> None:
    recording_path = tmp_path / "recording.tif"
    recording_path.write_text("binary-placeholder", encoding="utf-8")
    sidecar_path = tmp_path / "recording.json"
    sidecar_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")

    draft = SessionAssemblyService(build_adapter_registry()).assemble_draft((recording_path, sidecar_path))

    assert len(draft.groups) == 1
    assert draft.groups[0].group_label == "recording"
    assert draft.groups[0].source_count == 2
    assert draft.groups[0].metadata_count == 1
    assert draft.groups[0].group_kind == "sidecar_bundle"
    assert draft.groups[0].grouping_reason == "Grouped by same-stem metadata sidecar detection."
    assert draft.groups[0].member_labels == ("recording.tif", "recording.json")


def test_session_assembly_service_tracks_group_reason_and_review_issue_count(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")

    draft = SessionAssemblyService(build_adapter_registry()).assemble_draft((manifest_path, custom_path))

    assert draft.groups[0].group_kind == "folder"
    assert draft.groups[0].anchor_path == tmp_path
    assert draft.groups[0].grouping_reason == (
        "Grouped by shared location, but contains mixed supported/custom-looking inputs."
    )
    assert draft.groups[0].review_issue_count >= 1


def test_session_assembly_service_allows_manual_group_override(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")

    draft = SessionAssemblyService(build_adapter_registry()).assemble_draft(
        (manifest_path, custom_path),
        group_overrides={"custom-session": "Custom Metadata Bundle"},
    )

    assert [source.group_label for source in draft.sources] == [tmp_path.name, "Custom Metadata Bundle"]
    assert not any(issue.code == "session-assembly-auto-grouped-inputs" for issue in draft.issues)


def test_session_assembly_service_can_confirm_auto_grouped_bundle(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    custom_path = tmp_path / "custom_session.json"
    custom_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")

    service = SessionAssemblyService(build_adapter_registry())
    unconfirmed = service.assemble_draft((manifest_path, custom_path))
    confirmed = service.assemble_draft(
        (manifest_path, custom_path),
        confirmed_group_keys=(unconfirmed.groups[0].group_key,),
    )
    session = service.create_session(confirmed)

    assert unconfirmed.groups[0].is_confirmed is False
    assert confirmed.groups[0].is_confirmed is True
    assert not any(issue.code == "session-assembly-auto-grouped-inputs" for issue in confirmed.issues)
    assert session.sources[0].metadata["session_assembly.group_confirmed"] == "true"


def test_session_assembly_service_detects_simple_metadata_sidecar(tmp_path: Path) -> None:
    image_path = tmp_path / "recording.tif"
    image_path.write_text("binary-placeholder", encoding="utf-8")
    sidecar_path = tmp_path / "recording.json"
    sidecar_path.write_text(json.dumps({"session": {"session_id": "sidecar-01"}}), encoding="utf-8")

    draft = SessionAssemblyService(build_adapter_registry()).assemble_draft((image_path, sidecar_path))

    image_source, sidecar_source = draft.sources
    assert image_source.role == "primary"
    assert sidecar_source.role == "metadata"
    assert sidecar_source.sidecar_for_label == "recording.tif"
    assert sidecar_source.sidecar_for_source_id == image_source.source_id
    assert any(issue.code == "session-assembly-sidecar-association" for issue in draft.issues)


def test_session_assembly_service_deduplicates_selected_paths(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")

    service = SessionAssemblyService(build_adapter_registry())
    draft = service.assemble_draft((manifest_path, manifest_path, manifest_path.resolve()))

    assert len(draft.sources) == 1


def test_session_assembly_service_requires_primary_source(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")

    service = SessionAssemblyService(build_adapter_registry())
    draft = service.assemble_draft(
        (manifest_path,),
        source_roles={"session-manifest": "metadata"},
    )

    assert draft.can_create_session is False
    assert any(issue.code == "session-assembly-no-primary-source" for issue in draft.issues)


def test_session_assembly_service_blocks_mismatched_selected_supported_route(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")

    service = SessionAssemblyService(build_adapter_registry())
    draft = service.assemble_draft(
        (manifest_path,),
        source_intents={
            str(manifest_path.resolve()): {
                "ingest_kind": "supported",
                "route_name": "deeplabcut",
                "route_display_name": "DeepLabCut",
            }
        },
    )

    assert draft.can_create_session is False
    assert draft.sources[0].ingest_kind == "supported"
    assert draft.sources[0].selection_label == "DeepLabCut"
    assert draft.sources[0].route_name == "deeplabcut"
    assert draft.sources[0].matching_adapter_ids == ()
    assert any(issue.code == "session-assembly-selected-route-mismatch" for issue in draft.issues)


def test_session_assembly_service_accepts_valid_supported_entry_and_records_entry_metadata(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")

    service = SessionAssemblyService(build_adapter_registry())
    accepted, intents, rejected = service.validate_supported_selected_paths(
        (manifest_path,),
        route_name="session_manifest",
        route_display_name="Session Manifest",
    )
    draft = service.assemble_draft(accepted, source_intents=intents)

    assert accepted == (manifest_path.resolve(),)
    assert rejected == ()
    assert intents[str(manifest_path.resolve())]["entry_role_label"] == "manifest file or session directory"
    assert intents[str(manifest_path.resolve())]["entry_validation_status"] == "validated"
    assert draft.sources[0].entry_path_kind == "file"
    assert draft.sources[0].entry_role_label == "manifest file or session directory"
    assert draft.sources[0].entry_validation_status == "validated"


def test_session_assembly_service_accepts_directory_entries_for_media_routes(tmp_path: Path) -> None:
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    (image_dir / "frame-01.tif").write_text("binary-placeholder", encoding="utf-8")
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    (audio_dir / "trial.wav").write_text("binary-placeholder", encoding="utf-8")
    video_dir = tmp_path / "videos"
    video_dir.mkdir()
    (video_dir / "behavior.mp4").write_text("binary-placeholder", encoding="utf-8")
    tiff_dir = tmp_path / "tiff"
    tiff_dir.mkdir()
    (tiff_dir / "plane-01.tif").write_text("binary-placeholder", encoding="utf-8")

    service = SessionAssemblyService(build_adapter_registry())

    accepted_image, intents_image, rejected_image = service.validate_supported_selected_paths(
        (image_dir,),
        route_name="image",
        route_display_name="Images",
    )
    accepted_audio, intents_audio, rejected_audio = service.validate_supported_selected_paths(
        (audio_dir,),
        route_name="audio",
        route_display_name="Audio",
    )
    accepted_video, intents_video, rejected_video = service.validate_supported_selected_paths(
        (video_dir,),
        route_name="videos",
        route_display_name="Videos",
    )
    accepted_tiff, intents_tiff, rejected_tiff = service.validate_supported_selected_paths(
        (tiff_dir,),
        route_name="tiff",
        route_display_name="TIFF",
    )

    assert accepted_image == (image_dir.resolve(),)
    assert rejected_image == ()
    assert intents_image[str(image_dir.resolve())]["entry_path_kind"] == "directory"
    assert intents_image[str(image_dir.resolve())]["entry_role_label"] == "image file or root directory"

    assert accepted_audio == (audio_dir.resolve(),)
    assert rejected_audio == ()
    assert intents_audio[str(audio_dir.resolve())]["entry_path_kind"] == "directory"
    assert intents_audio[str(audio_dir.resolve())]["entry_role_label"] == "audio file or root directory"

    assert accepted_video == (video_dir.resolve(),)
    assert rejected_video == ()
    assert intents_video[str(video_dir.resolve())]["entry_path_kind"] == "directory"
    assert intents_video[str(video_dir.resolve())]["entry_role_label"] == "video file or root directory"

    assert accepted_tiff == (tiff_dir.resolve(),)
    assert rejected_tiff == ()
    assert intents_tiff[str(tiff_dir.resolve())]["entry_path_kind"] == "directory"
    assert intents_tiff[str(tiff_dir.resolve())]["entry_role_label"] == "main imaging file or root directory"


def test_session_assembly_service_rejects_obviously_wrong_supported_entry_path(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")

    service = SessionAssemblyService(build_adapter_registry())
    accepted, intents, rejected = service.validate_supported_selected_paths(
        (manifest_path,),
        route_name="deeplabcut",
        route_display_name="DeepLabCut",
    )

    assert accepted == ()
    assert intents == {}
    assert len(rejected) == 1
    assert "DeepLabCut" in rejected[0]
    assert ".csv, .h5" in rejected[0]


def test_session_assembly_service_validates_thor_entries_as_tiff_files(tmp_path: Path) -> None:
    thor_file = tmp_path / "Image_0001_0001.tif"
    thor_file.write_text("binary-placeholder", encoding="utf-8")
    experiment_xml = tmp_path / "Experiment.xml"
    experiment_xml.write_text("<Experiment />", encoding="utf-8")
    wrong_dir = tmp_path / "thor"
    wrong_dir.mkdir()

    service = SessionAssemblyService(build_adapter_registry())

    accepted, intents, rejected = service.validate_supported_selected_paths(
        (thor_file,),
        route_name="thor",
        route_display_name="Thor",
    )
    rejected_dir = service.validate_supported_selected_paths(
        (wrong_dir,),
        route_name="thor",
        route_display_name="Thor",
    )[2]

    assert accepted == (thor_file.resolve(),)
    assert rejected == ()
    assert intents[str(thor_file.resolve())]["entry_role_label"] == "main imaging file"
    assert rejected_dir
    assert "main imaging file" in rejected_dir[0]


def test_session_assembly_service_summarizes_resolved_structured_bundle_members(tmp_path: Path) -> None:
    thor_file = tmp_path / "Image_0001_0001.tif"
    thor_file.write_text("binary-placeholder", encoding="utf-8")
    experiment_xml = tmp_path / "Experiment.xml"
    experiment_xml.write_text("<Experiment />", encoding="utf-8")

    service = SessionAssemblyService(build_adapter_registry())
    accepted, intents, rejected = service.validate_supported_selected_paths(
        (thor_file,),
        route_name="thor",
        route_display_name="Thor",
    )
    draft = service.assemble_draft(accepted, source_intents=intents)
    session = service.create_session(draft)

    assert rejected == ()
    assert draft.sources[0].structured_bundle_member_count == 2
    assert draft.sources[0].structured_bundle_member_labels == ("Experiment.xml", "Image_0001_0001.tif")
    assert draft.groups[0].canonical_bundle_member_count == 2
    assert draft.groups[0].grouping_reason.endswith("with 2 resolved bundle members.")
    assert session.sources[0].metadata["session_assembly.structured_bundle_member_count"] == "2"
    assert json.loads(session.sources[0].metadata["session_assembly.structured_bundle_member_labels_json"]) == [
        "Experiment.xml",
        "Image_0001_0001.tif",
    ]


def test_session_assembly_service_summarizes_directory_supported_bundle_members(tmp_path: Path) -> None:
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    (image_dir / "frame-01.tif").write_text("binary-placeholder", encoding="utf-8")
    (image_dir / "frame-02.tif").write_text("binary-placeholder", encoding="utf-8")

    service = SessionAssemblyService(build_adapter_registry())
    accepted, intents, rejected = service.validate_supported_selected_paths(
        (image_dir,),
        route_name="image",
        route_display_name="Images",
    )
    draft = service.assemble_draft(accepted, source_intents=intents)

    assert rejected == ()
    assert draft.sources[0].structured_bundle_member_count == 2
    assert draft.sources[0].structured_bundle_member_labels == ("frame-01.tif", "frame-02.tif")
    assert draft.groups[0].canonical_bundle_member_count == 2


def test_session_assembly_service_filters_bruker_route_matches_with_current_adapter_ids(tmp_path: Path) -> None:
    image_path = tmp_path / "bruker_recording.tif"
    image_path.write_text("binary-placeholder", encoding="utf-8")

    registry = AdapterRegistry()
    registry.register(_AlwaysMatchingAdapter())

    draft = SessionAssemblyService(registry).assemble_draft(
        (image_path,),
        source_intents={
            str(image_path.resolve()): {
                "ingest_kind": "supported",
                "route_name": "brukertiff",
                "route_display_name": "Bruker TIFF",
            }
        },
    )

    assert draft.sources[0].route_name == "brukertiff"
    assert draft.sources[0].matching_adapter_ids == ("neuroconv_brukertiff_singleplane",)
    assert draft.sources[0].suggested_adapter_id == "neuroconv_brukertiff_singleplane"
    assert not any(issue.code == "session-assembly-selected-route-mismatch" for issue in draft.issues)


def test_session_assembly_service_preserves_selected_source_context_in_draft(tmp_path: Path) -> None:
    notes_path = tmp_path / "notes.txt"
    notes_path.write_text("operator notes", encoding="utf-8")

    service = SessionAssemblyService(build_adapter_registry())
    draft = service.assemble_draft(
        (notes_path,),
        source_intents={
            str(notes_path.resolve()): {
                "ingest_kind": "supported",
                "route_name": "deeplabcut",
                "route_display_name": "DeepLabCut",
            }
        },
        source_roles={"notes": "primary"},
    )

    assert draft.sources[0].selection_label == "DeepLabCut"
    assert draft.sources[0].route_name == "deeplabcut"


def test_session_assembly_service_filters_unsupported_custom_file_types(tmp_path: Path) -> None:
    notes_path = tmp_path / "notes.txt"
    notes_path.write_text("operator notes", encoding="utf-8")
    binary_path = tmp_path / "mystery.exe"
    binary_path.write_text("not a dataset", encoding="utf-8")

    service = SessionAssemblyService(build_adapter_registry())
    accepted, rejected = service.filter_custom_selected_paths((notes_path, binary_path))

    assert accepted == (notes_path.resolve(),)
    assert len(rejected) == 1
    assert "mystery.exe" in rejected[0]


def test_session_assembly_service_attaches_custom_input_to_single_supported_anchor(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    notes_path = tmp_path / "notes.txt"
    notes_path.write_text("operator notes", encoding="utf-8")

    service = SessionAssemblyService(build_adapter_registry())
    draft = service.assemble_draft(
        (manifest_path, notes_path),
        source_intents={
            str(manifest_path.resolve()): {
                "ingest_kind": "supported",
                "route_name": "session_manifest",
                "route_display_name": "Session Manifest",
                "entry_path_kind": "file",
                "entry_role_label": "manifest file or session directory",
                "entry_validation_status": "validated",
            }
        },
    )

    manifest_source = next(source for source in draft.sources if source.location == manifest_path.resolve())
    notes_source = next(source for source in draft.sources if source.location == notes_path.resolve())

    assert len(draft.groups) == 1
    assert notes_source.group_key == manifest_source.group_key
    assert notes_source.context_source_id == manifest_source.source_id
    assert notes_source.context_label == "Session Manifest"
    assert draft.groups[0].canonical_source_id == manifest_source.source_id
    assert draft.groups[0].canonical_source_label == "session_manifest.json"
    assert draft.groups[0].canonical_source_path == manifest_path.resolve()
    assert draft.groups[0].canonical_entry_role_label == "manifest file or session directory"
    assert draft.groups[0].canonical_selection_label == "Session Manifest"
    assert any(issue.code == "session-assembly-custom-context-association" for issue in draft.issues)

    confirmed = service.assemble_draft(
        (manifest_path, notes_path),
        source_intents={
            str(manifest_path.resolve()): {
                "ingest_kind": "supported",
                "route_name": "session_manifest",
                "route_display_name": "Session Manifest",
                "entry_path_kind": "file",
                "entry_role_label": "manifest file or session directory",
                "entry_validation_status": "validated",
            }
        },
        confirmed_group_keys=(draft.groups[0].group_key,),
    )
    session = service.create_session(confirmed)

    assert session.sources[0].metadata["session_assembly.group_kind"] == "supported_anchor"
    assert session.sources[0].metadata["session_assembly.group_pathway"] == "hybrid"
    assert session.sources[0].metadata["session_assembly.group_canonical_source_label"] == "session_manifest.json"
    assert session.sources[1].metadata["session_assembly.group_canonical_selection_label"] == "Session Manifest"
    assert json.loads(session.sources[0].metadata["session_assembly.group_member_labels_json"]) == [
        "session_manifest.json",
        "notes.txt",
    ]
    assert json.loads(session.sources[1].metadata["session_assembly.group_source_ids_json"]) == [
        manifest_source.source_id,
        notes_source.source_id,
    ]


def test_session_assembly_service_leaves_custom_input_separate_when_multiple_supported_anchors_exist(
    tmp_path: Path,
) -> None:
    first_manifest_path = tmp_path / "session_manifest.json"
    first_manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    second_manifest_path = tmp_path / "custom_session.json"
    second_manifest_path.write_text(json.dumps({"recording_context": {"recording_id": "custom-01"}}), encoding="utf-8")
    notes_path = tmp_path / "notes.txt"
    notes_path.write_text("operator notes", encoding="utf-8")

    service = SessionAssemblyService(build_adapter_registry())
    draft = service.assemble_draft(
        (first_manifest_path, second_manifest_path, notes_path),
        source_intents={
            str(first_manifest_path.resolve()): {
                "ingest_kind": "supported",
                "route_display_name": "Session Manifest",
            },
            str(second_manifest_path.resolve()): {
                "ingest_kind": "supported",
                "route_display_name": "Custom Session",
            },
        },
    )

    notes_source = next(source for source in draft.sources if source.location == notes_path.resolve())

    assert notes_source.context_source_id is None
    assert len(draft.groups) == 3
    assert any(issue.code == "session-assembly-ambiguous-custom-context" for issue in draft.issues)


def test_session_assembly_service_groups_supported_sources_as_combined_workflow(tmp_path: Path) -> None:
    imaging_dir = tmp_path / "imaging"
    imaging_dir.mkdir()
    (imaging_dir / "plane-01.tif").write_text("binary-placeholder", encoding="utf-8")
    suite2p_dir = tmp_path / "suite2p"
    suite2p_dir.mkdir()

    service = SessionAssemblyService(_build_workflow_registry())
    draft = service.assemble_draft(
        (imaging_dir, suite2p_dir),
        source_intents={
            str(imaging_dir.resolve()): {
                "ingest_kind": "supported",
                "route_name": "tiff",
                "route_display_name": "TIFF Imaging",
            },
            str(suite2p_dir.resolve()): {
                "ingest_kind": "supported",
                "route_name": "suite2p",
                "route_display_name": "Suite2p",
            },
        },
    )
    confirmed = service.assemble_draft(
        (imaging_dir, suite2p_dir),
        source_intents={
            str(imaging_dir.resolve()): {
                "ingest_kind": "supported",
                "route_name": "tiff",
                "route_display_name": "TIFF Imaging",
            },
            str(suite2p_dir.resolve()): {
                "ingest_kind": "supported",
                "route_name": "suite2p",
                "route_display_name": "Suite2p",
            },
        },
        confirmed_group_keys=(draft.groups[0].group_key,),
    )
    session = service.create_session(confirmed)

    assert len(draft.groups) == 1
    assert draft.groups[0].group_kind == "workflow_bundle"
    assert draft.groups[0].workflow_adapter_id == "workflow_tiff_suite2p"
    assert draft.groups[0].workflow_display_name == "TIFF + Suite2p Workflow"
    assert "combined NeuroConv workflow" in draft.groups[0].grouping_reason
    assert {source.workflow_display_name for source in draft.sources} == {"TIFF + Suite2p Workflow"}
    assert session.sources[0].metadata["session_assembly.group_kind"] == "workflow_bundle"
    assert session.sources[0].metadata["session_assembly.group_pathway"] == "supported"
    assert "combined NeuroConv workflow" in session.sources[0].metadata["session_assembly.grouping_reason"]
    assert json.loads(session.sources[0].metadata["session_assembly.group_member_labels_json"]) == [
        "imaging",
        "suite2p",
    ]
    assert json.loads(session.sources[1].metadata["session_assembly.group_source_ids_json"]) == [
        draft.sources[0].source_id,
        draft.sources[1].source_id,
    ]
    assert session.sources[0].metadata["session_assembly.workflow_adapter_id"] == "workflow_tiff_suite2p"
    assert session.sources[1].metadata["session_assembly.workflow_display_name"] == "TIFF + Suite2p Workflow"


def test_session_assembly_service_warns_on_heterogeneous_custom_folder_group(tmp_path: Path) -> None:
    table_path = tmp_path / "behavior.csv"
    table_path.write_text("time,value\n0,1\n", encoding="utf-8")
    video_path = tmp_path / "behavior.mp4"
    video_path.write_text("binary-placeholder", encoding="utf-8")

    service = SessionAssemblyService(build_adapter_registry())
    draft = service.assemble_draft((table_path, video_path))

    assert len(draft.groups) == 1
    assert any(issue.code == "session-assembly-ambiguous-custom-bundle" for issue in draft.issues)


def test_session_assembly_service_preserves_project_origin_in_created_session(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(json.dumps({"session": {"session_id": "supported-01"}}), encoding="utf-8")
    project_path = tmp_path / "projects" / "saved-project.nwbforge-project.json"
    project_path.parent.mkdir()

    service = SessionAssemblyService(build_adapter_registry())
    draft = service.assemble_draft((manifest_path,), project_path=project_path)
    session = service.create_session(draft)

    assert session.sources[0].metadata["session_assembly.project_path"] == str(project_path.resolve())
    assert session.sources[0].metadata["session_assembly.project_name"] == "saved-project.nwbforge-project.json"


def test_session_assembly_service_attaches_custom_input_to_matched_workflow_group(tmp_path: Path) -> None:
    imaging_dir = tmp_path / "imaging"
    imaging_dir.mkdir()
    (imaging_dir / "plane-01.tif").write_text("binary-placeholder", encoding="utf-8")
    suite2p_dir = tmp_path / "suite2p"
    suite2p_dir.mkdir()
    notes_path = tmp_path / "notes.txt"
    notes_path.write_text("operator notes", encoding="utf-8")

    service = SessionAssemblyService(_build_workflow_registry())
    draft = service.assemble_draft(
        (imaging_dir, suite2p_dir, notes_path),
        source_intents={
            str(imaging_dir.resolve()): {
                "ingest_kind": "supported",
                "route_name": "tiff",
                "route_display_name": "TIFF Imaging",
            },
            str(suite2p_dir.resolve()): {
                "ingest_kind": "supported",
                "route_name": "suite2p",
                "route_display_name": "Suite2p",
            },
        },
    )

    notes_source = next(source for source in draft.sources if source.location == notes_path.resolve())

    assert len(draft.groups) == 1
    assert notes_source.context_label == "TIFF + Suite2p Workflow"
    assert draft.groups[0].workflow_display_name == "TIFF + Suite2p Workflow"
    assert "supplemental or custom inputs attached for review" in draft.groups[0].grouping_reason


def test_session_assembly_service_absorbs_selected_thor_bundle_member(tmp_path: Path) -> None:
    thor_file = tmp_path / "Image_0001_0001.tif"
    thor_file.write_text("binary-placeholder", encoding="utf-8")
    experiment_xml = tmp_path / "Experiment.xml"
    experiment_xml.write_text("<Experiment />", encoding="utf-8")

    service = SessionAssemblyService(build_adapter_registry())
    draft = service.assemble_draft(
        (thor_file, experiment_xml),
        source_intents={
            str(thor_file.resolve()): {
                "ingest_kind": "supported",
                "route_name": "thor",
                "route_display_name": "Thor",
                "entry_path_kind": "file",
                "entry_role_label": "main imaging file",
                "entry_validation_status": "validated",
            }
        },
    )

    assert len(draft.sources) == 1
    assert draft.sources[0].location == thor_file.resolve()
    assert draft.sources[0].structured_bundle_member_count == 2
    assert any(issue.code == "session-assembly-structured-member-absorbed" for issue in draft.issues)


def test_session_assembly_service_absorbs_selected_file_inside_supported_directory_bundle(tmp_path: Path) -> None:
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    image_file = image_dir / "frame-01.tif"
    image_file.write_text("binary-placeholder", encoding="utf-8")

    service = SessionAssemblyService(build_adapter_registry())
    draft = service.assemble_draft(
        (image_dir, image_file),
        source_intents={
            str(image_dir.resolve()): {
                "ingest_kind": "supported",
                "route_name": "image",
                "route_display_name": "Image",
                "entry_path_kind": "directory",
                "entry_role_label": "image file or root directory",
                "entry_validation_status": "validated",
            }
        },
    )

    assert len(draft.sources) == 1
    assert draft.sources[0].location == image_dir.resolve()
    assert draft.groups[0].canonical_bundle_member_count == 1
    assert any(issue.code == "session-assembly-structured-member-absorbed" for issue in draft.issues)
