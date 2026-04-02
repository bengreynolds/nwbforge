"""Embedded read-only NWB viewer widget for the main desktop workspace."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nwbforge.app.services.nwb_viewer import NwbFileController, NwbTreeNode, NwbViewerError
from nwbforge.app.services.nwb_viewer_rich import BaseRichNodeRenderer, NwbWidgetsPanelRenderer
from nwbforge.ui.qt.nwb_detail_pane import NwbDetailPane
from nwbforge.ui.qt.styling import build_page_header


class NwbViewerWidget(QWidget):
    """Embedded read-only NWB viewer with lazy tree/detail browsing."""

    status_message_changed = Signal(str)

    def __init__(
        self,
        controller: NwbFileController | None = None,
        *,
        rich_renderer: BaseRichNodeRenderer | None = None,
        file_path: Path | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller or NwbFileController()
        self._rich_renderer = rich_renderer or NwbWidgetsPanelRenderer()

        (
            self._header_frame,
            self._header_title_label,
            self._header_subtitle_label,
            self._header_badge_label,
        ) = build_page_header(
            "NWB Viewer",
            "Open any valid NWB file in read-only mode and inspect its semantic structure without leaving the desktop workspace.",
            badge_text="Read Only",
            parent=self,
        )
        self._status_label = QLabel("Open an NWB file to inspect it.", self)
        self._status_label.setProperty("role", "muted")
        self._status_label.setWordWrap(True)

        self._open_button = QPushButton("Open NWB...", self)
        self._open_button.clicked.connect(self._open_file_from_dialog)
        self._reload_button = QPushButton("Reload", self)
        self._reload_button.setProperty("secondary", True)
        self._reload_button.clicked.connect(self.reload_file)
        self._rich_preview_button = QPushButton("Open Rich Preview", self)
        self._rich_preview_button.setProperty("secondary", True)
        self._rich_preview_button.clicked.connect(self._open_rich_preview_for_current_node)

        action_row = QHBoxLayout()
        action_row.addWidget(self._open_button)
        action_row.addWidget(self._reload_button)
        action_row.addWidget(self._rich_preview_button)
        action_row.addStretch(1)

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
        self._splitter = splitter

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self._header_frame)
        layout.addLayout(action_row)
        layout.addWidget(self._status_label)
        layout.addWidget(splitter, 1)

        if file_path is not None:
            self.open_file(file_path)
        else:
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

    def close(self) -> bool:  # noqa: A003
        if hasattr(self._rich_renderer, "close"):
            self._rich_renderer.close()
        self._controller.close()
        return super().close()

    def open_file(self, file_path: Path) -> bool:
        try:
            root_nodes = self._controller.open_file(file_path)
        except NwbViewerError as exc:
            self._show_error("NWB Viewer Error", exc)
            return False

        self._populate_root_nodes(root_nodes)
        self._header_title_label.setText(file_path.name)
        self._header_subtitle_label.setText(f"{file_path.resolve()} | read-only inspection")
        if self._header_badge_label is not None:
            self._header_badge_label.setText("Read Only")
        self._set_status_message(f"Loaded {file_path.name} (read-only).")
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
            self._set_status_message(f"Reloaded {file_path.name} (read-only).")
        return True

    def _set_status_message(self, message: str) -> None:
        self._status_label.setText(message)
        self.status_message_changed.emit(message)

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
        self._set_status_message(error.message)
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
        self._rich_preview_button.setEnabled(status.is_available and status.is_supported)
        self._rich_preview_button.setToolTip(status.message)

    def _open_rich_preview_for_current_node(self) -> None:
        node = self._current_node()
        if node is None:
            return
        try:
            session = self._rich_renderer.launch_for_node(node)
        except NwbViewerError as exc:
            self._show_error("Rich Preview Error", exc)
            return
        self._set_status_message(f"Opened rich preview at {session.url}")
