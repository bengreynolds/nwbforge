# Release Strategy Baseline

Last updated: 2026-03-31

## Purpose

This note captures the current architectural planning for packaging, installation, updates, and distribution. It does not change the current implementation sequence; it makes release engineering an explicit design track.

## Product requirements

The application must support formal releases on:
- Windows
- macOS
- Linux

Each release must provide:
- a platform-native installer or installable package
- bundled runtime dependencies
- support for fresh install and in-place update
- a built-in UI updater that can check GitHub releases and preserve settings when possible

## Required packaging baseline

Final application releases must follow this sequence:
1. build the application in Python
2. package the application with PyInstaller
3. wrap the PyInstaller output in a native installer or installable package for the target platform
4. publish release artifacts to GitHub Releases
5. let the in-app updater discover and pull the latest compatible release from GitHub Releases

This is the required distribution model for the product, not an open packaging comparison.

## PyInstaller as the primary packaging layer

PyInstaller is the required first-stage packager because it best fits the current product constraints:
- Python-first application and backend architecture
- desktop distribution to non-technical lab users
- bundled scientific Python dependencies
- no requirement for users to install Python, Conda, or a virtual environment

The PyInstaller payload is expected to bundle:
- the Python interpreter
- application code
- required Python dependencies
- scientific Python dependencies and supporting binary assets needed at runtime

## Native installer strategy

The installer layer wraps the PyInstaller build. It does not replace the Python-first runtime model.

Windows:
- wrap the PyInstaller application in a native installer such as Inno Setup, NSIS, or WiX
- support install-location selection, desktop shortcut creation, start menu entries, and uninstall/repair flows

macOS:
- wrap the PyInstaller-built `.app` in a signed `.dmg` or `.pkg`
- support standard macOS install expectations and platform signing/notarization requirements

Linux:
- wrap the PyInstaller build in at least one broadly distributable format such as AppImage
- optionally provide a native package such as `.deb` for managed lab environments

## Updater design

The in-app updater should:
- check GitHub Releases for newer compatible versions
- show release notes and update availability inside the UI
- download the correct platform-specific release artifact
- launch a user-friendly update handoff
- preserve user settings, templates, and local session state when possible

Initial design assumptions:
- settings and local state should live outside the installed application directory
- update checks should be explicit and user-visible first, with optional background polling later
- rollback should rely on reinstalling a known-good release while preserving compatible local state
- failed update handoffs should leave the current installation usable

## Versioning strategy

Planned baseline:
- semantic versioning for public releases
- pre-release tags for internal department pilots
- explicit compatibility notes when config, session, or plugin formats change

## Release pipeline

Target pipeline:
1. build the Python application for the target platform
2. package it with PyInstaller into a self-contained payload
3. validate the packaged runtime and bundled scientific dependencies
4. wrap the PyInstaller payload in a native installer or installable package
5. publish GitHub release assets and notes
6. application updater consumes published release metadata and launches the correct update asset

## Failure and rollback considerations

- updater failures must not corrupt user settings or local session data
- installers should support repair or reinstall paths
- release metadata should allow downgrading to a prior known-good version
- schema/config migrations should be versioned and reversible where feasible
- scientific Python dependencies must be tested inside packaged builds on every supported platform

## Packaging tradeoffs and risks

- scientific Python stacks can produce large application bundles
- compiled dependencies may require explicit PyInstaller hooks, data-file collection, or hidden-import configuration
- platform-specific signing, notarization, and antivirus reputation can complicate installer rollout
- packaging HDF5-backed libraries and other binary dependencies can fail differently across Windows, macOS, and Linux
- plugin discovery and dynamically imported modules may need explicit packaging rules

Mitigation direction:
- keep release builds reproducible and platform-specific
- maintain explicit PyInstaller configuration rather than relying only on defaults
- run packaged smoke tests on each supported platform before promotion
- separate developer environment policy from packaged runtime behavior
