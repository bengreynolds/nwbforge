"""Background executors for running conversion work off the UI thread."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from nwbforge.app.runtime.contracts import ConversionExecutor
from nwbforge.app.runtime.models import PipelineProgressEvent, PipelineRuntimeError, PipelineStage, ProgressCallback
from nwbforge.app.services import ConversionPipelineService, ConversionPreview
from nwbforge.domain.models import ConversionSession


class ThreadedConversionExecutor(ConversionExecutor):
    """Run conversion work in a thread pool and surface runtime-safe errors."""

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
            return self._pipeline_service.build_preview(
                session,
                progress_callback=progress_callback,
            )
        except PipelineRuntimeError:
            raise
        except Exception as exc:
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
            return self._pipeline_service.execute(
                preview,
                output_path,
                progress_callback=progress_callback,
            )
        except PipelineRuntimeError:
            raise
        except Exception as exc:
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
