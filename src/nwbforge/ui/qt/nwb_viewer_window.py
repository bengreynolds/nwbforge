"""Standalone wrapper window for the read-only NWB viewer widget."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow

from nwbforge.app.services.nwb_viewer import NwbFileController
from nwbforge.app.services.nwb_viewer_rich import BaseRichNodeRenderer, NwbWidgetsPanelRenderer
from nwbforge.ui.qt.nwb_detail_pane import NwbDetailPane
from nwbforge.ui.qt.nwb_viewer_widget import NwbViewerWidget


class NwbViewerWindow(QMainWindow):
    """Top-level read-only NWB viewer window."""

    def __init__(
        self,
        controller: NwbFileController | None = None,
        *,
        rich_renderer: BaseRichNodeRenderer | None = None,
        file_path: Path | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("NWB Viewer")
        self.resize(1100, 760)

        self._viewer_widget = NwbViewerWidget(
            controller=controller,
            rich_renderer=rich_renderer or NwbWidgetsPanelRenderer(),
            file_path=file_path,
            parent=self,
        )
        self._viewer_widget.status_message_changed.connect(self.statusBar().showMessage)
        self.setCentralWidget(self._viewer_widget)
        self._build_menus()
        self.statusBar().showMessage(self._viewer_widget._status_label.text())
        if file_path is not None:
            self.setWindowTitle(f"NWB Viewer - {file_path.name}")

    @property
    def controller(self) -> NwbFileController:
        return self._viewer_widget.controller

    @property
    def tree_widget(self):
        return self._viewer_widget.tree_widget

    @property
    def detail_pane(self) -> NwbDetailPane:
        return self._viewer_widget.detail_pane

    def open_file(self, file_path: Path) -> bool:
        opened = self._viewer_widget.open_file(file_path)
        if opened:
            self.setWindowTitle(f"NWB Viewer - {file_path.name}")
        return opened

    def reload_file(self) -> bool:
        return self._viewer_widget.reload_file()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._viewer_widget.close()
        super().closeEvent(event)

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        self._open_action = QAction("Open NWB...", self)
        self._open_action.triggered.connect(self._viewer_widget._open_file_from_dialog)
        file_menu.addAction(self._open_action)

        self._reload_action = QAction("Reload", self)
        self._reload_action.triggered.connect(self._viewer_widget.reload_file)
        file_menu.addAction(self._reload_action)

        self._close_action = QAction("Close", self)
        self._close_action.triggered.connect(self.close)
        file_menu.addAction(self._close_action)

        render_menu = self.menuBar().addMenu("&Render")
        self._open_rich_preview_action = QAction("Open Rich Preview", self)
        self._open_rich_preview_action.triggered.connect(self._viewer_widget._open_rich_preview_for_current_node)
        render_menu.addAction(self._open_rich_preview_action)
