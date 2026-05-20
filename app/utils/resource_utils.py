"""Resource path utilities.

Resolves the ``app/`` root directory correctly in both development
and Nuitka-compiled builds.
"""
from __future__ import annotations

import sys
from pathlib import Path


def get_app_dir() -> Path:
    """Return the ``app/`` root directory.

    - **Nuitka**: uses ``sys.__nuitka_binary_dir`` which points to the
      folder containing the compiled executable plus any data files.
    - **Development**: walks up from this file's location.
    """
    if hasattr(sys, "__nuitka_binary_dir"):
        return Path(sys.__nuitka_binary_dir)  # type: ignore[attr-defined]
    # This file lives at app/utils/resource_utils.py
    # → parent       = app/utils/
    # → parent.parent = app/
    return Path(__file__).resolve().parent.parent


def get_asset(relative_path: str) -> Path:
    """Return an absolute Path to an asset inside ``app/assets/``.

    Example::

        icon_path = get_asset("icons/logo.png")
    """
    return get_app_dir() / "assets" / relative_path

