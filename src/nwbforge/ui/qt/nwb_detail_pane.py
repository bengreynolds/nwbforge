"""Detail pane for standalone NWB viewer windows."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nwbforge.app.services.nwb_viewer import NwbNodeDetail
from nwbforge.ui.qt.styling import build_page_header


class NwbDetailPane(QWidget):
    """Render structured node-detail content for the NWB viewer."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        (
            self._header_frame,
            self._title_label,
            self._path_label,
            self._detail_badge_label,
        ) = build_page_header(
            "No node selected.",
            "",
            badge_text="Detail",
            parent=self,
        )
        self._type_label = QLabel("", self)
        self._type_label.setProperty("role", "muted")
        self._path_label.setProperty("role", "muted")

        self._summary_table = QTableWidget(0, 2, self)
        self._summary_table.setHorizontalHeaderLabels(("Field", "Value"))
        self._summary_table.verticalHeader().setVisible(False)
        self._summary_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._summary_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._summary_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._summary_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._summary_table.setAlternatingRowColors(True)

        self._detail_table = QTableWidget(0, 0, self)
        self._detail_table.verticalHeader().setVisible(False)
        self._detail_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._detail_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._detail_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._detail_table.setAlternatingRowColors(True)

        self._detail_text = QPlainTextEdit(self)
        self._detail_text.setReadOnly(True)

        layout.addWidget(self._header_frame)
        layout.addWidget(self._type_label)
        layout.addWidget(self._summary_table, 1)
        layout.addWidget(self._detail_table, 2)
        layout.addWidget(self._detail_text, 2)

        self.clear()

    def clear(self) -> None:
        self._title_label.setText("No node selected.")
        if self._detail_badge_label is not None:
            self._detail_badge_label.setText("Detail")
        self._type_label.clear()
        self._path_label.clear()
        self._summary_table.setRowCount(0)
        self._detail_table.setRowCount(0)
        self._detail_table.setColumnCount(0)
        self._detail_table.hide()
        self._detail_text.clear()
        self._detail_text.hide()

    def render_detail(self, detail: NwbNodeDetail) -> None:
        self._title_label.setText(detail.title)
        if self._detail_badge_label is not None:
            self._detail_badge_label.setText(detail.node_type)
        self._type_label.setText(f"Type: {detail.node_type}")
        self._path_label.setText(f"Path: {detail.path}")

        self._summary_table.setRowCount(len(detail.summary_rows))
        for row_index, (key, value) in enumerate(detail.summary_rows):
            self._summary_table.setItem(row_index, 0, QTableWidgetItem(key))
            self._summary_table.setItem(row_index, 1, QTableWidgetItem(value))

        if detail.table is not None:
            self._detail_table.setColumnCount(len(detail.table.headers))
            self._detail_table.setHorizontalHeaderLabels(detail.table.headers)
            self._detail_table.setRowCount(len(detail.table.rows))
            for row_index, row in enumerate(detail.table.rows):
                for column_index, value in enumerate(row):
                    self._detail_table.setItem(row_index, column_index, QTableWidgetItem(value))
            self._detail_table.show()
        else:
            self._detail_table.hide()
            self._detail_table.setRowCount(0)
            self._detail_table.setColumnCount(0)

        if detail.text_content:
            self._detail_text.setPlainText(detail.text_content)
            self._detail_text.show()
        else:
            self._detail_text.clear()
            self._detail_text.hide()
