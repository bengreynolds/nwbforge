"""Optional rich renderers for the standalone NWB viewer."""

from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType
from typing import Any, Protocol
import webbrowser

from nwbforge.app.runtime.python_env import import_modules_without_user_site
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
                message=(
                    "Optional rich preview requires the 'viewer_rich' support target "
                    "(`nwbwidgets` + `panel`). Install it from Optional Workflow Support or "
                    "`pip install -e .[viewer_rich]`."
                ),
            )
        return NwbRichRendererStatus(
            renderer_name=self.renderer_name,
            is_available=True,
            is_supported=True,
            message="Open the selected node in the optional NWB rich preview renderer.",
        )

    def launch_for_node(self, node: NwbTreeNode) -> NwbRichRenderSession:
        if not self._is_available():
            raise NwbViewerError(
                "Rich preview is not available.",
                "Install the optional 'viewer_rich' support target (`nwbwidgets` + `panel`) to enable rich previews.",
            )

        panel_module, nwbwidgets_module = self._load_modules()
        panel_module.extension("ipywidgets")
        widget = nwbwidgets_module.nwb2widget(node.object_ref)
        panel_view = panel_module.panel(widget)
        server = self._serve_view(panel_module, panel_view, title=f"NWB Rich Preview - {node.label}")
        session = PanelRenderSession(url=self._server_url(server, panel_module), _server=server)
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
    def _server_url(server: Any, panel_module: ModuleType | None = None) -> str:
        direct_url = NwbWidgetsPanelRenderer._server_url_from_candidate(server)
        if direct_url is not None:
            return direct_url

        resolved_server = NwbWidgetsPanelRenderer._resolve_panel_server(server, panel_module)
        if resolved_server is not None:
            resolved_url = NwbWidgetsPanelRenderer._server_url_from_candidate(resolved_server)
            if resolved_url is not None:
                return resolved_url
        raise NwbViewerError("Rich preview server did not expose a usable URL.")

    @staticmethod
    def _resolve_panel_server(server: Any, panel_module: ModuleType | None) -> Any | None:
        server_id = getattr(server, "server_id", None)
        if not server_id or panel_module is None:
            return None
        panel_state = getattr(panel_module, "state", None)
        panel_servers = getattr(panel_state, "_servers", None)
        if isinstance(panel_servers, dict):
            entry = panel_servers.get(server_id)
            if isinstance(entry, tuple) and entry:
                return entry[0]
        return None

    @staticmethod
    def _server_url_from_candidate(candidate: Any) -> str | None:
        if candidate is None:
            return None
        address = getattr(candidate, "address", None)
        port = getattr(candidate, "port", None)
        if port:
            host = address or "127.0.0.1"
            return f"http://{host}:{port}/"
        for attribute_name in ("url", "urls"):
            normalized = NwbWidgetsPanelRenderer._normalize_url_value(getattr(candidate, attribute_name, None))
            if normalized is not None:
                return normalized
        return None

    @staticmethod
    def _normalize_url_value(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            for nested in value.values():
                normalized = NwbWidgetsPanelRenderer._normalize_url_value(nested)
                if normalized is not None:
                    return normalized
            return None
        if isinstance(value, (list, tuple, set)):
            for nested in value:
                normalized = NwbWidgetsPanelRenderer._normalize_url_value(nested)
                if normalized is not None:
                    return normalized
            return None
        stringified = str(value).strip()
        if stringified.startswith("http://") or stringified.startswith("https://"):
            return stringified
        return None

    @staticmethod
    def _load_modules() -> tuple[ModuleType, ModuleType]:
        _ensure_hdmf_docval_compat()
        return import_modules_without_user_site(
            "panel",
            "nwbwidgets",
            purge_prefixes=("panel", "nwbwidgets", "ndx_icephys_meta", "hdmf", "pynwb"),
        )

    @staticmethod
    def _is_available() -> bool:
        try:
            NwbWidgetsPanelRenderer._load_modules()
        except Exception:
            return False
        return True


def _ensure_hdmf_docval_compat() -> None:
    """Patch legacy docval helpers expected by optional viewer dependencies."""

    (hdmf_utils_module,) = import_modules_without_user_site(
        "hdmf.utils",
        purge_prefixes=("hdmf", "pynwb"),
    )
    if not hasattr(hdmf_utils_module, "call_docval_func"):
        def call_docval_func(func: Any, kwargs: dict[str, Any]) -> Any:
            return func(**kwargs)

        hdmf_utils_module.call_docval_func = call_docval_func
    if not hasattr(hdmf_utils_module, "fmt_docval_args"):
        def fmt_docval_args(func: Any, kwargs: dict[str, Any]) -> tuple[tuple[Any, ...], dict[str, Any]]:
            del func
            return (), dict(kwargs)

        hdmf_utils_module.fmt_docval_args = fmt_docval_args
