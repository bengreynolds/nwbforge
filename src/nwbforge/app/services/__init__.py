"""Concrete application services."""

from __future__ import annotations

from nwbforge.app.services.errors import (
    AdapterSelectionError,
    AssemblyConfigurationError,
    ReviewDecisionError,
    SourceNotFoundError,
)
from nwbforge.app.services.inspection import RegistrySourceInspectionService
from nwbforge.app.services.models import ConversionExecution, ConversionPreview, ReviewSubmission
from nwbforge.app.services.persistence import SessionPersistenceService
from nwbforge.app.services.pipeline import ConversionPipelineService
from nwbforge.app.services.projects import JsonSessionAssemblyProjectStore, SessionAssemblyProjectDocument
from nwbforge.app.services.provenance import SessionProvenanceService
from nwbforge.app.services.review import ExecutionReviewService
from nwbforge.app.services.session_assembly import (
    JsonSessionAssemblyWorkspaceStore,
    SessionAssemblyDraft,
    SessionAssemblyIssue,
    SessionAssemblyService,
    SessionAssemblySource,
    SessionAssemblyWorkspace,
)
from nwbforge.app.services.settings import UiSettings, UiSettingsService
from nwbforge.app.services.supported_execution import NeuroConvSupportedExecutionService

__all__ = [
    "AdapterSelectionError",
    "AssemblyConfigurationError",
    "ConversionExecution",
    "ConversionPipelineService",
    "ConversionPreview",
    "ExecutionReviewService",
    "JsonSessionAssemblyWorkspaceStore",
    "JsonSessionAssemblyProjectStore",
    "NeuroConvSupportedExecutionService",
    "PackageManagementController",
    "RegistrySourceInspectionService",
    "ReviewDecisionError",
    "ReviewSubmission",
    "SessionAssemblyDraft",
    "SessionAssemblyIssue",
    "SessionAssemblyProjectDocument",
    "SessionAssemblyService",
    "SessionAssemblySource",
    "SessionAssemblyWorkspace",
    "SessionPersistenceService",
    "SessionProvenanceService",
    "SourceNotFoundError",
    "UiSettings",
    "UiSettingsService",
]


def __getattr__(name: str):
    if name == "PackageManagementController":
        from nwbforge.app.services.package_management import PackageManagementController

        return PackageManagementController
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
