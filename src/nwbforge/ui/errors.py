"""Shared user-facing error translation for the UI layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from nwbforge.app.packages import PackageInstallRuntimeError
from nwbforge.app.runtime import PipelineRuntimeError


@dataclass(frozen=True, slots=True)
class UserFacingError:
    """A UI-safe error payload with concise message and optional detail."""

    title: str
    message: str
    detail: str | None = None
    category: str = "general"


class UiErrorPresenter(Protocol):
    """Protocol for turning runtime exceptions into UI-safe messages."""

    def present(self, error: BaseException) -> UserFacingError:
        """Translate the given exception into a user-facing payload."""


class DefaultUiErrorPresenter:
    """Translate known runtime exceptions into consistent UI-facing messages."""

    def present(self, error: BaseException) -> UserFacingError:
        if isinstance(error, PipelineRuntimeError):
            return UserFacingError(
                title="Conversion Error",
                message=error.user_message,
                detail=error.detail,
                category="conversion",
            )

        if isinstance(error, PackageInstallRuntimeError):
            return UserFacingError(
                title="Package Installation Error",
                message=error.user_message,
                detail=error.detail,
                category="packages",
            )

        if isinstance(error, ValueError):
            return UserFacingError(
                title="Invalid Action",
                message=str(error),
                category="validation",
            )

        return UserFacingError(
            title="Unexpected Error",
            message="An unexpected error occurred. See logs for details.",
            detail=str(error),
            category="unexpected",
        )
