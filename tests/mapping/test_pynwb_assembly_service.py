from pathlib import Path

from pynwb import NWBHDF5IO

from nwbforge.domain.enums import ConversionPathway, ValueOrigin
from nwbforge.domain.models import (
    ConversionSession,
    MappingDecision,
    MappingPlan,
    NormalizedMetadataBundle,
    NormalizedSessionMetadata,
    NormalizedSubject,
    NormalizedValue,
)
from nwbforge.mapping import PyNWBAssemblyService
from nwbforge.domain.enums import MappingAction


def test_pynwb_assembly_service_writes_minimal_nwb_file(tmp_path: Path) -> None:
    metadata = NormalizedMetadataBundle(
        subject=NormalizedSubject(
            subject_id=NormalizedValue("mouse-01", origin=ValueOrigin.ADAPTER_EXTRACTED),
            species=NormalizedValue("Mus musculus", origin=ValueOrigin.ADAPTER_EXTRACTED),
            sex=NormalizedValue("U", origin=ValueOrigin.ADAPTER_EXTRACTED),
            age=NormalizedValue("P90D", origin=ValueOrigin.ADAPTER_EXTRACTED),
            description=NormalizedValue("Test subject", origin=ValueOrigin.ADAPTER_EXTRACTED),
            date_of_birth=NormalizedValue(
                "2025-12-31T08:00:00-07:00",
                origin=ValueOrigin.ADAPTER_EXTRACTED,
            ),
        ),
        session=NormalizedSessionMetadata(
            session_id=NormalizedValue("session-01", origin=ValueOrigin.ADAPTER_EXTRACTED),
            session_description=NormalizedValue("Visual task", origin=ValueOrigin.USER_SUPPLIED),
            experiment_description=NormalizedValue(
                "Visual stimulation task",
                origin=ValueOrigin.USER_SUPPLIED,
            ),
            start_time=NormalizedValue("2026-03-31T10:15:00-06:00", origin=ValueOrigin.ADAPTER_EXTRACTED),
            experimenter=NormalizedValue("Researcher, Alice", origin=ValueOrigin.USER_SUPPLIED),
            institution=NormalizedValue("Test University", origin=ValueOrigin.USER_SUPPLIED),
            lab=NormalizedValue("Test Lab", origin=ValueOrigin.USER_SUPPLIED),
            keywords=(NormalizedValue("vision", origin=ValueOrigin.ADAPTER_EXTRACTED),),
        ),
    )
    plan = MappingPlan(
        pathway=ConversionPathway.SUPPORTED,
        decisions=(
            MappingDecision(
                source_key="session.session_description",
                target_path="NWBFile.session_description",
                action=MappingAction.DIRECT,
                rationale="Required field.",
            ),
        ),
    )
    output_path = tmp_path / "written.nwb"

    artifacts = PyNWBAssemblyService().write(
        session=ConversionSession(session_id="sess-001", pathway=ConversionPathway.SUPPORTED),
        metadata=metadata,
        mapping_plan=plan,
        output_path=str(output_path),
    )

    assert artifacts[0].location == output_path
    with NWBHDF5IO(str(output_path), "r") as io:
        nwbfile = io.read()
        assert nwbfile.session_description == "Visual task"
        assert nwbfile.experiment_description == "Visual stimulation task"
        assert nwbfile.identifier == "session-01"
        assert nwbfile.subject.subject_id == "mouse-01"
        assert nwbfile.subject.sex == "U"
        assert nwbfile.subject.age == "P90D"
        assert nwbfile.subject.description == "Test subject"
        assert "vision" in nwbfile.keywords
