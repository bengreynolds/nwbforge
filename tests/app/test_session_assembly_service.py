from __future__ import annotations

import json
from pathlib import Path

from nwbforge.app.desktop import build_adapter_registry
from nwbforge.app.services import SessionAssemblyService


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
