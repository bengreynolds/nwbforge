# Release Strategy Baseline

Purpose: capture packaging, installation, update, and distribution direction.

Current baseline:
- Releases are planned around a PyInstaller-built desktop app wrapped in native installers
- The updater is expected to work through GitHub Releases
- Packaging must keep the runtime self-contained for end users

Constraints:
- Do not require Conda or a virtual environment on user machines
- Keep packaging, signing, and binary-dependency risks explicit

Next step:
- Stay at the planning stage until the desktop workflow is stable enough to justify release work
