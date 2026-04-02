"""Optional rich renderers for the standalone NWB viewer."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
from types import ModuleType
from typing import Any, Protocol
import webbrowser

from nwbforge.app.services.nwb_viewer import NwbTreeNode, NwbViewerError


@dataclass(frozen=True, slots=True)
class NwbRichRendererStatus:
    """Availability and support status for an optional rich renderer."""

    renderer_name: str
    is_available: bool
    is_supported: bool
    message: str


class NwbRichRenderSession(Protocol):
    """Running rich-render session handle."""

    @property
    def url(self) -> str:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


@dataclass(slots=True)
class PanelRenderSession:
    """Panel-backed rich render session."""

    url: str
    _server: Any

    def close(self) -> None:
        if self._server is not None:
            self._server.stop()


class BaseRichNodeRenderer:
    """Optional richer renderer interface for NWB viewer nodes."""

    renderer_name = "base"

    def status_for_node(self, node: NwbTreeNode | None) -> NwbRichRendererStatus:
        raise NotImplementedError

    def launch_for_node(self, node: NwbTreeNode) -> NwbRichRenderSession:
        raise NotImplementedError


class NwbWidgetsPanelRenderer(BaseRichNodeRenderer):
    """Optional `nwbwidgets + Panel` rich renderer."""

    renderer_name = "nwbwidgets-panel"

    def __init__(self) -> None:
        self._last_session: PanelRenderSession | None = None

    def status_for_node(self, node: NwbTreeNode | None) -> NwbRichRendererStatus:
        if node is None:
            return NwbRichRendererStatus(
                renderer_name=self.renderer_name,
                is_available=self._is_available(),
                is_supported=False,
                message="Select an NWB node to preview it with the optional renderer.",
            )
        if not self._is_available():
            return NwbRichRendererStatus(
                renderer_name=self.renderer_name,
                is_available=False,
                is_supported=False,
                message="Optional rich preview requires the 'nwbwidgets' and 'panel' packages.",
            )
        return NwbRichRendererStatus(
            renderer_name=self.renderer_name,
            is_available=True,
            is_supported=True,
            message="Open the selected node in an optional nwbwidgets/Panel preview.",
        )

    def launch_for_node(self, node: NwbTreeNode) -> NwbRichRenderSession:
        if not self._is_available():
            raise NwbViewerError(
                "Rich preview is not available.",
                "Install the optional 'nwbwidgets' and 'panel' packages to enable rich previews.",
            )

        panel_module, nwbwidgets_module = self._load_modules()
        panel_module.extension("ipywidgets")
        widget = nwbwidgets_module.nwb2widget(node.object_ref)
        panel_view = panel_module.panel(widget)
        server = self._serve_view(panel_module, panel_view, title=f"NWB Rich Preview - {node.label}")
        session = PanelRenderSession(url=self._server_url(server), _server=server)
        webbrowser.open_new_tab(session.url)
        self._close_last_session()
        self._last_session = session
        return session

    def close(self) -> None:
        self._close_last_session()

    def _close_last_session(self) -> None:
        if self._last_session is not None:
            self._last_session.close()
        self._last_session = None

    @staticmethod
    def _serve_view(panel_module: ModuleType, panel_view: Any, *, title: str) -> Any:
        return panel_module.serve(panel_view, title=title, show=False, start=True, threaded=True, port=0)

    @staticmethod
    def _server_url(server: Any) -> str:
        if hasattr(server, "address") and hasattr(server, "port"):
            address = server.address or "127.0.0.1"
            return f"http://{address}:{server.port}/"
        if hasattr(server, "url"):
            return str(server.url)
        raise NwbViewerError("Rich preview server did not expose a usable URL.")

    @staticmethod
    def _load_modules() -> tuple[ModuleType, ModuleType]:
        panel_module = importlib.import_module("panel")
        nwbwidgets_module = importlib.import_module("nwbwidgets")
        return panel_module, nwbwidgets_module

    @staticmethod
    def _is_available() -> bool:
        try:
            importlib.import_module("panel")
            importlib.import_module("nwbwidgets")
        except Exception:
            return False
        return True
