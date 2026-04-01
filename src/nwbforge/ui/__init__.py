"""Toolkit-agnostic desktop UI models for NWB Forge."""

from nwbforge.ui.models import (
    ConversionSessionScreenState,
    DesktopShellState,
    FileMenuAction,
    FileMenuEntry,
    PackageInstallerState,
    SettingsScreenState,
    StatusBarState,
)
from nwbforge.ui.conversion_session import ConversionSessionScreenModel
from nwbforge.ui.errors import DefaultUiErrorPresenter, UiErrorPresenter, UserFacingError
from nwbforge.ui.logs import (
    CompositeUiLogSink,
    FileUiLogSink,
    InMemoryUiLogSink,
    UiLogEntry,
    UiLogHandler,
    UiLogSink,
    UiLogSubscriptionSink,
)
from nwbforge.ui.package_setup import PackageInstallerScreenModel
from nwbforge.ui.settings import SettingsScreenModel
from nwbforge.ui.shell import DesktopShellModel

__all__ = [
    "ConversionSessionScreenModel",
    "ConversionSessionScreenState",
    "CompositeUiLogSink",
    "DefaultUiErrorPresenter",
    "DesktopShellModel",
    "DesktopShellState",
    "FileUiLogSink",
    "FileMenuAction",
    "FileMenuEntry",
    "InMemoryUiLogSink",
    "PackageInstallerScreenModel",
    "PackageInstallerState",
    "SettingsScreenModel",
    "SettingsScreenState",
    "StatusBarState",
    "UiErrorPresenter",
    "UiLogEntry",
    "UiLogHandler",
    "UiLogSink",
    "UiLogSubscriptionSink",
    "UserFacingError",
]
