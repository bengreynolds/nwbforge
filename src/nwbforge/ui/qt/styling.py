"""Shared Qt styling helpers for the NWB Forge desktop UI."""

from __future__ import annotations

from string import Template

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


#: Qt's QSS is a subset of CSS. `letter-spacing` and `text-transform` are NOT
#: supported and are silently ignored, so emphasis here is carried by weight,
#: size and colour only; anything that needs to read as a caption is cased in
#: Python instead.
#: Role-based design tokens. Names describe the job a value does, not what
#: it looks like, so a theme change is one edit here rather than a hunt
#: through the sheet. Collapsed from 72 raw literals that had accumulated
#: five near-identical off-whites and seven near-identical borders -
#: differences nobody chose, which simply drifted in over time.
_COLOR = {
    "surface_page": "#f4f1ea",
    "surface": "#fcfaf6",
    "surface_raised": "#fffdf9",
    "surface_sunken": "#ede8df",
    "surface_subtle": "#f7f4ee",
    "surface_alt": "#f6f2ea",
    "surface_tab": "#ebe4d7",
    "outline": "#d9d0c2",
    "outline_strong": "#c7bdae",
    "outline_stronger": "#ab9f8c",
    "text": "#1e2a2d",
    "text_heading": "#17333a",
    "text_muted": "#4e5d61",
    "text_subtle": "#607072",
    "interactive": "#1f5c64",
    "interactive_hover": "#17484f",
    "interactive_pressed": "#123940",
    "on_interactive": "#f7fbfa",
    "accent_surface": "#e7f0ec",
    "accent_surface_hover": "#d7e4de",
    "accent_outline": "#a9c2b7",
    "accent_text": "#46655f",
    "disabled_surface": "#ddd8ce",
    "disabled_text": "#575c58",
    "state_done_bg": "#dcebe4",
    "state_done_fg": "#1c4f43",
    "state_done_outline": "#a9c8ba",
    "state_active_bg": "#f6e8cd",
    "state_active_fg": "#6d4d12",
    "state_active_outline": "#ddbf82",
    "state_active_dot": "#d8a24a",
    "state_active_dot_outline": "#b98526",
    "state_idle_bg": "#ece6da",
    "progress_fill": "#2f7a72",
    "danger": "#8b4a43",
    "danger_hover": "#733a34",
    "selection_bg": "#b9d3c6",
}

#: Modular scale, base 14px, minor third (1.2): 12 / 14 / 17 / 20 / 24.
#: Five derived steps replacing seven arbitrary sizes. Base is 14 rather
#: than the 16 a web target would take - this is a dense Windows desktop
#: tool in a fixed window, where native body text sits nearer 12px. Change
#: t_body to rescale the whole sheet.
_TYPE = {
    "t_caption": "12",
    "t_body": "14",
    "t_section": "17",
    "t_value": "20",
    "t_title": "24",
}

#: QSS has no variables and str.format would collide with CSS braces,
#: so substitution is string.Template - '$' never appears in QSS.
_TOKENS = {**_COLOR, **_TYPE}

