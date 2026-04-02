"""Provenance records for conversion transparency."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nwbforge.domain.enums import ConversionPathway


@dataclass(frozen=True, slots=True)
class ProvenanceArtifact:
    artifact_type: str
    location: Path
    description: str | None = None
    sha256: str | None = None


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    session_id: str
    pathway: ConversionPathway
    input_artifacts: tuple[ProvenanceArtifact, ...] = ()
    generated_artifacts: tuple[ProvenanceArtifact, ...] = ()
    adapter_ids: tuple[str, ...] = ()
    lab_profile: str | None = None
    notes: tuple[str, ...] = ()

    def artifact_locations(self) -> tuple[Path, ...]:
        return tuple(
            artifact.location for artifact in self.input_artifacts + self.generated_artifacts
        )
