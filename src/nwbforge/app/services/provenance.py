"""Concrete provenance services."""

from __future__ import annotations

from nwbforge.domain.contracts import ProvenanceService
from nwbforge.domain.models import ConversionSession, ProvenanceArtifact, ProvenanceRecord


class SessionProvenanceService(ProvenanceService):
    """Build provenance records directly from session state."""

    def build_record(
        self,
        session: ConversionSession,
        input_artifacts: tuple[ProvenanceArtifact, ...],
        generated_artifacts: tuple[ProvenanceArtifact, ...],
    ) -> ProvenanceRecord:
        adapter_ids = tuple(
            sorted(
                {
                    source.adapter_hint
                    for source in session.sources
                    if source.adapter_hint is not None
                }
            )
        )
        return ProvenanceRecord(
            session_id=session.session_id,
            pathway=session.pathway,
            input_artifacts=input_artifacts,
            generated_artifacts=generated_artifacts,
            adapter_ids=adapter_ids,
            lab_profile=session.lab_profile,
            notes=session.notes,
        )
