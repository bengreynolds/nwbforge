"""Explicit project-file persistence for direct-ingest desktop sessions."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from nwbforge.app.services.session_assembly import SessionAssemblyWorkspace


@dataclass(frozen=True, slots=True)
class SessionAssemblyProjectDocument:
    """A persisted direct-ingest project document."""

    project_path: Path
    workspace: SessionAssemblyWorkspace


class JsonSessionAssemblyProjectStore:
    """Persist explicit direct-ingest project files."""

    _SCHEMA_VERSION = 1
    _PROJECT_KIND = "nwbforge.session-assembly-project"

    def save(
        self,
        project_path: Path,
        workspace: SessionAssemblyWorkspace,
    ) -> SessionAssemblyProjectDocument:
        resolved_path = project_path.resolve()
        payload = {
            "schema_version": self._SCHEMA_VERSION,
            "project_kind": self._PROJECT_KIND,
            "workspace": {
                "selected_paths": [str(path) for path in workspace.selected_paths],
                "session_id": workspace.session_id,
                "title": workspace.title,
                "has_unsaved_changes": False,
                "source_roles": dict(workspace.source_roles or {}),
                "group_overrides": dict(workspace.group_overrides or {}),
                "metadata_overrides": dict(workspace.metadata_overrides or {}),
                "source_metadata_overrides": {
                    str(source_id): {
                        str(key): str(value)
                        for key, value in dict(overrides).items()
                        if str(value).strip()
                    }
                    for source_id, overrides in (workspace.source_metadata_overrides or {}).items()
                    if overrides
                },
            },
        }
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return SessionAssemblyProjectDocument(project_path=resolved_path, workspace=workspace)

    def load(self, project_path: Path) -> SessionAssemblyProjectDocument:
        resolved_path = project_path.resolve()
        payload = json.loads(resolved_path.read_text(encoding="utf-8"))
        if payload.get("project_kind") != self._PROJECT_KIND:
            raise ValueError(f"Project file is not a supported NWB Forge direct-ingest project: {resolved_path}")

        workspace_payload = payload.get("workspace")
        if not isinstance(workspace_payload, dict):
            raise ValueError(f"Project file is missing a workspace payload: {resolved_path}")

        return SessionAssemblyProjectDocument(
            project_path=resolved_path,
            workspace=SessionAssemblyWorkspace(
                selected_paths=tuple(Path(path) for path in workspace_payload.get("selected_paths", ())),
                session_id=str(workspace_payload.get("session_id", "")),
                title=str(workspace_payload.get("title", "")),
                has_unsaved_changes=bool(workspace_payload.get("has_unsaved_changes", False)),
                source_roles={
                    str(key): str(value)
                    for key, value in dict(workspace_payload.get("source_roles", {})).items()
                },
                group_overrides={
                    str(key): str(value)
                    for key, value in dict(workspace_payload.get("group_overrides", {})).items()
                },
                metadata_overrides={
                    str(key): str(value)
                    for key, value in dict(workspace_payload.get("metadata_overrides", {})).items()
                },
                source_metadata_overrides={
                    str(source_id): {
                        str(key): str(value)
                        for key, value in dict(overrides).items()
                    }
                    for source_id, overrides in dict(workspace_payload.get("source_metadata_overrides", {})).items()
                },
            ),
        )
