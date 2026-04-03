"""Shared Qt styling helpers for the NWB Forge desktop UI."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


_NWB_FORGE_STYLESHEET = """
QWidget {
    background: #f4f1ea;
    color: #1e2a2d;
    font-size: 13px;
}

QMainWindow, QDialog {
    background: #ede8df;
}

QMenuBar {
    background: #f7f4ee;
    border-bottom: 1px solid #d6cec0;
    padding: 4px 8px;
}

QMenuBar::item {
    background: transparent;
    padding: 6px 10px;
    border-radius: 6px;
}

QMenuBar::item:selected,
QMenu::item:selected {
    background: #d9e7e0;
}

QMenu {
    background: #fffdf8;
    border: 1px solid #d6cec0;
    padding: 6px;
}

QMenu::item {
    padding: 7px 24px 7px 10px;
    border-radius: 6px;
}

QStatusBar {
    background: #f7f4ee;
    border-top: 1px solid #d6cec0;
}

QGroupBox {
    background: #fcfaf6;
    border: 1px solid #d9d0c2;
    border-radius: 12px;
    margin-top: 14px;
    padding: 16px 14px 14px 14px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #47605f;
}

QLabel[role="pageTitle"] {
    font-size: 24px;
    font-weight: 700;
    color: #17333a;
}

QLabel[role="sectionTitle"] {
    font-size: 16px;
    font-weight: 700;
    color: #234248;
}

QLabel[role="muted"] {
    color: #5f6e71;
}

QLabel[role="badge"] {
    background: #1f5c64;
    color: #f8fffd;
    border-radius: 12px;
    padding: 5px 10px;
    font-size: 11px;
    font-weight: 700;
}

QLabel[role="cardLabel"] {
    color: #607072;
    font-size: 11px;
    font-weight: 700;
}

QLabel[role="cardValue"] {
    color: #18353a;
    font-size: 18px;
    font-weight: 700;
}

QFrame[role="headerCard"] {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 #fbf8f2,
        stop: 1 #efe6d8
    );
    border: 1px solid #d9d0c2;
    border-radius: 16px;
}

QFrame[role="metricCard"] {
    background: #fffdf9;
    border: 1px solid #ddd4c5;
    border-radius: 12px;
}

QFrame[role="metricCard"][accent="true"] {
    background: #e7f0ec;
    border: 1px solid #a9c2b7;
}

QLineEdit, QPlainTextEdit, QListWidget, QTreeWidget, QTableWidget, QComboBox {
    background: #fffdfa;
    border: 1px solid #d1c7b8;
    border-radius: 10px;
    padding: 7px 9px;
    selection-background-color: #b9d3c6;
    selection-color: #17333a;
}

QListWidget, QTreeWidget, QTableWidget {
    alternate-background-color: #f6f2ea;
}

QListWidget::item,
QTreeWidget::item {
    padding: 5px 3px;
    border-radius: 6px;
}

QTabWidget::pane {
    border: 1px solid #d9d0c2;
    border-radius: 12px;
    background: #fcfaf6;
    top: -1px;
}

QTabBar::tab {
    background: #ebe4d7;
    border: 1px solid #d5cbbd;
    border-bottom: none;
    padding: 8px 14px;
    margin-right: 4px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    color: #556769;
    font-weight: 600;
}

QTabBar::tab:selected {
    background: #fcfaf6;
    color: #17333a;
}

QPushButton {
    background: #1f5c64;
    color: #f7fbfa;
    border: none;
    border-radius: 10px;
    padding: 8px 14px;
    font-weight: 600;
}

QPushButton:hover {
    background: #17484f;
}

QPushButton:pressed {
    background: #123940;
}

QPushButton:disabled {
    background: #c0c8c8;
    color: #eef2f2;
}

QPushButton[secondary="true"] {
    background: #e6ece8;
    color: #1e3538;
    border: 1px solid #bfd0c8;
}

QPushButton[secondary="true"]:hover {
    background: #d7e4de;
}

QPushButton[danger="true"] {
    background: #8b4a43;
}

QPushButton[danger="true"]:hover {
    background: #733a34;
}

QProgressBar {
    min-width: 180px;
    background: #e7dfd2;
    border: 1px solid #cfc3b1;
    border-radius: 10px;
    text-align: center;
    color: #17333a;
}

QProgressBar::chunk {
    background: #2f7a72;
    border-radius: 9px;
}

QDockWidget {
    color: #17333a;
}

QDockWidget::title {
    background: #f7f4ee;
    border-bottom: 1px solid #d6cec0;
    padding: 8px 10px;
    text-align: left;
    font-weight: 700;
}

QHeaderView::section {
    background: #efe8dc;
    color: #35545a;
    padding: 6px;
    border: none;
    border-right: 1px solid #d9d0c2;
    border-bottom: 1px solid #d9d0c2;
    font-weight: 700;
}

QSplitter::handle {
    background: #ddd4c5;
    width: 3px;
    height: 3px;
}
"""


def apply_nwbforge_application_style(app: QApplication) -> None:
    """Apply the shared desktop style to the active application."""

    if app.property("nwbforgeStyleApplied"):
        return
    app.setStyle("Fusion")
    app.setStyleSheet(_NWB_FORGE_STYLESHEET)
    app.setProperty("nwbforgeStyleApplied", True)


def apply_window_chrome(widget: QWidget) -> None:
    """Ensure top-level windows use the shared application style."""

    app = QApplication.instance()
    if app is not None:
        apply_nwbforge_application_style(app)
    widget.setContentsMargins(0, 0, 0, 0)


def build_page_header(
    title: str,
    subtitle: str,
    *,
    badge_text: str | None = None,
    parent: QWidget | None = None,
) -> tuple[QFrame, QLabel, QLabel, QLabel | None]:
    """Build a reusable page header card with optional badge text."""

    frame = QFrame(parent)
    frame.setProperty("role", "headerCard")
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(14)

    text_column = QVBoxLayout()
    text_column.setContentsMargins(0, 0, 0, 0)
    text_column.setSpacing(4)

    title_label = QLabel(title, frame)
    title_label.setProperty("role", "pageTitle")
    subtitle_label = QLabel(subtitle, frame)
    subtitle_label.setWordWrap(True)
    subtitle_label.setProperty("role", "muted")

    text_column.addWidget(title_label)
    text_column.addWidget(subtitle_label)
    layout.addLayout(text_column, 1)

    badge_label: QLabel | None = None
    if badge_text is not None:
        badge_label = QLabel(badge_text, frame)
        badge_label.setProperty("role", "badge")
        layout.addWidget(badge_label, 0, Qt.AlignmentFlag.AlignTop)

    return frame, title_label, subtitle_label, badge_label


def build_metric_card(
    title: str,
    value: str,
    *,
    accent: bool = False,
    parent: QWidget | None = None,
) -> tuple[QFrame, QLabel]:
    """Build a small summary card for dashboard-style metrics."""

    frame = QFrame(parent)
    frame.setProperty("role", "metricCard")
    if accent:
        frame.setProperty("accent", True)

    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(4)

    label = QLabel(title, frame)
    label.setProperty("role", "cardLabel")
    value_label = QLabel(value, frame)
    value_label.setProperty("role", "cardValue")
    value_label.setWordWrap(True)

    layout.addWidget(label)
    layout.addWidget(value_label)
    layout.addStretch(1)
    return frame, value_label
