import json
from pathlib import Path

from pynwb import NWBHDF5IO, TimeSeries

from nwbforge.adapters import (
    AdapterRegistry,
    NeuroConvCsvTimeIntervalsAdapter,
    SessionManifestAdapter,
)
from nwbforge.adapters.neuroconv import NeuroConvDirectConversionAdapter
from nwbforge.adapters.supported.workflows import NeuroConvSpikeGLXPhyWorkflowAdapter
from nwbforge.app.services import (
    NeuroConvSupportedExecutionService,
    RegistrySourceInspectionService,
    SessionProvenanceService,
)
from nwbforge.app.services.models import ConversionPreview
from nwbforge.app.services.pipeline import ConversionPipelineService
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.enums import ValueOrigin
from nwbforge.domain.models import (
    ConversionSession,
    ExtractionResult,
    MappingPlan,
    NormalizedMetadataBundle,
    NormalizedSessionMetadata,
    NormalizedValue,
    SourceReference,
)
from nwbforge.mapping import PyNWBAssemblyService, RuleBasedMappingPlanner
from nwbforge.normalization import RuleBasedNormalizationService
from nwbforge.validation import (
    ArtifactValidationService,
    CompositeValidationService,
    DefaultValidationReviewPolicyService,
    JsonValidationReportService,
    NWBInspectorValidationService,
    PyNWBSchemaValidationService,
)


class _WorkflowDirectAdapter(NeuroConvDirectConversionAdapter):
    source_types = (SourceType.FILE, SourceType.DIRECTORY)
    supported_suffixes = ()
    source_path_kwarg = "file_path"

    def __init__(self, *, adapter_id: str, series_name: str) -> None:
        self.adapter_id = adapter_id
        self.display_name = adapter_id
        self.version = "0.1.0"
        self.interface_cls = object
        self.record_type = adapter_id
        self._series_name = series_name

    def build_interface(self, source, config):
        return None

    def extract(self, *, source, interface, config):
        return {}, (), ()

    def write_conversion(self, *, session, source, output_path, nwbfile):
        del session, source
        nwbfile.add_acquisition(
            TimeSeries(
                name=self._series_name,
                data=[1.0, 2.0, 3.0],
                unit="a.u.",
                rate=1.0,
                description=f"workflow series {self._series_name}",
            )
        )
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with NWBHDF5IO(str(output_file), "w") as io:
            io.write(nwbfile)
        return ()


def test_supported_execution_service_writes_neuroconv_trial_output(tmp_path: Path) -> None:
    manifest_path = tmp_path / "session_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "session": {
                    "session_id": "session-01",
                    "description": "Visual task recording",
                    "start_time": "2026-03-31T10:15:00-06:00",
                    "experiment_description": "Visual stimulation task",
                },
                "subject": {
                    "subject_id": "mouse-01",
                    "species": "Mus musculus",
                    "sex": "U",
                    "age": "P90D",
                },
            }
        ),
        encoding="utf-8",
    )
    csv_path = tmp_path / "trials.csv"
    csv_path.write_text("start_time,stop_time,condition\n0.5,1.0,left\n1.2,1.8,right\n", encoding="utf-8")

    session = ConversionSession(
        session_id="sess-supported-exec",
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
    pipeline = ConversionPipelineService(
        inspection_service=RegistrySourceInspectionService(registry),
        normalization_service=RuleBasedNormalizationService(),
        mapping_planner=RuleBasedMappingPlanner(),
        provenance_service=SessionProvenanceService(),
        validation_service=CompositeValidationService(
            (
                ArtifactValidationService(),
                PyNWBSchemaValidationService(),
                NWBInspectorValidationService(),
            )
        ),
        validation_policy_service=DefaultValidationReviewPolicyService(),
        validation_report_service=JsonValidationReportService(),
        assembly_service=PyNWBAssemblyService(),
        supported_execution_service=NeuroConvSupportedExecutionService(registry),
    )

    preview = pipeline.build_preview(session)
    output_path = tmp_path / "generated" / "session.nwb"
    execution = pipeline.execute(preview, output_path)

    assert execution.validation_summary.is_passing() is True
    with NWBHDF5IO(str(output_path), "r") as io:
        nwbfile = io.read()
        assert nwbfile.session_description == "Visual task recording"
        assert nwbfile.subject is not None
        assert nwbfile.subject.subject_id == "mouse-01"
        assert nwbfile.trials is not None
        assert nwbfile.trials["condition"][:].tolist() == ["left", "right"]


def test_supported_execution_service_executes_combined_workflow_directly(tmp_path: Path) -> None:
    registry = AdapterRegistry()
    spikeglx_delegate = _WorkflowDirectAdapter(
        adapter_id="neuroconv_spikeglx",
        series_name="SpikeGLX Recording",
    )
    phy_delegate = _WorkflowDirectAdapter(
        adapter_id="neuroconv_phy_sorting",
        series_name="Phy Sorting",
    )
    workflow_adapter = NeuroConvSpikeGLXPhyWorkflowAdapter(
        delegates={
            "recording": spikeglx_delegate,
            "sorting": phy_delegate,
        }
    )
    registry.register(spikeglx_delegate)
    registry.register(phy_delegate)
    registry.register_workflow(workflow_adapter)

    session = ConversionSession(
        session_id="sess-workflow-exec",
        pathway=ConversionPathway.SUPPORTED,
        sources=(
            SourceReference(
                source_id="recording",
                location=tmp_path / "recording.bin",
                source_type=SourceType.FILE,
                label="SpikeGLX Recording",
                role="primary",
                adapter_hint="neuroconv_spikeglx",
            ),
            SourceReference(
                source_id="sorting",
                location=tmp_path / "sorting",
                source_type=SourceType.DIRECTORY,
                label="Phy Sorting",
                adapter_hint="neuroconv_phy_sorting",
            ),
        ),
    )
    preview = ConversionPreview(
        session=session,
        extraction_results=(
            ExtractionResult(
                source_id="recording",
                adapter_id="neuroconv_spikeglx",
                record_type="recording",
                fields={},
                issues=(),
                notes=(),
            ),
            ExtractionResult(
                source_id="sorting",
                adapter_id="neuroconv_phy_sorting",
                record_type="sorting",
                fields={},
                issues=(),
                notes=(),
            ),
        ),
        normalized_metadata=NormalizedMetadataBundle(
            session=NormalizedSessionMetadata(
                session_description=NormalizedValue("Workflow execution test", origin=ValueOrigin.USER_SUPPLIED),
                start_time=NormalizedValue("2026-04-03T10:15:00-06:00", origin=ValueOrigin.ADAPTER_EXTRACTED),
                session_id=NormalizedValue("sess-workflow-exec", origin=ValueOrigin.ADAPTER_EXTRACTED),
            )
        ),
        mapping_plan=MappingPlan(pathway=ConversionPathway.SUPPORTED),
        provenance_record=SessionProvenanceService().build_record(session, (), ()),
    )

    output_path = tmp_path / "generated" / "workflow.nwb"
    artifacts = NeuroConvSupportedExecutionService(registry).write(preview, output_path)

    assert artifacts[0].artifact_type == "nwb"
    with NWBHDF5IO(str(output_path), "r") as io:
        nwbfile = io.read()
        assert "SpikeGLX Recording" in nwbfile.acquisition
        assert "Phy Sorting" in nwbfile.acquisition
