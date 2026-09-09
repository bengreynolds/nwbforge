"""Validation-layer implementations."""

from __future__ import annotations

from importlib import import_module

from nwbforge.validation.policies import DefaultValidationReviewPolicyService, ValidationPolicy
from nwbforge.validation.reports import JsonValidationReportService
from nwbforge.validation.reviews import JsonExecutionReviewArtifactService

__all__ = [
    "ArtifactValidationService",
    "CompositeValidationService",
    "DefaultValidationReviewPolicyService",
    "JsonExecutionReviewArtifactService",
    "JsonValidationReportService",
    "NWBInspectorValidationService",
    "PyNWBSchemaValidationService",
    "ValidationPolicy",
]

_LAZY_EXPORTS = {
    "ArtifactValidationService": ("nwbforge.validation.services", "ArtifactValidationService"),
    "CompositeValidationService": ("nwbforge.validation.services", "CompositeValidationService"),
    "NWBInspectorValidationService": ("nwbforge.validation.services", "NWBInspectorValidationService"),
    "PyNWBSchemaValidationService": ("nwbforge.validation.services", "PyNWBSchemaValidationService"),
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
