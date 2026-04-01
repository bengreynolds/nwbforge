"""Toolkit-agnostic desktop UI models for NWB Forge."""

from nwbforge.ui.models import (
    DesktopShellState,
    FileMenuAction,
    FileMenuEntry,
    PackageInstallerState,
    StatusBarState,
)
from nwbforge.ui.package_setup import PackageInstallerScreenModel
from nwbforge.ui.shell import DesktopShellModel

__all__ = [
    "DesktopShellModel",
    "DesktopShellState",
    "FileMenuAction",
    "FileMenuEntry",
    "PackageInstallerScreenModel",
    "PackageInstallerState",
    "StatusBarState",
]
