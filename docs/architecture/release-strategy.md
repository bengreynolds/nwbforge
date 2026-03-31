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

## Packaging and installer evaluation

### Option 1: Python desktop app with PySide6 plus PyInstaller/Nuitka

Pros:
- strongest alignment with the existing Python-heavy backend
- simpler model for sharing domain, adapter, normalization, mapping, and validation code
- avoids a split frontend/backend distribution model early

Cons:
- updater and installer polish must be assembled explicitly
- platform-specific packaging is still non-trivial

Installer pairing by platform:
- Windows: Inno Setup, NSIS, or WiX
- macOS: signed `.dmg` or `.pkg`
- Linux: AppImage and at least one native package path such as `.deb`

### Option 2: Electron desktop shell with Python backend sidecar

Pros:
- mature installer and update ecosystem
- flexible UI stack

Cons:
- larger distribution footprint
- more operational complexity around bundling and supervising the Python sidecar
- more moving parts for a small team

### Option 3: Tauri frontend with Python backend sidecar

Pros:
- smaller footprint than Electron
- strong native-updater story

Cons:
- still requires sidecar packaging complexity
- introduces Rust and web frontend build concerns early

## Current recommendation

Current planning bias:
- stay desktop-first
- keep the primary application stack Python-centric initially
- evaluate PySide6 with PyInstaller or Nuitka plus platform-specific installers first

Reasoning:
- this minimizes early architectural split while the backend contracts are still settling
- it fits the current repo trajectory and lets release engineering evolve without forcing an immediate frontend rewrite

## Updater design

The application should include a built-in updater flow that:
- checks GitHub releases for a newer compatible version
- presents release notes and update availability in the UI
- downloads the correct platform artifact
- launches the installer/update flow
- preserves user settings, templates, and session history when possible

Initial design assumptions:
- settings and local state should live outside the installed application directory
- update checks should be explicit and user-visible, with optional background polling later
- rollback should rely on reinstalling a known-good previous release plus preserved user-state migration safety

## Versioning strategy

Planned baseline:
- semantic versioning for public releases
- pre-release tags for internal department pilots
- explicit compatibility notes when config, session, or plugin formats change

## Release pipeline

Target pipeline:
1. build platform-specific application artifact
2. package with bundled runtime
3. wrap in installer/update package
4. publish GitHub release assets and notes
5. application updater consumes published release metadata

## Failure and rollback considerations

- updater failures must not corrupt user settings or local session data
- installers should support repair or reinstall paths
- release metadata should allow downgrading to a prior known-good version
- schema/config migrations should be versioned and reversible where feasible
