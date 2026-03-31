"""Application-service errors."""


class SourceNotFoundError(LookupError):
    """Raised when a requested source is not attached to a session."""


class AdapterSelectionError(LookupError):
    """Raised when adapter selection is missing, invalid, or ambiguous."""
