from __future__ import annotations

from types import ModuleType

from nwbforge.app.runtime.python_env import import_modules_without_user_site


def test_import_modules_without_user_site_hides_user_site_and_purges_conflicting_modules(monkeypatch) -> None:
    fake_user_site = "C:/Users/test/AppData/Roaming/Python/Python311/site-packages"
    original_path = [fake_user_site, "C:/env/Lib/site-packages"]
    fake_cached_hdmf = ModuleType("hdmf")
    fake_cached_hdmf.__file__ = f"{fake_user_site}/hdmf/__init__.py"
    seen_user_site: list[bool] = []

    def fake_import_module(name: str):
        import sys

        seen_user_site.append(
            any(path.replace("\\", "/").lower() == fake_user_site.lower() for path in sys.path)
        )
        module = ModuleType(name)
        module.__file__ = f"C:/env/Lib/site-packages/{name.replace('.', '/')}/__init__.py"
        return module

    monkeypatch.setattr("nwbforge.app.runtime.python_env.site.getusersitepackages", lambda: fake_user_site)
    monkeypatch.setattr("nwbforge.app.runtime.python_env.sys.path", list(original_path))
    monkeypatch.setitem(__import__("sys").modules, "hdmf", fake_cached_hdmf)
    monkeypatch.setattr("nwbforge.app.runtime.python_env.importlib.import_module", fake_import_module)

    imported_hdmf, imported_pynwb = import_modules_without_user_site(
        "hdmf",
        "pynwb",
        purge_prefixes=("hdmf", "pynwb"),
    )

    assert imported_hdmf.__file__ == "C:/env/Lib/site-packages/hdmf/__init__.py"
    assert imported_pynwb.__file__ == "C:/env/Lib/site-packages/pynwb/__init__.py"
    assert seen_user_site == [False, False]