_NWB_FORGE_STYLESHEET = Template("""
QWidget {
    background: ${surface_page};
    color: ${text};
    /* Named explicitly rather than inherited. Qt's default on Windows falls
       back through a stack that can land on MS Shell Dlg 2, which renders a
       full step smaller and without the hinting the rest of the desktop
       gets. */
    font-family: "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif;
    font-size: ${t_body}px;
}

/* The rule above paints EVERY widget opaque in the page colour, including
   labels and the plain QWidgets used as layout rows. Sat inside a group box
   (${surface}) or a card (${surface_raised}) those repaint the page colour behind their own
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
    background: ${surface_sunken};
}

QMenuBar {
    background: ${surface_subtle};
    border-bottom: 1px solid ${outline};
    padding: 4px 8px;
}

QMenuBar::item {
    background: transparent;
    padding: 6px 10px;
    border-radius: 6px;
}

QMenuBar::item:selected,
QMenu::item:selected {
    background: ${accent_surface};
}

QMenu {
    background: ${surface_raised};
    border: 1px solid ${outline};
    padding: 6px;
}

QMenu::item {
    padding: 7px 24px 7px 10px;
    border-radius: 6px;
}

QStatusBar {
    background: ${surface_subtle};
    border-top: 1px solid ${outline};
}

QGroupBox {
    background: ${surface};
    border: 1px solid ${outline};
    border-radius: 12px;
    margin-top: 14px;
    padding: 16px 14px 14px 14px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: ${text_muted};
}

QLabel[role="pageTitle"] {
    font-size: ${t_title}px;
    font-weight: 700;
    color: ${text_heading};
}

QLabel[role="sectionTitle"] {
    font-size: ${t_section}px;
    font-weight: 700;
    color: ${text_heading};
}

/* 4.71:1 against the page previously, which clears AA by a hair and fails it
   outright once a display is dimmed. Darkened to ~6:1 so subtitles and helper
   text stay legible without becoming a second body colour. */
QLabel[role="muted"] {
    color: ${text_muted};
}

QLabel[role="badge"] {
    background: ${interactive};
    color: ${on_interactive};
    border-radius: 12px;
    padding: 5px 10px;
    font-size: ${t_caption}px;
    font-weight: 700;
}

QLabel[role="cardLabel"] {
    color: ${text_subtle};
    font-size: ${t_caption}px;
    font-weight: 700;
}

QLabel[role="cardValue"] {
    color: ${text_heading};
    font-size: ${t_value}px;
    font-weight: 700;
}

QFrame[role="headerCard"] {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 ${surface_raised},
        stop: 1 ${surface_sunken}
    );
    border: 1px solid ${outline};
    border-radius: 16px;
}

QFrame[role="metricCard"] {
    background: ${surface_raised};
    border: 1px solid ${outline};
    border-radius: 12px;
}

QFrame[role="metricCard"][accent="true"] {
    background: ${accent_surface};
    border: 1px solid ${accent_outline};
}

QLineEdit, QPlainTextEdit, QListWidget, QTreeWidget, QTableWidget, QComboBox {
    background: ${surface_raised};
    border: 1px solid ${outline};
    border-radius: 10px;
    padding: 7px 9px;
    selection-background-color: ${selection_bg};
    selection-color: ${text_heading};
}

QListWidget, QTreeWidget, QTableWidget {
    alternate-background-color: ${surface_alt};
}

QListWidget::item,
QTreeWidget::item {
    padding: 5px 3px;
    border-radius: 6px;
}

QTabWidget::pane {
    border: 1px solid ${outline};
    border-radius: 12px;
    background: ${surface};
    top: -1px;
}

QTabBar::tab {
    background: ${surface_tab};
    border: 1px solid ${outline};
    border-bottom: none;
    padding: 8px 14px;
    margin-right: 4px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    color: ${text_subtle};
    font-weight: 600;
}

QTabBar::tab:selected {
    background: ${surface};
    color: ${text_heading};
}

QPushButton {
    /* Was ~34px tall from padding alone. WCAG 2.2 target size (minimum) is
       24px and was already met; 44px is the touch recommendation and would
       look oversized on a mouse-driven desktop tool, so 36px is the
       compromise - a real gain in click area without inflating the panel. */
    min-height: 36px;
    background: ${interactive};
    color: ${on_interactive};
    border: none;
    border-radius: 10px;
    padding: 8px 14px;
    font-weight: 600;
}

QPushButton:hover {
    background: ${interactive_hover};
}

QPushButton:pressed {
    background: ${interactive_pressed};
}

/* Was ${disabled_text} on ${disabled_surface}: a contrast ratio of 1.51:1, which is not a dim
   label but an unreadable one - and this app disables its primary action
   constantly, because "Write NWB" stays blocked until the pre-write checklist
   clears. The label naming the blocked action has to stay readable, so this is
   now a recessed surface with real text on it rather than white-on-grey. */
QPushButton:disabled {
    background: ${disabled_surface};
    color: ${disabled_text};
    border: 1px solid ${outline};
}

QPushButton[secondary="true"] {
    background: ${accent_surface};
    color: ${text_heading};
    border: 1px solid ${accent_outline};
}

QPushButton[secondary="true"]:hover {
    background: ${accent_surface_hover};
}

QPushButton[danger="true"] {
    background: ${danger};
}

QPushButton[danger="true"]:hover {
    background: ${danger_hover};
}

QProgressBar {
    min-width: 180px;
    background: ${surface_tab};
    border: 1px solid ${outline};
    border-radius: 10px;
    text-align: center;
    color: ${text_heading};
}

QProgressBar::chunk {
    background: ${progress_fill};
    border-radius: 9px;
}

QDockWidget {
    color: ${text_heading};
}

QDockWidget::title {
    background: ${surface_subtle};
    border-bottom: 1px solid ${outline};
    padding: 8px 10px;
    text-align: left;
    font-weight: 700;
}

QHeaderView::section {
    background: ${surface_subtle};
    color: ${text_muted};
    padding: 6px;
    border: none;
    border-right: 1px solid ${outline};
    border-bottom: 1px solid ${outline};
    font-weight: 700;
}

QSplitter::handle {
    background: ${outline};
    width: 3px;
    height: 3px;
}

/* ---- step bar ---------------------------------------------------------- */

QFrame[role="stepBar"] {
    background: ${surface_raised};
    border: 1px solid ${outline};
    border-radius: 12px;
}

QLabel[role="stepNumber"] {
    border-radius: 12px;
    font-size: ${t_caption}px;
    font-weight: 700;
    background: ${surface_tab};
    color: ${text_subtle};
    border: 1px solid ${outline};
}

QLabel[role="stepNumber"][state="done"] {
    background: ${interactive};
    color: ${on_interactive};
    border: 1px solid ${interactive};
}

QLabel[role="stepNumber"][state="current"] {
    background: ${surface_raised};
    color: ${text_heading};
    border: 2px solid ${interactive};
}

QLabel[role="stepCaption"] {
    font-size: ${t_caption}px;
    color: ${text_subtle};
}

QLabel[role="stepCaption"][state="done"] {
    color: ${text};
}

/* The only step rendered at full strength, so the eye lands on "you are here"
   before it reads any of the words. */
QLabel[role="stepCaption"][state="current"] {
    color: ${text_heading};
    font-weight: 700;
}

QLabel[role="stepConnector"] {
    background: ${outline};
    max-height: 1px;
    min-height: 1px;
    margin: 0 10px;
}

/* ---- next action ------------------------------------------------------- */

/* One card carrying the single thing to do next, replacing three sentences
   that each restated it. */
QFrame[role="actionCard"] {
    background: ${accent_surface};
    border: 1px solid ${accent_outline};
    border-radius: 12px;
}

QLabel[role="actionEyebrow"] {
    color: ${accent_text};
    font-size: ${t_caption}px;
    font-weight: 700;
}

QLabel[role="actionTitle"] {
    color: ${text_heading};
    font-size: ${t_section}px;
    font-weight: 700;
}

QLabel[role="actionDetail"] {
    color: ${text_muted};
}

/* ---- checklist --------------------------------------------------------- */

QLabel[role="checkName"] {
    color: ${text};
}

/* A filled dot for done, a hollow ring for everything outstanding: the shape
   carries the state, so it survives greyscale and colour blindness rather than
   relying on the pill's tint. */
QLabel[role="checkMarker"] {
    border-radius: 7px;
    background: ${surface_raised};
    border: 2px solid ${outline_strong};
}

QLabel[role="checkMarker"][state="done"] {
    background: ${interactive};
    border: 2px solid ${interactive};
}

QLabel[role="checkMarker"][state="active"] {
    background: ${state_active_dot};
    border: 2px solid ${state_active_dot_outline};
}

QLabel[role="statePill"] {
    border-radius: 9px;
    padding: 2px 9px;
    font-size: ${t_caption}px;
    font-weight: 700;
    background: ${state_idle_bg};
    color: ${disabled_text};
    border: 1px solid ${outline};
}

QLabel[role="statePill"][state="done"] {
    background: ${state_done_bg};
    color: ${state_done_fg};
    border: 1px solid ${state_done_outline};
}

QLabel[role="statePill"][state="active"] {
    background: ${state_active_bg};
    color: ${state_active_fg};
    border: 1px solid ${state_active_outline};
}

QLabel[role="statePill"][state="waiting"] {
    background: ${state_idle_bg};
    color: ${text_subtle};
    border: 1px solid ${outline};
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
    border: 2px solid ${interactive};
    /* Padding drops by the extra border pixel so the control does not grow
       and nudge the layout when it takes focus. */
    padding: 6px 8px;
}

QPushButton:focus {
    border: 2px solid ${text_heading};
    padding: 7px 13px;
}

QTabBar::tab:focus {
    background: ${surface_alt};
    color: ${text_heading};
}

QCheckBox:focus,
QRadioButton:focus {
    color: ${text_heading};
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
    background: ${outline_strong};
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    min-height: 28px;
}

QScrollBar::handle:horizontal {
    min-width: 28px;
}

QScrollBar::handle:hover {
    background: ${outline_stronger};
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
""").substitute(_TOKENS)


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
