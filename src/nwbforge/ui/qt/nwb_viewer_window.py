"""Standalone NWB viewer window for read-only file inspection."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QSplitter, QTreeWidget, QTreeWidgetItem

from nwbforge.app.services.nwb_viewer import NwbFileController, NwbTreeNode, NwbViewerError
from nwbforge.app.services.nwb_viewer_rich import BaseRichNodeRenderer, NwbWidgetsPanelRenderer
from nwbforge.ui.qt.nwb_detail_pane import NwbDetailPane
from nwbforge.ui.qt.styling import apply_window_chrome


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
        apply_window_chrome(self)

        self._controller = controller or NwbFileController()
        self._rich_renderer = rich_renderer or NwbWidgetsPanelRenderer()

        self._tree = QTreeWidget(self)
        self._tree.setHeaderLabels(("NWB Node", "Type"))
        self._tree.setAlternatingRowColors(True)
        self._tree.setUniformRowHeights(True)
        self._tree.itemExpanded.connect(self._handle_item_expanded)
        self._tree.currentItemChanged.connect(self._handle_current_item_changed)

        self._detail_pane = NwbDetailPane(self)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(self._tree)
        splitter.addWidget(self._detail_pane)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        self.setCentralWidget(splitter)

        self._build_menus()
        self.statusBar().showMessage("Open an NWB file to inspect it.")

        if file_path is not None:
            self.open_file(file_path)
        self._update_rich_preview_action()

    @property
    def controller(self) -> NwbFileController:
        return self._controller

    @property
    def tree_widget(self) -> QTreeWidget:
        return self._tree

    @property
    def detail_pane(self) -> NwbDetailPane:
        return self._detail_pane

    def closeEvent(self, event) -> None:  # noqa: N802
        if hasattr(self._rich_renderer, "close"):
            self._rich_renderer.close()
        self._controller.close()
        super().closeEvent(event)

    def open_file(self, file_path: Path) -> bool:
        try:
            root_nodes = self._controller.open_file(file_path)
        except NwbViewerError as exc:
            self._show_error("NWB Viewer Error", exc)
            return False

        self._populate_root_nodes(root_nodes)
        self.statusBar().showMessage(f"Loaded {file_path.name} (read-only).")
        self.setWindowTitle(f"NWB Viewer - {file_path.name}")
        return True

    def reload_file(self) -> bool:
        try:
            root_nodes = self._controller.reload()
        except NwbViewerError as exc:
            self._show_error("NWB Viewer Error", exc)
            return False

        self._populate_root_nodes(root_nodes)
        file_path = self._controller.file_path
        if file_path is not None:
            self.statusBar().showMessage(f"Reloaded {file_path.name} (read-only).")
        return True

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        self._open_action = QAction("Open NWB...", self)
        self._open_action.triggered.connect(self._open_file_from_dialog)
        file_menu.addAction(self._open_action)

        self._reload_action = QAction("Reload", self)
        self._reload_action.triggered.connect(self.reload_file)
        file_menu.addAction(self._reload_action)

        self._close_action = QAction("Close", self)
        self._close_action.triggered.connect(self.close)
        file_menu.addAction(self._close_action)

        render_menu = self.menuBar().addMenu("&Render")
        self._open_rich_preview_action = QAction("Open Rich Preview", self)
        self._open_rich_preview_action.triggered.connect(self._open_rich_preview_for_current_node)
        render_menu.addAction(self._open_rich_preview_action)

        view_menu = self.menuBar().addMenu("&View")
        self._expand_all_action = QAction("Expand All", self)
        self._expand_all_action.triggered.connect(self._tree.expandAll)
        view_menu.addAction(self._expand_all_action)

        self._collapse_all_action = QAction("Collapse All", self)
        self._collapse_all_action.triggered.connect(self._collapse_to_default)
        view_menu.addAction(self._collapse_all_action)

        self._expand_children_action = QAction("Expand Children", self)
        self._expand_children_action.triggered.connect(self._expand_current_children)
        view_menu.addAction(self._expand_children_action)

        self._collapse_subtree_action = QAction("Collapse Subtree", self)
        self._collapse_subtree_action.triggered.connect(self._collapse_current_subtree)
        view_menu.addAction(self._collapse_subtree_action)

    def _open_file_from_dialog(self) -> None:
        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open NWB File",
            str(Path.cwd()),
            "NWB files (*.nwb);;All files (*)",
        )
        if selected_path:
            self.open_file(Path(selected_path))

    def _populate_root_nodes(self, root_nodes: tuple[NwbTreeNode, ...]) -> None:
        self._tree.clear()
        self._detail_pane.clear()
        for node in root_nodes:
            self._tree.addTopLevelItem(self._build_tree_item(node))
        self._collapse_to_default()

    def _collapse_to_default(self) -> None:
        self._tree.collapseAll()
        default_path = self._controller.default_expanded_path
        if default_path is None:
            return
        item = self._find_item_by_path(default_path)
        if item is not None:
            item.setExpanded(True)
            self._tree.setCurrentItem(item)

    def _build_tree_item(self, node: NwbTreeNode) -> QTreeWidgetItem:
        item = QTreeWidgetItem((node.label, node.node_type))
        item.setData(0, Qt.ItemDataRole.UserRole, node.path)
        item.setData(0, Qt.ItemDataRole.UserRole + 1, False)
        if node.child_count > 0:
            item.addChild(QTreeWidgetItem(("Loading...", "")))
        return item

    def _populate_item_children(self, item: QTreeWidgetItem) -> None:
        if item.data(0, Qt.ItemDataRole.UserRole + 1):
            return
        node_path = item.data(0, Qt.ItemDataRole.UserRole)
        children = self._controller.children_for_path(node_path)
        item.takeChildren()
        for child in children:
            item.addChild(self._build_tree_item(child))
        item.setData(0, Qt.ItemDataRole.UserRole + 1, True)

    def _handle_item_expanded(self, item: QTreeWidgetItem) -> None:
        self._populate_item_children(item)

    def _handle_current_item_changed(self, current: QTreeWidgetItem | None, previous: QTreeWidgetItem | None) -> None:
        del previous
        if current is None:
            self._detail_pane.clear()
            self._update_rich_preview_action()
            return
        self._populate_item_children(current)
        node_path = current.data(0, Qt.ItemDataRole.UserRole)
        try:
            detail = self._controller.detail_for_path(node_path)
        except NwbViewerError as exc:
            self._show_error("NWB Viewer Error", exc)
            return
        self._detail_pane.render_detail(detail)
        self._update_rich_preview_action()

    def _expand_current_children(self) -> None:
        item = self._tree.currentItem()
        if item is None:
            return
        self._populate_item_children(item)
        item.setExpanded(True)
        for index in range(item.childCount()):
            item.child(index).setExpanded(True)

    def _collapse_current_subtree(self) -> None:
        item = self._tree.currentItem()
        if item is None:
            return
        self._collapse_item_recursively(item)

    def _collapse_item_recursively(self, item: QTreeWidgetItem) -> None:
        for index in range(item.childCount()):
            self._collapse_item_recursively(item.child(index))
        item.setExpanded(False)

    def _find_item_by_path(self, path: str) -> QTreeWidgetItem | None:
        for index in range(self._tree.topLevelItemCount()):
            found = self._find_item_recursive(self._tree.topLevelItem(index), path)
            if found is not None:
                return found
        return None

    def _find_item_recursive(self, item: QTreeWidgetItem, path: str) -> QTreeWidgetItem | None:
        if item.data(0, Qt.ItemDataRole.UserRole) == path:
            return item
        self._populate_item_children(item)
        for index in range(item.childCount()):
            found = self._find_item_recursive(item.child(index), path)
            if found is not None:
                return found
        return None

    def _show_error(self, title: str, error: NwbViewerError) -> None:
        self.statusBar().showMessage(error.message)
        message_box = QMessageBox(self)
        message_box.setIcon(QMessageBox.Icon.Warning)
        message_box.setWindowTitle(title)
        message_box.setText(error.message)
        if error.detail:
            message_box.setDetailedText(error.detail)
        message_box.open()

    def _current_node(self) -> NwbTreeNode | None:
        current = self._tree.currentItem()
        if current is None:
            return None
        node_path = current.data(0, Qt.ItemDataRole.UserRole)
        try:
            return self._controller.node_for_path(node_path)
        except Exception:
            return None

    def _update_rich_preview_action(self) -> None:
        status = self._rich_renderer.status_for_node(self._current_node())
        self._open_rich_preview_action.setEnabled(status.is_available and status.is_supported)
        self._open_rich_preview_action.setStatusTip(status.message)
        self._open_rich_preview_action.setToolTip(status.message)

    def _open_rich_preview_for_current_node(self) -> None:
        node = self._current_node()
        if node is None:
            return
        try:
            session = self._rich_renderer.launch_for_node(node)
        except NwbViewerError as exc:
            self._show_error("Rich Preview Error", exc)
            return
        self.statusBar().showMessage(f"Opened rich preview at {session.url}")
