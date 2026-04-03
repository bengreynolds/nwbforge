from __future__ import annotations

import types

import nwbforge.adapters as adapters_module
import nwbforge.adapters.supported as supported_module


def test_supported_try_import_optional_ignores_missing_exports(monkeypatch) -> None:
    missing_export_module = types.SimpleNamespace()
    export_name = "MissingSupportedExportForTest"

    monkeypatch.setattr(supported_module, "import_module", lambda name: missing_export_module)

    supported_module._try_import_optional("nwbforge.adapters.supported.media", export_name)

    assert export_name not in supported_module.__all__


def test_top_level_try_import_optional_ignores_missing_exports(monkeypatch) -> None:
    missing_export_module = types.SimpleNamespace()
    export_name = "MissingTopLevelExportForTest"

    monkeypatch.setattr(adapters_module, "import_module", lambda name: missing_export_module)

    adapters_module._try_import_optional("nwbforge.adapters.supported", export_name)

    assert export_name not in adapters_module.__all__
