"""Helpers for keeping dedicated-environment imports authoritative."""

from __future__ import annotations

from contextlib import contextmanager
import importlib
import site
import sys
from types import ModuleType


def _normalized_user_site_paths() -> tuple[str, ...]:
    user_site = site.getusersitepackages()
    candidates = (user_site,) if isinstance(user_site, str) else tuple(user_site)
    return tuple(
        str(path).replace("\\", "/").lower().rstrip("/")
        for path in candidates
        if str(path).strip()
    )


def _normalized_path(path: str | None) -> str:
    return str(path or "").replace("\\", "/").lower().rstrip("/")


def _matches_prefix(module_name: str, prefixes: tuple[str, ...]) -> bool:
    return any(module_name == prefix or module_name.startswith(f"{prefix}.") for prefix in prefixes)


def purge_user_site_modules(*module_prefixes: str) -> None:
    """Drop cached modules that were loaded from the user site."""

    if not module_prefixes:
        return
    normalized_sites = _normalized_user_site_paths()
    if not normalized_sites:
        return
    to_remove: list[str] = []
    for module_name, module in tuple(sys.modules.items()):
        if not _matches_prefix(module_name, tuple(module_prefixes)):
            continue
        module_path = _normalized_path(getattr(module, "__file__", None))
        if any(module_path.startswith(f"{user_site}/") or module_path == user_site for user_site in normalized_sites):
            to_remove.append(module_name)
    for module_name in sorted(to_remove, key=lambda value: value.count("."), reverse=True):
        sys.modules.pop(module_name, None)


@contextmanager
def without_user_site_paths():
    """Temporarily hide user-site paths so the dedicated env stays authoritative."""

    normalized_sites = _normalized_user_site_paths()
    if not normalized_sites:
        yield
        return
    original_sys_path = list(sys.path)
    sys.path[:] = [
        path
        for path in sys.path
        if _normalized_path(path) not in normalized_sites
    ]
    try:
        yield
    finally:
        sys.path[:] = original_sys_path


def import_modules_without_user_site(
    *module_names: str,
    purge_prefixes: tuple[str, ...] = (),
) -> tuple[ModuleType, ...]:
    """Import modules with user-site paths hidden and conflicting cached modules purged."""

    with without_user_site_paths():
        purge_user_site_modules(*purge_prefixes)
        return tuple(importlib.import_module(module_name) for module_name in module_names)
