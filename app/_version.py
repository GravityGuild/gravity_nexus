"""Single source of truth for the application version.

All other modules (main.py, build_nuitka.py, etc.) import from here so that
bumping the version only ever requires editing this one file.

Version format: MAJOR.MINOR.PATCH  (PEP 440 / SemVer-compatible)
"""

__version__: str = "0.1.0"
