"""JSON-backed persistence for resumable session snapshots."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from nwbforge.domain.contracts import SessionSnapshotStore
from nwbforge.domain.enums import (
    ConversionPathway,
    IssueSeverity,
    ReviewStatus,
    SessionStatus,
    SourceType,
    ValidationReviewStatus,
)
from nwbforge.domain.models import (
    ConversionSession,
    ExecutionReviewRecord,
    ProvenanceArtifact,
    ProvenanceRecord,
    SessionSnapshot,
    SessionSnapshotHistoryEntry,
    SourceReference,
    ValidationIssue,
    ValidationReviewOutcome,
    ValidationSummary,
)


class JsonSessionSnapshotStore(SessionSnapshotStore):
    """Persist session snapshots as JSON files under a configurable base directory."""

    def __init__(
        self,
        base_dir: str | Path = Path("artifacts") / "session-state",
        *,
        history_limit: int = 10,
    ) -> None:
        self._base_dir = Path(base_dir)
        self._history_limit = max(int(history_limit), 1)

    @property
    def history_limit(self) -> int:
        return self._history_limit

    def set_history_limit(self, history_limit: int) -> None:
        self._history_limit = max(int(history_limit), 1)

    def save(self, snapshot: SessionSnapshot) -> ProvenanceArtifact:
        normalized_snapshot = self._with_snapshot_identity(snapshot)
        snapshot_path = self.snapshot_path(normalized_snapshot.session.session_id)
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(
            json.dumps(self._serialize_snapshot(normalized_snapshot), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        history_path = self.version_path(
            normalized_snapshot.session.session_id,
            normalized_snapshot.snapshot_id or "latest",
        )
        history_path.parent.mkdir(parents=True, exist_ok=True)
        history_path.write_text(
            json.dumps(self._serialize_snapshot(normalized_snapshot), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        self._trim_history(normalized_snapshot.session.session_id)
        return ProvenanceArtifact(
            artifact_type="session_snapshot",
            location=snapshot_path,
            description="Persisted session snapshot.",
        )

    def load(self, session_id: str) -> SessionSnapshot | None:
        snapshot_path = self.snapshot_path(session_id)
        if not snapshot_path.exists():
            return None
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        return self._deserialize_snapshot(payload)

    def list_history(self, session_id: str) -> tuple[SessionSnapshotHistoryEntry, ...]:
        history_dir = self.history_dir(session_id)
        if not history_dir.exists():
            return ()
        entries: list[SessionSnapshotHistoryEntry] = []
        for snapshot_path in sorted(history_dir.glob("*.json"), reverse=True):
            payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
            snapshot = self._deserialize_snapshot(payload)
            if snapshot.snapshot_id is None or snapshot.saved_at is None:
                continue
            issue_count = len(snapshot.validation_summary.issues) if snapshot.validation_summary is not None else 0
            artifact_count = (
                len(snapshot.provenance_record.generated_artifacts)
                if snapshot.provenance_record is not None
                else 0
            )
            entries.append(
                SessionSnapshotHistoryEntry(
                    snapshot_id=snapshot.snapshot_id,
                    session_id=snapshot.session.session_id,
                    saved_at=snapshot.saved_at,
                    location=snapshot_path,
                    status=snapshot.session.status.value,
                    artifact_count=artifact_count,
                    issue_count=issue_count,
                    has_review_record=snapshot.review_record is not None,
                )
            )
        return tuple(sorted(entries, key=lambda entry: entry.saved_at, reverse=True))

    def load_version(self, session_id: str, snapshot_id: str) -> SessionSnapshot | None:
        snapshot_path = self.version_path(session_id, snapshot_id)
        if not snapshot_path.exists():
            return None
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        return self._deserialize_snapshot(payload)

    def snapshot_path(self, session_id: str) -> Path:
        return self._base_dir / session_id / "session-state.json"

    def history_dir(self, session_id: str) -> Path:
        return self._base_dir / session_id / "history"

    def version_path(self, session_id: str, snapshot_id: str) -> Path:
        return self.history_dir(session_id) / f"{snapshot_id}.json"

    @staticmethod
    def _serialize_snapshot(snapshot: SessionSnapshot) -> dict[str, object]:
        return {
            "schema_version": 1,
            "snapshot_id": snapshot.snapshot_id,
            "saved_at": snapshot.saved_at.isoformat() if snapshot.saved_at is not None else None,
            "session": JsonSessionSnapshotStore._serialize_session(snapshot.session),
            "provenance_record": JsonSessionSnapshotStore._serialize_provenance(snapshot.provenance_record),
            "validation_summary": JsonSessionSnapshotStore._serialize_validation_summary(
                snapshot.validation_summary
            ),
            "review_outcome": JsonSessionSnapshotStore._serialize_review_outcome(snapshot.review_outcome),
            "review_record": JsonSessionSnapshotStore._serialize_review_record(snapshot.review_record),
        }

    @staticmethod
    def _deserialize_snapshot(payload: dict[str, object]) -> SessionSnapshot:
        return SessionSnapshot(
            snapshot_id=None if payload.get("snapshot_id") is None else str(payload["snapshot_id"]),
            saved_at=(
                None
                if payload.get("saved_at") is None
                else datetime.fromisoformat(str(payload["saved_at"]))
            ),
            session=JsonSessionSnapshotStore._deserialize_session(payload["session"]),
            provenance_record=JsonSessionSnapshotStore._deserialize_provenance(
                payload.get("provenance_record")
            ),
            validation_summary=JsonSessionSnapshotStore._deserialize_validation_summary(
                payload.get("validation_summary")
            ),
            review_outcome=JsonSessionSnapshotStore._deserialize_review_outcome(
                payload.get("review_outcome")
            ),
            review_record=JsonSessionSnapshotStore._deserialize_review_record(payload.get("review_record")),
        )

    @staticmethod
    def _with_snapshot_identity(snapshot: SessionSnapshot) -> SessionSnapshot:
        snapshot_id = snapshot.snapshot_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + f"-{uuid4().hex[:8]}"
        saved_at = snapshot.saved_at or datetime.now(UTC)
        return SessionSnapshot(
            snapshot_id=snapshot_id,
            saved_at=saved_at,
            session=snapshot.session,
            provenance_record=snapshot.provenance_record,
            validation_summary=snapshot.validation_summary,
            review_outcome=snapshot.review_outcome,
            review_record=snapshot.review_record,
        )

    def _trim_history(self, session_id: str) -> None:
        history = self.list_history(session_id)
        for entry in history[self._history_limit :]:
            if entry.location.exists():
                entry.location.unlink()

    @staticmethod
    def _serialize_session(session: ConversionSession) -> dict[str, object]:
        return {
            "session_id": session.session_id,
            "pathway": str(session.pathway),
            "status": str(session.status),
            "title": session.title,
            "lab_profile": session.lab_profile,
            "metadata_overrides": dict(session.metadata_overrides),
            "source_metadata_overrides": {
                str(source_id): {
                    str(key): str(value)
                    for key, value in overrides.items()
                    if str(value).strip()
                }
                for source_id, overrides in session.source_metadata_overrides.items()
                if overrides
            },
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "notes": list(session.notes),
            "sources": [
                {
                    "source_id": source.source_id,
                    "location": str(source.location),
                    "source_type": str(source.source_type),
                    "label": source.label,
                    "role": source.role,
                    "media_type": source.media_type,
                    "adapter_hint": source.adapter_hint,
                    "metadata": source.metadata,
                    "sidecar_ids": list(source.sidecar_ids),
                }
                for source in session.sources
            ],
        }

    @staticmethod
    def _deserialize_session(payload: object) -> ConversionSession:
        if not isinstance(payload, dict):
            raise TypeError("Session snapshot payload must contain a session object.")
        return ConversionSession(
            session_id=str(payload["session_id"]),
            pathway=ConversionPathway(str(payload["pathway"])),
            status=SessionStatus(str(payload["status"])),
            sources=tuple(
                SourceReference(
                    source_id=str(source["source_id"]),
                    location=Path(str(source["location"])),
                    source_type=SourceType(str(source["source_type"])),
                    label=str(source["label"]),
                    role=str(source.get("role", "primary")),
                    media_type=None if source.get("media_type") is None else str(source["media_type"]),
                    adapter_hint=None
                    if source.get("adapter_hint") is None
                    else str(source["adapter_hint"]),
                    metadata=dict(source.get("metadata", {})),
                    sidecar_ids=tuple(str(value) for value in source.get("sidecar_ids", ())),
                )
                for source in payload.get("sources", [])
            ),
            title=None if payload.get("title") is None else str(payload["title"]),
            lab_profile=None if payload.get("lab_profile") is None else str(payload["lab_profile"]),
            metadata_overrides={
                str(key): str(value)
                for key, value in dict(payload.get("metadata_overrides", {})).items()
                if value is not None and str(value).strip()
            },
            source_metadata_overrides={
                str(source_id): {
                    str(key): str(value)
                    for key, value in dict(overrides).items()
                    if value is not None and str(value).strip()
                }
                for source_id, overrides in dict(payload.get("source_metadata_overrides", {})).items()
            },
            created_at=datetime.fromisoformat(str(payload["created_at"])),
            updated_at=datetime.fromisoformat(str(payload["updated_at"])),
            notes=tuple(str(note) for note in payload.get("notes", ())),
        )

    @staticmethod
    def _serialize_provenance(record: ProvenanceRecord | None) -> dict[str, object] | None:
        if record is None:
            return None
        return {
            "session_id": record.session_id,
            "pathway": str(record.pathway),
            "input_artifacts": [
                JsonSessionSnapshotStore._serialize_artifact(artifact)
                for artifact in record.input_artifacts
            ],
            "generated_artifacts": [
                JsonSessionSnapshotStore._serialize_artifact(artifact)
                for artifact in record.generated_artifacts
            ],
            "adapter_ids": list(record.adapter_ids),
            "lab_profile": record.lab_profile,
            "notes": list(record.notes),
        }

    @staticmethod
    def _deserialize_provenance(payload: object) -> ProvenanceRecord | None:
        if payload is None:
            return None
        if not isinstance(payload, dict):
            raise TypeError("Provenance payload must be an object or null.")
        return ProvenanceRecord(
            session_id=str(payload["session_id"]),
            pathway=ConversionPathway(str(payload["pathway"])),
            input_artifacts=tuple(
                JsonSessionSnapshotStore._deserialize_artifact(artifact)
                for artifact in payload.get("input_artifacts", [])
            ),
            generated_artifacts=tuple(
                JsonSessionSnapshotStore._deserialize_artifact(artifact)
                for artifact in payload.get("generated_artifacts", [])
            ),
            adapter_ids=tuple(str(adapter_id) for adapter_id in payload.get("adapter_ids", ())),
            lab_profile=None if payload.get("lab_profile") is None else str(payload["lab_profile"]),
            notes=tuple(str(note) for note in payload.get("notes", ())),
        )

    @staticmethod
    def _serialize_artifact(artifact: ProvenanceArtifact) -> dict[str, object]:
        return {
            "artifact_type": artifact.artifact_type,
            "location": str(artifact.location),
            "description": artifact.description,
            "sha256": artifact.sha256,
        }

    @staticmethod
    def _deserialize_artifact(payload: object) -> ProvenanceArtifact:
        if not isinstance(payload, dict):
            raise TypeError("Artifact payload must be an object.")
        return ProvenanceArtifact(
            artifact_type=str(payload["artifact_type"]),
            location=Path(str(payload["location"])),
            description=None if payload.get("description") is None else str(payload["description"]),
            sha256=None if payload.get("sha256") is None else str(payload["sha256"]),
        )

    @staticmethod
    def _serialize_validation_summary(summary: ValidationSummary | None) -> dict[str, object] | None:
        if summary is None:
            return None
        return {
            "issues": [
                {
                    "code": issue.code,
                    "message": issue.message,
                    "severity": str(issue.severity),
                    "location": issue.location,
                    "tool": issue.tool,
                }
                for issue in summary.issues
            ]
        }

    @staticmethod
    def _deserialize_validation_summary(payload: object) -> ValidationSummary | None:
        if payload is None:
            return None
        if not isinstance(payload, dict):
            raise TypeError("Validation summary payload must be an object or null.")
        return ValidationSummary(
            issues=tuple(
                ValidationIssue(
                    code=str(issue["code"]),
                    message=str(issue["message"]),
                    severity=IssueSeverity(str(issue["severity"])),
                    location=None if issue.get("location") is None else str(issue["location"]),
                    tool=None if issue.get("tool") is None else str(issue["tool"]),
                )
                for issue in payload.get("issues", [])
            )
        )

    @staticmethod
    def _serialize_review_outcome(
        review_outcome: ValidationReviewOutcome | None,
    ) -> dict[str, object] | None:
        if review_outcome is None:
            return None
        return {
            "status": str(review_outcome.status),
            "blocks_completion": review_outcome.blocks_completion,
            "requires_manual_review": review_outcome.requires_manual_review,
            "error_count": review_outcome.error_count,
            "warning_count": review_outcome.warning_count,
        }

    @staticmethod
    def _deserialize_review_outcome(payload: object) -> ValidationReviewOutcome | None:
        if payload is None:
            return None
        if not isinstance(payload, dict):
            raise TypeError("Review outcome payload must be an object or null.")
        return ValidationReviewOutcome(
            status=ValidationReviewStatus(str(payload["status"])),
            blocks_completion=bool(payload["blocks_completion"]),
            requires_manual_review=bool(payload["requires_manual_review"]),
            error_count=int(payload["error_count"]),
            warning_count=int(payload["warning_count"]),
        )

    @staticmethod
    def _serialize_review_record(record: ExecutionReviewRecord | None) -> dict[str, object] | None:
        if record is None:
            return None
        return {
            "session_id": record.session_id,
            "reviewer": record.reviewer,
            "decision": str(record.decision),
            "validation_status": str(record.validation_status),
            "acknowledged_issue_refs": list(record.acknowledged_issue_refs),
            "override_blocks_completion": record.override_blocks_completion,
            "rationale": record.rationale,
            "reviewed_at": record.reviewed_at.isoformat(),
        }

    @staticmethod
    def _deserialize_review_record(payload: object) -> ExecutionReviewRecord | None:
        if payload is None:
            return None
        if not isinstance(payload, dict):
            raise TypeError("Review record payload must be an object or null.")
        return ExecutionReviewRecord(
            session_id=str(payload["session_id"]),
            reviewer=str(payload["reviewer"]),
            decision=ReviewStatus(str(payload["decision"])),
            validation_status=ValidationReviewStatus(str(payload["validation_status"])),
            acknowledged_issue_refs=tuple(
                str(issue_ref) for issue_ref in payload.get("acknowledged_issue_refs", ())
            ),
            override_blocks_completion=bool(payload.get("override_blocks_completion", False)),
            rationale=None if payload.get("rationale") is None else str(payload["rationale"]),
            reviewed_at=datetime.fromisoformat(str(payload["reviewed_at"])),
        )
