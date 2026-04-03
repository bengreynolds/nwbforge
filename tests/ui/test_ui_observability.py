from __future__ import annotations

import json
import logging
from pathlib import Path

from nwbforge.app.packages import PackageInstallRuntimeError, PackageInstallStage
from nwbforge.app.runtime import PipelineRuntimeError, PipelineStage
from nwbforge.ui import (
    CompositeUiLogSink,
    DefaultUiErrorPresenter,
    FileUiLogSink,
    InMemoryUiLogSink,
    UiLogEntry,
    UiLogHandler,
)


def test_default_ui_error_presenter_translates_known_runtime_errors() -> None:
    presenter = DefaultUiErrorPresenter()

    conversion_error = presenter.present(
        PipelineRuntimeError(
            stage=PipelineStage.FAILED,
            user_message="Conversion failed.",
            detail="bad metadata",
        )
    )
    package_error = presenter.present(
        PackageInstallRuntimeError(
            stage=PackageInstallStage.FAILED,
            user_message="Package install failed.",
            detail="pip failed",
        )
    )

    assert conversion_error.category == "conversion"
    assert conversion_error.detail == "bad metadata"
    assert package_error.category == "packages"
    assert package_error.detail == "pip failed"


def test_ui_log_handler_captures_structured_context() -> None:
    sink = InMemoryUiLogSink()
    handler = UiLogHandler(sink)
    logger = logging.getLogger("tests.ui.observability")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    try:
        logger.info("hello", extra={"nwbforge_context": {"session_id": "abc", "stage": "mapping"}})
    finally:
        logger.removeHandler(handler)
        handler.close()

    entries = sink.entries()
    assert len(entries) == 1
    assert entries[0].context == {"session_id": "abc", "stage": "mapping"}
    assert entries[0].level_name == "INFO"


def test_composite_ui_log_sink_mirrors_to_file(tmp_path: Path) -> None:
    memory_sink = InMemoryUiLogSink()
    file_path = tmp_path / "ui.log.jsonl"
    sink = CompositeUiLogSink(memory_sink, FileUiLogSink(file_path))
    handler = UiLogHandler(sink)
    logger = logging.getLogger("tests.ui.observability.file")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    try:
        logger.info("persisted entry", extra={"nwbforge_context": {"route": "deeplabcut"}})
    finally:
        logger.removeHandler(handler)
        handler.close()

    entries = memory_sink.entries()
    assert len(entries) == 1
    payload = json.loads(file_path.read_text(encoding="utf-8").strip())
    assert payload["message"] == "persisted entry"
    assert payload["context"] == {"route": "deeplabcut"}


def test_file_ui_log_sink_serializes_non_json_context_values(tmp_path: Path) -> None:
    file_path = tmp_path / "ui.log.jsonl"
    sink = FileUiLogSink(file_path)

    sink.append(
        UiLogEntry(
            level_name="INFO",
            message="persisted entry",
            logger_name="tests.ui.observability.file",
            context={"path": tmp_path, "marker": object()},
        )
    )

    payload = json.loads(file_path.read_text(encoding="utf-8").strip())
    assert payload["context"]["path"] == str(tmp_path)
    assert isinstance(payload["context"]["marker"], str)
