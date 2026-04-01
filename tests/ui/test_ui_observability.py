from __future__ import annotations

import logging

from nwbforge.app.packages import PackageInstallRuntimeError, PackageInstallStage
from nwbforge.app.runtime import PipelineRuntimeError, PipelineStage
from nwbforge.ui import DefaultUiErrorPresenter, InMemoryUiLogSink, UiLogHandler


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
