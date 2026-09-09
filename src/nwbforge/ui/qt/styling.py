"""Shared Qt styling helpers for the NWB Forge desktop UI."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


#: Qt's QSS is a subset of CSS. `letter-spacing` and `text-transform` are NOT
#: supported and are silently ignored, so emphasis here is carried by weight,
#: size and colour only; anything that needs to read as a caption is cased in
#: Python instead.
_NWB_FORGE_STYLESHEET = """
QWidget {
    background: #f4f1ea;
    color: #1e2a2d;
    /* Named explicitly rather than inherited. Qt's default on Windows falls
       back through a stack that can land on MS Shell Dlg 2, which renders a
       full step smaller and without the hinting the rest of the desktop
       gets. */
    font-family: "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif;
    font-size: 13px;
}

/* The rule above paints EVERY widget opaque in the page colour, including
   labels and the plain QWidgets used as layout rows. Sat inside a group box
   (#fcfaf6) or a card (#fffdf9) those repaint the page colour behind their own
   text, which is the mismatched band showing behind every line on the
   conversion screen.

   Text and the containers that only exist to hold a layout are therefore
   transparent, and colour is painted by the panels that actually own a
   surface. Anything that genuinely needs its own fill - badges, pills, step
   numbers, the checklist markers, the step connector - sets it through an
   attribute selector, which outranks the bare type selector here and so keeps
   working. */
