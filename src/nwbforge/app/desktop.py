"""Desktop application composition helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import logging

from nwbforge.adapters import AdapterRegistry, CustomJsonSessionAdapter, SessionManifestAdapter
from nwbforge.app.logging import get_logger, log_event
from nwbforge.app.packages.catalog import route_dependencies_available
from nwbforge.app.packages import (
    PackageCommandRunner,
    PackageInstallationService,
    PackageManagementService,
    SubprocessPackageCommandRunner,
)
from nwbforge.app.runtime import ThreadedConversionExecutor, ThreadedPackageInstallationExecutor
from nwbforge.app.services import (
    ConversionPipelineService,
    ExecutionReviewService,
    JsonSessionAssemblyWorkspaceStore,
    PackageManagementController,
    RegistrySourceInspectionService,
    SessionAssemblyService,
    SessionPersistenceService,
    SessionProvenanceService,
    UiSettingsService,
)
from nwbforge.app.services.settings import UiSettings
from nwbforge.domain.enums import ConversionPathway, SourceType
from nwbforge.domain.models import ConversionSession, SourceReference
from nwbforge.mapping import PyNWBAssemblyService, RuleBasedMappingPlanner
from nwbforge.normalization import RuleBasedNormalizationService
from nwbforge.persistence import JsonSessionSnapshotStore
from nwbforge.ui import (
    ConversionSessionScreenModel,
    DesktopShellModel,
    PackageInstallerScreenModel,
    SessionAssemblyScreenModel,
    SettingsScreenModel,
)
from nwbforge.validation import (
    ArtifactValidationService,
    CompositeValidationService,
    DefaultValidationReviewPolicyService,
    JsonExecutionReviewArtifactService,
    JsonValidationReportService,
    NWBInspectorValidationService,
    PyNWBSchemaValidationService,
)


@dataclass(frozen=True, slots=True)
class DesktopAppServices:
    """Composed desktop-application services and screen models."""

    repo_root: Path
    shell_model: DesktopShellModel
    settings_screen_model: SettingsScreenModel
    package_screen_model: PackageInstallerScreenModel
    session_assembly_screen_model: SessionAssemblyScreenModel
    conversion_screen_model: ConversionSessionScreenModel


LOGGER = get_logger(__name__)


def _all_routes_available(*route_names: str) -> bool:
    return all(route_dependencies_available(route_name) for route_name in route_names)


def build_adapter_registry() -> AdapterRegistry:
    """Build the default desktop adapter registry from available adapters."""

    registry = AdapterRegistry()
    registry.register(SessionManifestAdapter())
    registry.register(CustomJsonSessionAdapter())

    from nwbforge import adapters as adapters_module

    for adapter_name in (
        "NeuroConvCsvTimeIntervalsAdapter",
        "NeuroConvFicTracAdapter",
    ):
        adapter_cls = getattr(adapters_module, adapter_name, None)
        if adapter_cls is None:
            continue
        registry.register(adapter_cls())

    optional_routes = (
        ("alphaomega", "NeuroConvAlphaOmegaAdapter"),
        ("axon", "NeuroConvAxonAdapter"),
        ("axona", "NeuroConvAxonaAdapter"),
        ("biocam", "NeuroConvBiocamAdapter"),
        ("blackrock", "NeuroConvBlackrockAdapter"),
        ("blackrock", "NeuroConvBlackrockSortingAdapter"),
        ("brukertiff", "NeuroConvBrukerTiffSinglePlaneAdapter"),
        ("brukertiff", "NeuroConvBrukerTiffMultiPlaneAdapter"),
        ("caiman", "NeuroConvCaimanSegmentationAdapter"),
        ("cellexplorer", "NeuroConvCellExplorerSortingAdapter"),
        ("cnmfe", "NeuroConvCnmfeSegmentationAdapter"),
        ("excel", "NeuroConvExcelTimeIntervalsAdapter"),
        ("edf", "NeuroConvEdfAdapter"),
        ("extract", "NeuroConvExtractSegmentationAdapter"),
        ("femtonics", "NeuroConvFemtonicsAdapter"),
        ("image", "NeuroConvImageAdapter"),
        ("audio", "NeuroConvAudioAdapter"),
        ("videos", "NeuroConvVideoAdapter"),
        ("deeplabcut", "NeuroConvDeepLabCutAdapter"),
        ("inscopix", "NeuroConvInscopixAdapter"),
        ("inscopix", "NeuroConvInscopixSegmentationAdapter"),
        ("lightningpose", "NeuroConvLightningPoseAdapter"),
        ("kilosort", "NeuroConvKiloSortSortingAdapter"),
        ("mcsraw", "NeuroConvMCSRawAdapter"),
        ("maxone", "NeuroConvMaxOneAdapter"),
        ("mearec", "NeuroConvMEArecAdapter"),
        ("medpc", "NeuroConvMedPCAdapter"),
        ("neuralynx", "NeuroConvNeuralynxNvtAdapter"),
        ("sleap", "NeuroConvSLEAPAdapter"),
        ("intan", "NeuroConvIntanAdapter"),
        ("neuralynx", "NeuroConvNeuralynxAdapter"),
        ("neuralynx", "NeuroConvNeuralynxSortingAdapter"),
        ("neuroscope", "NeuroConvNeuroScopeAdapter"),
        ("neuroscope", "NeuroConvNeuroScopeSortingAdapter"),
        ("openephys_binary", "NeuroConvOpenEphysBinaryAnalogAdapter"),
        ("openephys_binary", "NeuroConvOpenEphysBinaryAdapter"),
        ("openephys_legacy", "NeuroConvOpenEphysLegacyAdapter"),
        ("plexon", "NeuroConvPlexonAdapter"),
        ("plexon", "NeuroConvPlexonSortingAdapter"),
        ("plexon2", "NeuroConvPlexon2Adapter"),
        ("phy", "NeuroConvPhySortingAdapter"),
        ("spike2", "NeuroConvSpike2Adapter"),
        ("spikegadgets", "NeuroConvSpikeGadgetsAdapter"),
        ("spikeglx", "NeuroConvSpikeGLXAdapter"),
        ("suite2p", "NeuroConvSuite2pSegmentationAdapter"),
        ("tdt", "NeuroConvTdtAdapter"),
        ("tdt_fiber_photometry", "NeuroConvTdtFiberPhotometryAdapter"),
        ("whitematter", "NeuroConvWhiteMatterAdapter"),
        ("hdf5", "NeuroConvHdf5ImagingAdapter"),
        ("micromanager", "NeuroConvMicroManagerTiffAdapter"),
        ("miniscope", "NeuroConvMiniscopeAdapter"),
        ("scanbox", "NeuroConvScanboxAdapter"),
        ("scanimage", "NeuroConvScanImageAdapter"),
        ("scanimage_legacy", "NeuroConvScanImageLegacyAdapter"),
        ("tiff", "NeuroConvTiffImagingAdapter"),
        ("thor", "NeuroConvThorAdapter"),
    )
    for route_name, adapter_name in optional_routes:
        if not route_dependencies_available(route_name):
            log_event(
                LOGGER,
                logging.DEBUG,
                "Skipping optional supported adapter because route dependencies are not installed.",
                route_name=route_name,
                adapter_name=adapter_name,
            )
            continue
        adapter_cls = getattr(adapters_module, adapter_name, None)
        if adapter_cls is None:
            log_event(
                LOGGER,
                logging.WARNING,
                "Route dependencies are installed but the adapter export is unavailable.",
                route_name=route_name,
                adapter_name=adapter_name,
            )
            continue
        registry.register(adapter_cls())

    workflow_routes = (
        (
            ("spikeglx", "phy"),
            "NeuroConvSpikeGLXPhyWorkflowAdapter",
            {
                "recording": "neuroconv_spikeglx",
                "sorting": "neuroconv_phy_sorting",
            },
        ),
        (
            ("tiff", "suite2p"),
            "NeuroConvTiffSuite2pWorkflowAdapter",
            {
                "imaging": "neuroconv_tiff_imaging",
                "segmentation": "neuroconv_suite2p_segmentation",
            },
        ),
        (
            ("openephys_binary", "deeplabcut"),
            "NeuroConvOpenEphysDeepLabCutWorkflowAdapter",
            {
                "recording": "neuroconv_openephys_binary",
                "behavior": "neuroconv_deeplabcut",
            },
        ),
    )
    for required_routes, workflow_name, delegate_map in workflow_routes:
        if not _all_routes_available(*required_routes):
            continue
        workflow_cls = getattr(adapters_module, workflow_name, None)
        if workflow_cls is None:
            continue
        try:
            delegates = {role: registry.get(adapter_id) for role, adapter_id in delegate_map.items()}
        except KeyError:
            continue
        registry.register_workflow(workflow_cls(delegates))

    return registry


def build_desktop_pipeline_service(registry: AdapterRegistry) -> ConversionPipelineService:
    """Build the real conversion pipeline used by the desktop shell."""

    assembly_service = PyNWBAssemblyService()
    from nwbforge.app.services import NeuroConvSupportedExecutionService

    return ConversionPipelineService(
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
        assembly_service=assembly_service,
        supported_execution_service=NeuroConvSupportedExecutionService(
            registry,
            base_assembly_service=assembly_service,
        ),
    )


def build_desktop_services(
    repo_root: Path,
    *,
    settings_path: Path | None = None,
    package_selection_path: Path | None = None,
    package_command_runner: PackageCommandRunner | None = None,
) -> DesktopAppServices:
    """Compose the real desktop service/model stack."""

    app_state_dir = repo_root / ".nwbforge"
    log_event(
        LOGGER,
        logging.INFO,
        "Building desktop service stack.",
        repo_root=str(repo_root),
        app_state_dir=str(app_state_dir),
    )
    settings_service = UiSettingsService(settings_path or app_state_dir / "ui-settings.json")
    settings_screen_model = SettingsScreenModel(settings_service)
    settings_screen_model.load()

    package_service = PackageManagementService(
        selection_path=package_selection_path or app_state_dir / "install-selection.json"
    )
    installation_service = PackageInstallationService(
        package_service,
        repo_root=repo_root,
        command_runner=package_command_runner or SubprocessPackageCommandRunner(),
    )
    package_executor = ThreadedPackageInstallationExecutor(installation_service)
    package_controller = PackageManagementController(package_service, package_executor)
    package_screen_model = PackageInstallerScreenModel(package_controller)

    registry = build_adapter_registry()
    session_assembly_screen_model = SessionAssemblyScreenModel(
        SessionAssemblyService(registry),
        workspace_store=JsonSessionAssemblyWorkspaceStore(app_state_dir / "session-assembly" / "draft.json"),
    )
    pipeline_service = build_desktop_pipeline_service(registry)
    conversion_executor = ThreadedConversionExecutor(pipeline_service)
    review_service = ExecutionReviewService(JsonExecutionReviewArtifactService())
    persistence_service = SessionPersistenceService(
        JsonSessionSnapshotStore(
            app_state_dir / "session-state",
            history_limit=settings_screen_model.state.applied_settings.snapshot_history_limit,
        )
    )
    conversion_screen_model = ConversionSessionScreenModel(
        conversion_executor,
        review_service=review_service,
        persistence_service=persistence_service,
        restore_latest_snapshot_on_load=settings_screen_model.state.applied_settings.restore_latest_snapshot_on_load,
    )

    return DesktopAppServices(
        repo_root=repo_root,
        shell_model=DesktopShellModel(),
        settings_screen_model=settings_screen_model,
        package_screen_model=package_screen_model,
        session_assembly_screen_model=session_assembly_screen_model,
        conversion_screen_model=conversion_screen_model,
    )


def load_manifest_session(location: Path) -> ConversionSession:
    """Create a supported-path session object for a manifest file or directory."""

    if location.is_dir():
        manifest_path = location / "session_manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest directory does not contain session_manifest.json: {location}")
        source_type = SourceType.DIRECTORY
        session_id = location.name
        source_location = location
    else:
        if location.name.lower() != "session_manifest.json":
            raise ValueError("Desktop launcher currently supports session_manifest.json sources only.")
        source_type = SourceType.FILE
        session_id = location.parent.name or location.stem
        source_location = location

    return ConversionSession(
        session_id=f"desktop-{session_id}",
        pathway=ConversionPathway.SUPPORTED,
        sources=(
            SourceReference(
                source_id="primary-source",
                location=source_location,
                source_type=source_type,
                label="Session manifest",
            ),
        ),
    )


def load_custom_session(location: Path) -> ConversionSession:
    """Create a custom-path session object for a custom session file or directory."""

    if location.is_dir():
        custom_path = location / "custom_session.json"
        if not custom_path.exists():
            raise FileNotFoundError(f"Custom session directory does not contain custom_session.json: {location}")
        source_type = SourceType.DIRECTORY
        session_id = location.name
        source_location = location
    else:
        if location.name.lower() != "custom_session.json":
            raise ValueError("Custom desktop sources must use the custom_session.json filename.")
        source_type = SourceType.FILE
        session_id = location.parent.name or location.stem
        source_location = location

    return ConversionSession(
        session_id=f"desktop-custom-{session_id}",
        pathway=ConversionPathway.CUSTOM,
        sources=(
            SourceReference(
                source_id="primary-source",
                location=source_location,
                source_type=source_type,
                label="Custom session JSON",
                adapter_hint="custom_json_session",
            ),
        ),
    )


def load_hybrid_session(location: Path) -> ConversionSession:
    """Create a hybrid-path session object from a desktop session descriptor."""

    if location.is_dir():
        descriptor_path = location / "hybrid_session.json"
        if not descriptor_path.exists():
            raise FileNotFoundError(f"Hybrid session directory does not contain hybrid_session.json: {location}")
    else:
        if location.name.lower() != "hybrid_session.json":
            raise ValueError("Hybrid desktop sources must use the hybrid_session.json filename.")
        descriptor_path = location

    payload = json.loads(descriptor_path.read_text(encoding="utf-8"))
    source_payloads = payload.get("sources")
    if not isinstance(source_payloads, list) or not source_payloads:
        raise ValueError("Hybrid session descriptor must define at least one source.")

    source_references: list[SourceReference] = []
    for index, source_payload in enumerate(source_payloads, start=1):
        if not isinstance(source_payload, dict):
            raise ValueError("Hybrid session source entries must be objects.")

        relative_location = source_payload.get("location")
        if not relative_location:
            raise ValueError("Hybrid session source entries must include a location.")

        resolved_location = (descriptor_path.parent / str(relative_location)).resolve()
        if not resolved_location.exists():
            raise FileNotFoundError(f"Hybrid session source does not exist: {resolved_location}")

        source_references.append(
            SourceReference(
                source_id=str(source_payload.get("source_id") or f"source-{index}"),
                location=resolved_location,
                source_type=SourceType.DIRECTORY if resolved_location.is_dir() else SourceType.FILE,
                label=str(source_payload.get("label") or resolved_location.name),
                role=str(source_payload.get("role") or "primary"),
                media_type=source_payload.get("media_type"),
                adapter_hint=source_payload.get("adapter_hint"),
            )
        )

    session_id = str(payload.get("session_id") or f"desktop-hybrid-{descriptor_path.parent.name or descriptor_path.stem}")
    notes_payload = payload.get("notes", ())
    notes = tuple(str(note) for note in notes_payload) if isinstance(notes_payload, list) else ()

    return ConversionSession(
        session_id=session_id,
        pathway=ConversionPathway.HYBRID,
        sources=tuple(source_references),
        title=payload.get("title"),
        notes=notes,
    )


def load_desktop_session(location: Path) -> ConversionSession:
    """Create a desktop session object by dispatching to the supported or custom loader."""

    if location.is_dir():
        if (location / "session_manifest.json").exists():
            return load_manifest_session(location)
        if (location / "custom_session.json").exists():
            return load_custom_session(location)
        if (location / "hybrid_session.json").exists():
            return load_hybrid_session(location)
        raise FileNotFoundError(
            "Session directory does not contain session_manifest.json, custom_session.json, or hybrid_session.json: "
            f"{location}"
        )

    name = location.name.lower()
    if name == "session_manifest.json":
        return load_manifest_session(location)
    if name == "custom_session.json":
        return load_custom_session(location)
    if name == "hybrid_session.json":
        return load_hybrid_session(location)
    raise ValueError(
        "Desktop session loader supports session_manifest.json, custom_session.json, and hybrid_session.json sources only."
    )


def ensure_demo_manifest(repo_root: Path) -> Path:
    """Create a real manifest-backed demo session for manual UI testing."""

    demo_dir = repo_root / ".nwbforge" / "demo-data"
    demo_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = demo_dir / "session_manifest.json"
    if manifest_path.exists():
        return manifest_path

    manifest_path.write_text(
        json.dumps(
            {
                "session": {
                    "session_id": "desktop-demo-001",
                    "description": "Demo NWB Forge desktop session",
                    "experiment_description": "Manifest-backed manual UI test",
                    "start_time": "2026-04-01T09:00:00-06:00",
                    "experimenter": "Researcher, Alice",
                    "institution": "Test Lab",
                },
                "subject": {
                    "subject_id": "demo-mouse-01",
                    "species": "Mus musculus",
                    "sex": "U",
                    "age": "P90D",
                    "description": "Demo subject",
                },
                "devices": [
                    {
                        "device_id": "camera-1",
                        "name": "Camera One",
                        "description": "Behavior camera",
                        "manufacturer": "Acme Imaging",
                    }
                ],
                "acquisition_streams": [
                    {
                        "stream_id": "lick-trace",
                        "name": "Lick Trace",
                        "modality": "behavior",
                        "description": "Example lick signal",
                        "data": [0.1, 0.2, 0.3],
                        "unit": "a.u.",
                        "rate": 10.0,
                    },
                    {
                        "stream_id": "animal-position",
                        "name": "Animal Position",
                        "modality": "behavior",
                        "behavior_type": "position",
                        "description": "Tracked animal position",
                        "data": [[0.0, 1.0], [1.5, 2.5], [3.0, 4.0]],
                        "unit": "meters",
                        "reference_frame": "origin at top-left corner of arena",
                        "rate": 20.0,
                    }
                ],
                "keywords": ["demo", "behavior"],
                "operator_note": "temporary desktop launcher",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return manifest_path


def build_default_log_file_path(repo_root: Path, settings: UiSettings | None = None) -> Path:
    """Return the default desktop shell log file path."""

    if settings is not None and settings.file_logging_enabled:
        return settings.log_file_path
    return repo_root / ".nwbforge" / "logs" / "desktop-ui.jsonl"


def resolve_startup_session_path(
    repo_root: Path,
    settings: UiSettings,
    *,
    requested_manifest: Path | None = None,
) -> Path:
    """Resolve the manifest path to load on desktop startup."""

    if requested_manifest is not None:
        return requested_manifest.resolve()

    if settings.last_open_session_path is not None and settings.last_open_session_path.exists():
        return settings.last_open_session_path

    return ensure_demo_manifest(repo_root)
