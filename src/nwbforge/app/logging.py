"""Structured logging helpers for NWB Forge runtime paths."""

from __future__ import annotations

import logging
from typing import Any


def get_logger(name: str) -> logging.Logger:
    """Return a standard application logger."""

    return logging.getLogger(name)


def log_event(
    logger: logging.Logger,
    level: int,
    message: str,
    **context: Any,
) -> None:
    """Emit a structured log record with stable context payload."""

    logger.log(level, message, extra={"nwbforge_context": context})