QLabel,
QCheckBox,
QRadioButton,
QFrame[role="checklist"],
QWidget[role="checkRow"],
QWidget[role="stepCell"] {
    background: transparent;
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

/* 4.71:1 against the page previously, which clears AA by a hair and fails it
   outright once a display is dimmed. Darkened to ~6:1 so subtitles and helper
   text stay legible without becoming a second body colour. */
QLabel[role="muted"] {
    color: #4e5d61;
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

/* Was #eef2f2 on #c0c8c8: a contrast ratio of 1.51:1, which is not a dim
   label but an unreadable one - and this app disables its primary action
   constantly, because "Write NWB" stays blocked until the pre-write checklist
   clears. The label naming the blocked action has to stay readable, so this is
   now a recessed surface with real text on it rather than white-on-grey. */
QPushButton:disabled {
    background: #ddd8ce;
    color: #575c58;
    border: 1px solid #cdc6b9;
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

/* ---- step bar ---------------------------------------------------------- */

QFrame[role="stepBar"] {
    background: #fffdf9;
    border: 1px solid #ddd4c5;
    border-radius: 12px;
}

QLabel[role="stepNumber"] {
    border-radius: 12px;
    font-size: 12px;
    font-weight: 700;
    background: #e7e1d6;
    color: #6b736f;
    border: 1px solid #d3cabc;
}

QLabel[role="stepNumber"][state="done"] {
    background: #1f5c64;
    color: #f7fbfa;
    border: 1px solid #1f5c64;
}

QLabel[role="stepNumber"][state="current"] {
    background: #fffdf9;
    color: #17333a;
    border: 2px solid #1f5c64;
}

QLabel[role="stepCaption"] {
    font-size: 12px;
    color: #6b736f;
}

QLabel[role="stepCaption"][state="done"] {
    color: #2c4a4a;
}

/* The only step rendered at full strength, so the eye lands on "you are here"
   before it reads any of the words. */
QLabel[role="stepCaption"][state="current"] {
    color: #17333a;
    font-weight: 700;
}

QLabel[role="stepConnector"] {
    background: #ddd4c5;
    max-height: 1px;
    min-height: 1px;
    margin: 0 10px;
}

/* ---- next action ------------------------------------------------------- */

/* One card carrying the single thing to do next, replacing three sentences
   that each restated it. */
QFrame[role="actionCard"] {
    background: #eef4f1;
    border: 1px solid #b8cfc6;
    border-radius: 12px;
}

QLabel[role="actionEyebrow"] {
    color: #46655f;
    font-size: 11px;
    font-weight: 700;
}

QLabel[role="actionTitle"] {
    color: #17333a;
    font-size: 17px;
    font-weight: 700;
}

QLabel[role="actionDetail"] {
    color: #40534f;
}

/* ---- checklist --------------------------------------------------------- */

QLabel[role="checkName"] {
    color: #26383b;
}

/* A filled dot for done, a hollow ring for everything outstanding: the shape
   carries the state, so it survives greyscale and colour blindness rather than
   relying on the pill's tint. */
QLabel[role="checkMarker"] {
    border-radius: 7px;
    background: #fffdf9;
    border: 2px solid #c3bbab;
}

QLabel[role="checkMarker"][state="done"] {
    background: #1f5c64;
    border: 2px solid #1f5c64;
}

QLabel[role="checkMarker"][state="active"] {
    background: #d8a24a;
    border: 2px solid #b98526;
}

QLabel[role="statePill"] {
    border-radius: 9px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: 700;
    background: #ece6da;
    color: #575c58;
    border: 1px solid #d5cbbd;
}

QLabel[role="statePill"][state="done"] {
    background: #dcebe4;
    color: #1c4f43;
    border: 1px solid #a9c8ba;
}

QLabel[role="statePill"][state="active"] {
    background: #f6e8cd;
    color: #6d4d12;
    border: 1px solid #ddbf82;
}

QLabel[role="statePill"][state="waiting"] {
    background: #ece6da;
    color: #5d5a52;
    border: 1px solid #d5cbbd;
}

/* ---- keyboard focus --------------------------------------------------- */

/* There was no focus styling at all, so tabbing through the conversion form
   moved an invisible cursor. Qt's `outline` support in QSS is unreliable
   across styles, so focus is carried by the border, which Fusion always
   honours. */
QLineEdit:focus,
QPlainTextEdit:focus,
QComboBox:focus,
QListWidget:focus,
QTreeWidget:focus,
QTableWidget:focus,
QAbstractSpinBox:focus {
    border: 2px solid #1f5c64;
    /* Padding drops by the extra border pixel so the control does not grow
       and nudge the layout when it takes focus. */
    padding: 6px 8px;
}

QPushButton:focus {
    border: 2px solid #17333a;
    padding: 7px 13px;
}

QTabBar::tab:focus {
    background: #f3ede1;
    color: #17333a;
}

QCheckBox:focus,
QRadioButton:focus {
    color: #17333a;
}

/* ---- scrollbars -------------------------------------------------------- */

/* Unstyled, these render as the stock Windows control: grey, square and
   noticeably wider than everything around them, which is the single loudest
   thing breaking the app's finish in a screenshot. */
QScrollBar:vertical {
    background: transparent;
    width: 12px;
    margin: 2px;
}

QScrollBar:horizontal {
    background: transparent;
    height: 12px;
    margin: 2px;
}

QScrollBar::handle:vertical,
QScrollBar::handle:horizontal {
    background: #c7bdae;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    min-height: 28px;
}

QScrollBar::handle:horizontal {
    min-width: 28px;
}

QScrollBar::handle:hover {
    background: #ab9f8c;
}

/* The stepper buttons and the track either side of the handle. Hidden rather
   than styled: they add two more clickable targets nobody uses and make the
   bar read as heavier than the content it scrolls. */
QScrollBar::add-line,
QScrollBar::sub-line {
    height: 0;
    width: 0;
    background: none;
    border: none;
}

QScrollBar::add-page,
QScrollBar::sub-page {
    background: none;
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


def repolish(widget: QWidget) -> None:
    """Re-evaluate a widget's style after a dynamic property changes.

    Qt resolves property selectors when a widget is polished, not when the
    property is set, so `setProperty` alone changes nothing on screen. Every
    state change below has to come back through here.
    """

    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def build_step_bar(
    steps: list[str],
    *,
    parent: QWidget | None = None,
) -> tuple[QFrame, list[tuple[QLabel, QLabel]]]:
    """Build a numbered step indicator for a linear workflow.

    Replaces a single wrapped sentence listing the steps. A stepper answers
    "where am I and what is left" at a glance, which a sentence cannot.
    """

    frame = QFrame(parent)
    frame.setProperty("role", "stepBar")
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(16, 12, 16, 12)
    layout.setSpacing(0)

    entries: list[tuple[QLabel, QLabel]] = []
    for index, caption in enumerate(steps):
        if index:
            connector = QLabel("", frame)
            connector.setProperty("role", "stepConnector")
            layout.addWidget(connector, 1)

        cell = QWidget(frame)
        # Marked so the sheet can keep it transparent; an unmarked QWidget
        # would paint the page colour over the step bar's own surface.
        cell.setProperty("role", "stepCell")
        cell_layout = QHBoxLayout(cell)
        cell_layout.setContentsMargins(0, 0, 0, 0)
        cell_layout.setSpacing(8)

        number = QLabel(str(index + 1), cell)
        number.setProperty("role", "stepNumber")
        number.setAlignment(Qt.AlignmentFlag.AlignCenter)
        number.setFixedSize(24, 24)

        text = QLabel(caption, cell)
        text.setProperty("role", "stepCaption")

        cell_layout.addWidget(number)
        cell_layout.addWidget(text)
        layout.addWidget(cell, 0)
        entries.append((number, text))

    return frame, entries


def set_step_states(
    entries: list[tuple[QLabel, QLabel]],
    current_index: int,
) -> None:
    """Mark steps before `current_index` done, that one current, the rest ahead."""

    for index, (number, text) in enumerate(entries):
        if index < current_index:
            state = "done"
        elif index == current_index:
            state = "current"
        else:
            state = "ahead"
        for widget in (number, text):
            widget.setProperty("state", state)
            repolish(widget)


def build_checklist(
    parent: QWidget | None = None,
) -> tuple[QFrame, QVBoxLayout]:
    """Container for `add_checklist_row` entries."""

    frame = QFrame(parent)
    frame.setProperty("role", "checklist")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)
    return frame, layout


def add_checklist_row(
    layout: QVBoxLayout,
    caption: str,
    *,
    parent: QWidget | None = None,
) -> tuple[QLabel, QLabel]:
    """One checklist line: a name on the left, a state pill on the right.

    Returns the pill and the row's own marker so callers can restate them.
    """

    row = QWidget(parent)
    row.setProperty("role", "checkRow")
    row_layout = QHBoxLayout(row)
    row_layout.setContentsMargins(0, 3, 0, 3)
    row_layout.setSpacing(10)

    marker = QLabel("", row)
    marker.setProperty("role", "checkMarker")
    marker.setFixedSize(14, 14)

    name = QLabel(caption, row)
    name.setProperty("role", "checkName")

    pill = QLabel("", row)
    pill.setProperty("role", "statePill")

    row_layout.addWidget(marker)
    row_layout.addWidget(name, 1)
    row_layout.addWidget(pill, 0, Qt.AlignmentFlag.AlignRight)
    layout.addWidget(row)
    return pill, marker


def set_check_state(pill: QLabel, marker: QLabel, status: str) -> None:
    """Apply one of the four statuses the conversion screen actually produces."""

    #: Anything unrecognised falls through as "pending" rather than rendering an
    #: unstyled pill, so a new status string degrades quietly instead of
    #: appearing broken.
    normalized = {
        "done": "done",
        "pending": "pending",
        "in progress": "active",
        "waiting for preview": "waiting",
    }.get(status.strip().lower(), "pending")

    pill.setText(status)
    for widget in (pill, marker):
        widget.setProperty("state", normalized)
        repolish(widget)


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
