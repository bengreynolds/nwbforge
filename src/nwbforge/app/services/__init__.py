"""Concrete application services."""

from __future__ import annotations

from importlib import import_module

from nwbforge.app.services.errors import (
    AdapterSelectionError,
    AssemblyConfigurationError,
    ReviewDecisionError,
    SourceNotFoundError,
)
from nwbforge.app.services.file_preview import FilePreviewKind, FilePreviewResult, FilePreviewTable, LocalFilePreviewService
from nwbforge.app.services.models import ConversionExecution, ConversionPreview, ReviewSubmission
from nwbforge.app.services.settings import UiSettings, UiSettingsService

__all__ = [
    "AdapterSelectionError",
    "AssemblyConfigurationError",
    "ConversionExecution",
    "ConversionPipelineService",
    "ConversionPreview",
    "ExecutionReviewService",
    "FilePreviewKind",
    "FilePreviewResult",
    "FilePreviewTable",
    "JsonSessionAssemblyWorkspaceStore",
    "JsonSessionAssemblyProjectStore",
    "LocalFilePreviewService",
    "BaseRichNodeRenderer",
    "NwbDetailTable",
    "NwbFileController",
    "NwbNodeDetail",
    "NwbRichRendererStatus",
    "NwbRichRenderSession",
    "NwbTreeModel",
    "NwbTreeNode",
    "NwbViewerError",
    "NwbWidgetsPanelRenderer",
    "NeuroConvSupportedExecutionService",
    "PanelRenderSession",
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

_LAZY_EXPORTS = {
    "ConversionPipelineService": ("nwbforge.app.services.pipeline", "ConversionPipelineService"),
    "ExecutionReviewService": ("nwbforge.app.services.review", "ExecutionReviewService"),
    "JsonSessionAssemblyWorkspaceStore": (
        "nwbforge.app.services.session_assembly",
        "JsonSessionAssemblyWorkspaceStore",
    ),
    "JsonSessionAssemblyProjectStore": (
        "nwbforge.app.services.projects",
        "JsonSessionAssemblyProjectStore",
    ),
    "BaseRichNodeRenderer": ("nwbforge.app.services.nwb_viewer_rich", "BaseRichNodeRenderer"),
    "NwbDetailTable": ("nwbforge.app.services.nwb_viewer", "NwbDetailTable"),
    "NwbFileController": ("nwbforge.app.services.nwb_viewer", "NwbFileController"),
    "NwbNodeDetail": ("nwbforge.app.services.nwb_viewer", "NwbNodeDetail"),
    "NwbRichRendererStatus": ("nwbforge.app.services.nwb_viewer_rich", "NwbRichRendererStatus"),
    "NwbRichRenderSession": ("nwbforge.app.services.nwb_viewer_rich", "NwbRichRenderSession"),
    "NwbTreeModel": ("nwbforge.app.services.nwb_viewer", "NwbTreeModel"),
    "NwbTreeNode": ("nwbforge.app.services.nwb_viewer", "NwbTreeNode"),
    "NwbViewerError": ("nwbforge.app.services.nwb_viewer", "NwbViewerError"),
    "NwbWidgetsPanelRenderer": ("nwbforge.app.services.nwb_viewer_rich", "NwbWidgetsPanelRenderer"),
    "NeuroConvSupportedExecutionService": (
        "nwbforge.app.services.supported_execution",
        "NeuroConvSupportedExecutionService",
    ),
    "PanelRenderSession": ("nwbforge.app.services.nwb_viewer_rich", "PanelRenderSession"),
    "PackageManagementController": ("nwbforge.app.services.package_management", "PackageManagementController"),
    "RegistrySourceInspectionService": (
        "nwbforge.app.services.inspection",
        "RegistrySourceInspectionService",
    ),
    "SessionAssemblyDraft": ("nwbforge.app.services.session_assembly", "SessionAssemblyDraft"),
    "SessionAssemblyIssue": ("nwbforge.app.services.session_assembly", "SessionAssemblyIssue"),
    "SessionAssemblyProjectDocument": ("nwbforge.app.services.projects", "SessionAssemblyProjectDocument"),
    "SessionAssemblyService": ("nwbforge.app.services.session_assembly", "SessionAssemblyService"),
    "SessionAssemblySource": ("nwbforge.app.services.session_assembly", "SessionAssemblySource"),
    "SessionAssemblyWorkspace": ("nwbforge.app.services.session_assembly", "SessionAssemblyWorkspace"),
    "SessionPersistenceService": ("nwbforge.app.services.persistence", "SessionPersistenceService"),
    "SessionProvenanceService": ("nwbforge.app.services.provenance", "SessionProvenanceService"),
}


def __getattr__(name: str):
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    try:
        module = import_module(target[0])
        export = getattr(module, target[1])
    except (AttributeError, ImportError):
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    globals()[name] = export
    return export
