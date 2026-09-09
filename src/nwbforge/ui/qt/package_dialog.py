"""Qt dialog for route-based package installation."""

from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from nwbforge.app.packages import InstallMode, InstallPreset
from nwbforge.ui.models import PackageInstallerState
from nwbforge.ui.package_setup import PackageInstallerScreenModel
from nwbforge.ui.qt.bridge import StateBridge
from nwbforge.ui.qt.styling import apply_window_chrome, build_page_header


class PackageInstallerDialog(QWidget):
    """Embedded panel bound to `PackageInstallerScreenModel`."""

    dismissed = Signal()

    def __init__(self, screen_model: PackageInstallerScreenModel, parent=None) -> None:
        super().__init__(parent)
        self.resize(680, 620)
        apply_window_chrome(self)
        self._screen_model = screen_model

        self._mode_combo = QComboBox(self)
        self._mode_combo.addItem("Minimal", InstallMode.MINIMAL.value)
        self._mode_combo.addItem("Selected", InstallMode.SELECTED.value)
        self._mode_combo.addItem("Full", InstallMode.FULL.value)
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)

        self._preset_combo = QComboBox(self)
        self._preset_combo.addItem("Minimal", InstallPreset.MINIMAL.value)
        self._preset_combo.addItem("Common", InstallPreset.COMMON.value)
        self._preset_combo.addItem("Full", InstallPreset.FULL.value)
        self._preset_combo.addItem("Custom", InstallPreset.CUSTOM.value)
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)

        self._route_list = QListWidget(self)
        self._route_list.itemChanged.connect(self._on_route_item_changed)

        self._guidance_label = QLabel(
            "Use this screen only when a representative dataset or optional viewer capability needs extra support in the dedicated development environment. Most direct-ingest work should start with New Session instead.",
            self,
        )
        self._guidance_label.setWordWrap(True)
        self._status_label = QLabel("Loading package options...", self)
        self._extras_label = QLabel("Resolved extras: none", self)
        self._issues_label = QLabel("No issues.", self)
        self._issues_label.setWordWrap(True)

        self._install_button = QPushButton("Install", self)
        self._install_button.clicked.connect(self._on_install_clicked)
        self._close_button = QPushButton("Close", self)
        self._close_button.clicked.connect(self.reject)
        self._close_button.setProperty("secondary", True)

        (
            self._header_frame,
            self._header_title_label,
            self._header_subtitle_label,
            self._header_badge_label,
        ) = build_page_header(
            "Optional Workflow Support",
            "Add optional route or NWB viewer support for representative datasets in the dedicated development environment without changing the main direct-ingest workflow.",
            badge_text="Secondary Setup",
            parent=self,
        )

        form_layout = QFormLayout()
        form_layout.addRow("Install mode", self._mode_combo)
        form_layout.addRow("Preset", self._preset_combo)
        options_group = QGroupBox("Install Options", self)
        options_group.setLayout(form_layout)

        self._route_group = QGroupBox("Custom Route Selection", self)
        route_layout = QVBoxLayout(self._route_group)
        route_layout.addWidget(self._guidance_label)
        route_layout.addWidget(self._route_list)

        summary_group = QGroupBox("Support Summary", self)
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.addWidget(self._extras_label)
        summary_layout.addWidget(self._issues_label)
        summary_layout.addWidget(self._status_label)

        buttons = QDialogButtonBox(self)
        buttons.addButton(self._install_button, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(self._close_button, QDialogButtonBox.ButtonRole.RejectRole)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        content = QWidget(self)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(14)
        content_layout.addWidget(self._header_frame)
        content_layout.addWidget(options_group)
        content_layout.addWidget(self._route_group, stretch=1)
        content_layout.addWidget(summary_group)
        content_layout.addWidget(buttons)

        self._scroll_area = QScrollArea(self)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setWidget(content)
        layout.addWidget(self._scroll_area)

        self._bridge = StateBridge(self)
        self._bridge.state_changed.connect(self._apply_state)
        self._screen_model.subscribe(self._bridge.publish)
        self._screen_model.load()

    def reject(self) -> None:
        self.dismissed.emit()

    def _apply_state(self, state: PackageInstallerState) -> None:
        self._sync_mode_combo(state.install_mode)
        self._sync_preset_combo(state.install_preset)
        self._sync_route_items(state)

        self._extras_label.setText(
            "Resolved extras: " + (", ".join(state.resolved_extras) if state.resolved_extras else "none")
        )

        if state.user_error is not None:
            self._issues_label.setText(state.user_error.message)
        elif state.issues:
            self._issues_label.setText("\n".join(issue.message for issue in state.issues))
        else:
            self._issues_label.setText("No issues.")

        if state.progress_event is not None:
            self._status_label.setText(state.progress_event.message)
        elif state.user_error is not None:
            self._status_label.setText(state.user_error.message)
        elif state.preview is not None:
            self._status_label.setText("Ready to install selected packages." if state.is_installable else "Selection needs review.")
        else:
            self._status_label.setText("Loading package options...")

        route_list_enabled = state.install_mode is InstallMode.SELECTED and state.install_preset is InstallPreset.CUSTOM
        self._route_group.setVisible(route_list_enabled)
        self._route_list.setEnabled(route_list_enabled)
        self._preset_combo.setEnabled(state.install_mode is InstallMode.SELECTED)
        self._install_button.setEnabled(state.is_installable and not state.is_install_running)

    def _sync_mode_combo(self, mode: InstallMode) -> None:
        with QSignalBlocker(self._mode_combo):
            index = self._mode_combo.findData(mode.value)
            if index >= 0:
                self._mode_combo.setCurrentIndex(index)

    def _sync_preset_combo(self, preset: InstallPreset) -> None:
        with QSignalBlocker(self._preset_combo):
            index = self._preset_combo.findData(preset.value)
            if index >= 0:
                self._preset_combo.setCurrentIndex(index)

    def _sync_route_items(self, state: PackageInstallerState) -> None:
        existing = {self._route_list.item(i).data(Qt.ItemDataRole.UserRole): self._route_list.item(i) for i in range(self._route_list.count())}
        selected = set(state.selected_routes)
        for spec in state.available_routes:
            item = existing.get(spec.route_name)
            if item is None:
                item = QListWidgetItem(spec.display_name)
                item.setData(Qt.ItemDataRole.UserRole, spec.route_name)
                item.setToolTip(spec.description)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                self._route_list.addItem(item)
            with QSignalBlocker(self._route_list):
                item.setCheckState(Qt.CheckState.Checked if spec.route_name in selected else Qt.CheckState.Unchecked)

    def _on_mode_changed(self) -> None:
        mode = self._mode_combo.currentData(Qt.ItemDataRole.UserRole)
        if mode is not None:
            self._screen_model.set_install_mode(InstallMode(str(mode)))

    def _on_preset_changed(self) -> None:
        preset = self._preset_combo.currentData(Qt.ItemDataRole.UserRole)
        if preset is not None:
            self._screen_model.select_preset(InstallPreset(str(preset)))

    def _on_route_item_changed(self) -> None:
        preset = self._preset_combo.currentData(Qt.ItemDataRole.UserRole)
        if preset is None or InstallPreset(str(preset)) is not InstallPreset.CUSTOM:
            return
        selected = []
        for index in range(self._route_list.count()):
            item = self._route_list.item(index)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.data(Qt.ItemDataRole.UserRole))
        self._screen_model.set_custom_routes(tuple(selected))

    def _on_install_clicked(self) -> None:
        self._screen_model.start_install()
