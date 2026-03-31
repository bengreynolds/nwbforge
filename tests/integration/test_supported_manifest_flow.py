import json
from pathlib import Path

from nwbforge.adapters import AdapterRegistry, SessionManifestAdapter
from nwbforge.app.services import RegistrySourceInspectionService
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ConversionSession, SourceReference
from nwbforge.mapping import RuleBasedMappingPlanner
from nwbforge.normalization import RuleBasedNormalizationService


def test_supported_manifest_flow_produces_reviewable_mapping_plan(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "session": {
                    "session_id": "session-01",
                    "description": "Visual task recording",
                    "start_time": "2026-03-31T10:15:00-06:00",
                    "experimenter": "Researcher A",
                },
                "subject": {
                    "subject_id": "mouse-01",
                    "species": "Mus musculus",
                },
                "keywords": ["vision", "behavior"],
                "operator_note": "check sync alignment",
            }
        ),
        encoding="utf-8",
    )
    source = SourceReference(
        source_id="source-1",
        location=manifest_path,
        source_type=SourceType.FILE,
        label="Structured session manifest",
    )
    session = ConversionSession(
        session_id="sess-001",
        pathway=ConversionPathway.SUPPORTED,
        sources=(source,),
    )

    registry = AdapterRegistry()
    registry.register(SessionManifestAdapter())

    extraction = RegistrySourceInspectionService(registry).inspect(session, "source-1")
    normalized = RuleBasedNormalizationService().normalize(session, (extraction,))
    plan = RuleBasedMappingPlanner().plan(session, normalized)

    assert extraction.record_type == "session_manifest"
    assert normalized.session.session_description is not None
    assert normalized.subject.subject_id is not None
    assert any(decision.target_path == "NWBFile.session_description" for decision in plan.decisions)
    assert any(decision.source_key == "operator_note" for decision in plan.decisions)
