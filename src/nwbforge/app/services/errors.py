"""Application-service errors."""


class SourceNotFoundError(LookupError):
    """Raised when a requested source is not attached to a session."""


class AdapterSelectionError(LookupError):
    """Raised when adapter selection is missing, invalid, or ambiguous."""


class AssemblyConfigurationError(RuntimeError):
    """Raised when execution is requested without a configured assembly service."""


class ReviewDecisionError(ValueError):
    """Raised when a review submission is inconsistent with the current validation outcome."""
