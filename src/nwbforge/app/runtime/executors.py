"""Background executors for running conversion and install work off the UI thread."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from nwbforge.app.packages import (
    PackageInstallProgressCallback,
    PackageInstallProgressEvent,
    PackageInstallationService,
    PackageInstallRequest,
    PackageInstallResult,
    PackageInstallRuntimeError,
    PackageInstallStage,
)
from nwbforge.app.logging import get_logger, log_event
from nwbforge.app.runtime.contracts import ConversionExecutor, PackageInstallationExecutor
from nwbforge.app.runtime.models import PipelineProgressEvent, PipelineRuntimeError, PipelineStage, ProgressCallback
from nwbforge.app.services.models import ConversionPreview
from nwbforge.domain.models import ConversionSession

if TYPE_CHECKING:
    from nwbforge.app.services.pipeline import ConversionPipelineService


class ThreadedConversionExecutor(ConversionExecutor):
    """Run conversion work in a thread pool and surface runtime-safe errors."""

    _logger = get_logger(__name__)

    def __init__(
        self,
        pipeline_service: ConversionPipelineService,
        *,
        max_workers: int = 1,
        thread_name_prefix: str = "nwbforge",
    ) -> None:
        self._pipeline_service = pipeline_service
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=thread_name_prefix,
        )

    def submit_preview(
        self,
        session: ConversionSession,
        *,
        progress_callback: ProgressCallback | None = None,
    ) -> Future[ConversionPreview]:
        log_event(
            self._logger,
            logging.INFO,
            "Queued preview execution.",
            session_id=session.session_id,
            pathway=session.pathway.value,
        )
        self._emit(
            progress_callback,
            PipelineProgressEvent(
                session_id=session.session_id,
                stage=PipelineStage.QUEUED,
                percent_complete=0,
                message="Preview queued.",
            ),
        )
        return self._executor.submit(self._run_preview, session, progress_callback)

    def submit_execute(
        self,
        preview: ConversionPreview,
        output_path: Path,
        *,
        progress_callback: ProgressCallback | None = None,
    ) -> Future:
        log_event(
            self._logger,
            logging.INFO,
            "Queued conversion execution.",
            session_id=preview.session.session_id,
            output_path=str(output_path),
        )
        self._emit(
            progress_callback,
            PipelineProgressEvent(
                session_id=preview.session.session_id,
                stage=PipelineStage.QUEUED,
                percent_complete=0,
                message="Execution queued.",
            ),
        )
        return self._executor.submit(self._run_execute, preview, output_path, progress_callback)

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)

    def _run_preview(
        self,
        session: ConversionSession,
        progress_callback: ProgressCallback | None,
    ) -> ConversionPreview:
        try:
            log_event(
                self._logger,
                logging.DEBUG,
                "Running preview in background executor.",
                session_id=session.session_id,
            )
            return self._pipeline_service.build_preview(
                session,
                progress_callback=progress_callback,
            )
        except PipelineRuntimeError:
            raise
        except Exception as exc:
            log_event(
                self._logger,
                logging.ERROR,
                "Preview execution failed.",
                session_id=session.session_id,
                detail=str(exc),
            )
            raise PipelineRuntimeError(
                stage=PipelineStage.FAILED,
                user_message="Preview generation failed.",
                session_id=session.session_id,
                detail=str(exc),
            ) from exc

    def _run_execute(
        self,
        preview: ConversionPreview,
        output_path: Path,
        progress_callback: ProgressCallback | None,
    ):
        try:
            log_event(
                self._logger,
                logging.DEBUG,
                "Running conversion in background executor.",
                session_id=preview.session.session_id,
                output_path=str(output_path),
            )
            return self._pipeline_service.execute(
                preview,
                output_path,
                progress_callback=progress_callback,
            )
        except PipelineRuntimeError:
            raise
        except Exception as exc:
            log_event(
                self._logger,
                logging.ERROR,
                "Conversion execution failed.",
                session_id=preview.session.session_id,
                output_path=str(output_path),
                detail=str(exc),
            )
            raise PipelineRuntimeError(
                stage=PipelineStage.FAILED,
                user_message="Conversion execution failed.",
                session_id=preview.session.session_id,
                detail=str(exc),
            ) from exc

    @staticmethod
    def _emit(
        progress_callback: ProgressCallback | None,
        event: PipelineProgressEvent,
    ) -> None:
        if progress_callback is not None:
            progress_callback(event)


class ThreadedPackageInstallationExecutor(PackageInstallationExecutor):
    """Run package-install work in a thread pool for future setup/package UI."""

    _logger = get_logger(__name__)

    def __init__(
        self,
        installation_service: PackageInstallationService,
        *,
        max_workers: int = 1,
        thread_name_prefix: str = "nwbforge-packages",
    ) -> None:
        self._installation_service = installation_service
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=thread_name_prefix,
        )

    def submit_install(
        self,
        request: PackageInstallRequest,
        *,
        progress_callback: PackageInstallProgressCallback | None = None,
    ) -> Future[PackageInstallResult]:
        route_names = request.routes
        log_event(
            self._logger,
            logging.INFO,
            "Queued package installation.",
            install_mode=request.mode.value,
            preset=request.preset.value if request.preset is not None else None,
            route_names=route_names,
        )
        self._emit_package_progress(
            progress_callback,
            PackageInstallProgressEvent(
                stage=PackageInstallStage.QUEUED,
                percent_complete=0,
                message="Package installation queued.",
                route_names=route_names,
            ),
        )
        return self._executor.submit(self._run_install, request, progress_callback)

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)

    def _run_install(
        self,
        request: PackageInstallRequest,
        progress_callback: PackageInstallProgressCallback | None,
    ) -> PackageInstallResult:
        try:
            log_event(
                self._logger,
                logging.DEBUG,
                "Running package installation in background executor.",
                install_mode=request.mode.value,
                preset=request.preset.value if request.preset is not None else None,
                route_names=request.routes,
            )
            return self._installation_service.execute_install(
                request,
                progress_callback=progress_callback,
            )
        except PackageInstallRuntimeError:
            raise
        except Exception as exc:
            log_event(
                self._logger,
                logging.ERROR,
                "Package installation execution failed.",
                route_names=request.routes,
                detail=str(exc),
            )
            raise PackageInstallRuntimeError(
                stage=PackageInstallStage.FAILED,
                user_message="Package installation failed.",
                detail=str(exc),
                route_names=request.routes,
            ) from exc

    @staticmethod
    def _emit_package_progress(
        progress_callback: PackageInstallProgressCallback | None,
        event: PackageInstallProgressEvent,
    ) -> None:
        if progress_callback is not None:
            progress_callback(event)
