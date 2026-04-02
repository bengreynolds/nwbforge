from pathlib import Path
from math import isnan

from pynwb import NWBHDF5IO

from nwbforge.domain.enums import ConversionPathway, ValueOrigin
from nwbforge.domain.models import (
    AcquisitionStream,
    ConversionSession,
    MappingDecision,
    MappingPlan,
    NormalizedDevice,
    NormalizedMetadataBundle,
    NormalizedSessionMetadata,
    NormalizedSubject,
    NormalizedTimeIntervalTable,
    NormalizedValue,
    TimeIntervalRow,
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
        devices=(
            NormalizedDevice(
                device_id="camera-1",
                name=NormalizedValue("Camera One", origin=ValueOrigin.ADAPTER_EXTRACTED),
                description=NormalizedValue("Behavior camera", origin=ValueOrigin.ADAPTER_EXTRACTED),
                manufacturer=NormalizedValue("Acme Imaging", origin=ValueOrigin.ADAPTER_EXTRACTED),
            ),
        ),
        acquisition_streams=(
            AcquisitionStream(
                stream_id="lick-trace",
                name=NormalizedValue("Lick Trace", origin=ValueOrigin.ADAPTER_EXTRACTED),
                modality="behavior",
                source_ids=("source-1",),
                description=NormalizedValue("Example lick signal", origin=ValueOrigin.ADAPTER_EXTRACTED),
                metadata={
                    "data": NormalizedValue([0.1, 0.2, 0.3], origin=ValueOrigin.ADAPTER_EXTRACTED),
                    "unit": NormalizedValue("a.u.", origin=ValueOrigin.ADAPTER_EXTRACTED),
                    "rate": NormalizedValue(10.0, origin=ValueOrigin.ADAPTER_EXTRACTED),
                },
            ),
            AcquisitionStream(
                stream_id="animal-position",
                name=NormalizedValue("Animal Position", origin=ValueOrigin.ADAPTER_EXTRACTED),
                modality="behavior",
                source_ids=("source-1",),
                description=NormalizedValue("Tracked animal position", origin=ValueOrigin.ADAPTER_EXTRACTED),
                metadata={
                    "behavior_type": NormalizedValue("position", origin=ValueOrigin.ADAPTER_EXTRACTED),
                    "data": NormalizedValue(
                        [[0.0, 1.0], [1.5, 2.5], [3.0, 4.0]],
                        origin=ValueOrigin.ADAPTER_EXTRACTED,
                    ),
                    "unit": NormalizedValue("meters", origin=ValueOrigin.ADAPTER_EXTRACTED),
                    "reference_frame": NormalizedValue(
                        "origin at top-left corner of arena",
                        origin=ValueOrigin.ADAPTER_EXTRACTED,
                    ),
                    "rate": NormalizedValue(20.0, origin=ValueOrigin.ADAPTER_EXTRACTED),
                },
            ),
        ),
        time_interval_tables=(
            NormalizedTimeIntervalTable(
                table_id="trials",
                table_name=NormalizedValue("trials", origin=ValueOrigin.ADAPTER_EXTRACTED),
                table_description=NormalizedValue(
                    "Experimental trials",
                    origin=ValueOrigin.ADAPTER_EXTRACTED,
                ),
                rows=(
                    TimeIntervalRow(
                        row_id="0",
                        source_ids=("source-2",),
                        start_time=NormalizedValue(0.5, origin=ValueOrigin.ADAPTER_EXTRACTED),
                        metadata={
                            "condition": NormalizedValue("left", origin=ValueOrigin.ADAPTER_EXTRACTED),
                        },
                    ),
                    TimeIntervalRow(
                        row_id="1",
                        source_ids=("source-2",),
                        start_time=NormalizedValue(1.2, origin=ValueOrigin.ADAPTER_EXTRACTED),
                        metadata={
                            "condition": NormalizedValue("right", origin=ValueOrigin.ADAPTER_EXTRACTED),
                        },
                    ),
                ),
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
        assert "Camera One" in nwbfile.devices
        assert nwbfile.devices["Camera One"].description == "Behavior camera"
        assert "behavior" in nwbfile.acquisition
        behavior = nwbfile.acquisition["behavior"]
        assert "Lick Trace" in behavior.time_series
        assert list(behavior.time_series["Lick Trace"].data[:]) == [0.1, 0.2, 0.3]
        assert "position" in nwbfile.acquisition
        position = nwbfile.acquisition["position"]
        assert "Animal Position" in position.spatial_series
        assert position.spatial_series["Animal Position"].data[:].tolist() == [
            [0.0, 1.0],
            [1.5, 2.5],
            [3.0, 4.0],
        ]
        assert nwbfile.trials is not None
        assert nwbfile.trials["start_time"][:].tolist() == [0.5, 1.2]
        stop_times = nwbfile.trials["stop_time"][:].tolist()
        assert stop_times[0] == 1.2
        assert isnan(stop_times[1])
        assert nwbfile.trials["condition"][:].tolist() == ["left", "right"]
        assert "vision" in nwbfile.keywords
