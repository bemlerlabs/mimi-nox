"""
Single source of truth for the MiMi Nox version string.

Reads the installed distribution version when available (packaged installs,
Docker, pip -e); falls back to the hardcoded version for source-tree runs
where the package metadata is not resolvable.
"""

from __future__ import annotations

import importlib.metadata

__all__ = ["__version__", "version_string"]


def _installed_version() -> str | None:
    try:
        return importlib.metadata.version("mimi-nox")
    except importlib.metadata.PackageNotFoundError:
        return None


# Kept in sync with pyproject.toml [project].version — update BOTH on release.
_FALLBACK_VERSION = "4.0.0"


def version_string() -> str:
    return _installed_version() or _FALLBACK_VERSION


__version__ = version_string()
