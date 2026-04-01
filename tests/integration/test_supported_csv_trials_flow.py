import json
from pathlib import Path

from nwbforge.adapters import AdapterRegistry, NeuroConvCsvTimeIntervalsAdapter, SessionManifestAdapter
from nwbforge.app.services import RegistrySourceInspectionService
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ConversionSession, SourceReference
from nwbforge.mapping import RuleBasedMappingPlanner
from nwbforge.normalization import RuleBasedNormalizationService


def test_supported_manifest_plus_csv_flow_produces_trial_mapping(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "session": {
                    "session_id": "session-01",
                    "description": "Visual task recording",
                    "start_time": "2026-03-31T10:15:00-06:00",
                },
                "subject": {
                    "subject_id": "mouse-01",
                    "species": "Mus musculus",
                    "sex": "U",
                    "age": "P90D",
                    "description": "Test subject",
                },
            }
        ),
        encoding="utf-8",
    )
    csv_path = tmp_path / "trials.csv"
    csv_path.write_text(
        "start_time,condition,correct\n0.5,left,True\n1.2,right,False\n",
        encoding="utf-8",
    )
    session = ConversionSession(
        session_id="sess-001",
        pathway=ConversionPathway.SUPPORTED,
        sources=(
            SourceReference(
                source_id="manifest",
                location=manifest_path,
                source_type=SourceType.FILE,
                label="Structured session manifest",
            ),
            SourceReference(
                source_id="trials",
                location=csv_path,
                source_type=SourceType.FILE,
                label="Trial intervals",
            ),
        ),
    )

    registry = AdapterRegistry()
    registry.register(SessionManifestAdapter())
    registry.register(NeuroConvCsvTimeIntervalsAdapter())
    inspection_service = RegistrySourceInspectionService(registry)

    extraction_results = (
        inspection_service.inspect(session, "manifest"),
        inspection_service.inspect(session, "trials"),
    )
    normalized = RuleBasedNormalizationService().normalize(session, extraction_results)
    plan = RuleBasedMappingPlanner().plan(session, normalized)

    assert len(normalized.time_interval_tables) == 1
    assert normalized.time_interval_tables[0].rows[0].metadata["condition"].value == "left"
    assert any(
        decision.target_path == "TimeIntervals[trials].rows[0].start_time"
        for decision in plan.decisions
    )
    assert any(
        decision.target_path == "TimeIntervals[trials].rows[1].correct"
        for decision in plan.decisions
    )
