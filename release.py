"""Gravity Nexus full release pipeline.

Steps:
  1. Read version from app/_version.py
  2. Sync #define AppVersion in installer/gravity_nexus_setup.iss
  3. Create a clean build venv (build_env\\) with runtime deps + nuitka
  4. Compile the exe via build_nuitka.py
  5. Locate ISCC.exe (Inno Setup compiler)
  6. Build the installer

Usage::

    python release.py [--skip-venv]

--skip-venv  Reuse an existing build_env\\ instead of recreating it.
             Useful when iterating on Nuitka flags without reinstalling deps.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD_VENV = ROOT / "build_env"
VENV_PYTHON = BUILD_VENV / "Scripts" / "python.exe"

SKIP_VENV = "--skip-venv" in sys.argv

_WIDTH = 60


def _banner(n: int, label: str) -> None:
    print(f"\n{'=' * _WIDTH}")
    print(f"  STEP {n}: {label}")
    print(f"{'=' * _WIDTH}")


def _run(cmd: list[str | Path], *, cwd: Path | None = None) -> None:
    printable = " ".join(f'"{c}"' if " " in str(c) else str(c) for c in cmd)
    print(f"  $ {printable}")
    result = subprocess.run([str(c) for c in cmd], cwd=cwd or ROOT)
    if result.returncode != 0:
        raise SystemExit(f"\n  ERROR: command exited with code {result.returncode}")


def read_version() -> str:
    text = (ROOT / "app" / "_version.py").read_text(encoding="utf-8")
    m = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    if not m:
        raise SystemExit("  ERROR: could not parse __version__ from app/_version.py")
    return m.group(1)


def sync_iss_version(version: str) -> None:
    iss_path = ROOT / "installer" / "gravity_nexus_setup.iss"
    text = iss_path.read_text(encoding="utf-8")
    pattern = r'(#define\s+AppVersion\s+")[^"]*(")'
    new_text, count = re.subn(pattern, rf'\g<1>{version}\g<2>', text)
    if count == 0:
        raise SystemExit("  ERROR: #define AppVersion not found in .iss file")
    if new_text == text:
        print(f"  [ok] AppVersion already {version!r}")
    else:
        iss_path.write_text(new_text, encoding="utf-8")
        print(f"  [updated] AppVersion -> {version!r}")


def create_build_venv() -> None:
    if BUILD_VENV.exists():
        print(f"  Removing existing {BUILD_VENV.name}\\")
        try:
            shutil.rmtree(BUILD_VENV)
        except OSError as exc:
            raise SystemExit(
                f"  ERROR: could not remove {BUILD_VENV} — close any process using "
                f"files inside it and try again.\n  {exc}"
            ) from exc
    print(f"  Creating {BUILD_VENV.name}\\")
    venv.create(BUILD_VENV, with_pip=True, clear=True)


def install_deps() -> None:
    _run([VENV_PYTHON, "-m", "pip", "install", "--upgrade", "pip", "--quiet"])
    print()
    print("  Installing runtime dependencies …")
    _run([VENV_PYTHON, "-m", "pip", "install", "-r", "requirements-runtime.txt"])
    print()
    print("  Installing nuitka (build tool) …")
    _run([VENV_PYTHON, "-m", "pip", "install", "nuitka[onefile]"])


def build_exe(version: str) -> None:
    print(f"  Building Gravity Nexus v{version} exe …")
    print()
    _run([VENV_PYTHON, "build_nuitka.py"])
    exe = ROOT / "dist" / "main.exe"
    if not exe.exists():
        raise SystemExit(f"  ERROR: expected output not found: {exe}")
    size_mb = exe.stat().st_size / (1024 * 1024)
    print(f"\n  [ok] dist\\main.exe ({size_mb:.1f} MB)")


def find_iscc() -> Path:
    candidates: list[Path] = []
    which = shutil.which("ISCC") or shutil.which("iscc")
    if which:
        candidates.append(Path(which))
    candidates += [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 5\ISCC.exe"),
    ]
    for c in candidates:
        if c.is_file():
            print(f"  [ok] Found ISCC.exe: {c}")
            return c
    raise SystemExit(
        "  ERROR: ISCC.exe not found.\n"
        "  Install Inno Setup 6 from https://jrsoftware.org/isinfo.php\n"
        "  or add it to your PATH."
    )


def build_installer(iscc: Path, version: str) -> None:
    iss_file = ROOT / "installer" / "gravity_nexus_setup.iss"
    _run([iscc, str(iss_file)])
    output = ROOT / "installer" / "Output" / f"GravityNexus_Setup_{version}.exe"
    if not output.exists():
        raise SystemExit(f"  ERROR: expected installer not found: {output}")
    size_mb = output.stat().st_size / (1024 * 1024)
    print(f"\n  [ok] installer\\Output\\{output.name} ({size_mb:.1f} MB)")


def main() -> None:
    _banner(1, "Read version")
    version = read_version()
    print(f"  Version: {version}")

    _banner(2, "Sync installer version")
    sync_iss_version(version)

    if SKIP_VENV:
        _banner(3, "Build venv — SKIPPED (--skip-venv)")
        if not VENV_PYTHON.exists():
            raise SystemExit(
                f"  ERROR: --skip-venv was given but {VENV_PYTHON} does not exist.\n"
                "  Run without --skip-venv first."
            )
    else:
        _banner(3, "Create build venv")
        create_build_venv()
        install_deps()

    _banner(4, "Build executable (Nuitka)")
    build_exe(version)

    _banner(5, "Locate Inno Setup compiler")
    iscc = find_iscc()

    _banner(6, "Build installer (Inno Setup)")
    build_installer(iscc, version)

    print(f"\n{'=' * _WIDTH}")
    print(f"  RELEASE COMPLETE — Gravity Nexus v{version}")
    print(f"  Executable : dist\\main.exe")
    print(f"  Installer  : installer\\Output\\GravityNexus_Setup_{version}.exe")
    print(f"{'=' * _WIDTH}\n")


if __name__ == "__main__":
    main()
