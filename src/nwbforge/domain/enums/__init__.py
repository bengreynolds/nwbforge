"""Domain enums for workflow and review state."""

from enum import Enum


class StrEnum(str, Enum):
    """A small compatibility shim for string-valued enums."""

    def __str__(self) -> str:
        return self.value


class ConversionPathway(StrEnum):
    SUPPORTED = "supported"
    CUSTOM = "custom"
    HYBRID = "hybrid"


class SessionStatus(StrEnum):
    DRAFT = "draft"
    SOURCES_ADDED = "sources_added"
    INSPECTING = "inspecting"
    NORMALIZING = "normalizing"
    MAPPING = "mapping"
    REVIEW = "review"
    VALIDATING = "validating"
    READY_TO_WRITE = "ready_to_write"
    COMPLETED = "completed"
    FAILED = "failed"


class ReviewStatus(StrEnum):
    NOT_REVIEWED = "not_reviewed"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ValueOrigin(StrEnum):
    ADAPTER_EXTRACTED = "adapter_extracted"
    INFERRED = "inferred"
    USER_SUPPLIED = "user_supplied"
    LAB_PROFILE = "lab_profile"
    DEFAULTED = "defaulted"
    COMPUTED = "computed"


class SourceType(StrEnum):
    FILE = "file"
    DIRECTORY = "directory"
    MANIFEST = "manifest"
    SIDECAR = "sidecar"


class MappingAction(StrEnum):
    DIRECT = "direct"
    TRANSFORM = "transform"
    MERGE = "merge"
    DESCRIBE = "describe"
    EXTEND = "extend"
    OMIT = "omit"


class IssueSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
