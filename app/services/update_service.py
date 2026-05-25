"""UpdateService — checks GitHub Releases for new versions and manages installation."""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

import requests

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from _version import __version__

log = logging.getLogger(__name__)

_GITHUB_API_URL = "https://api.github.com/repos/GravityGuild/gravity_nexus/releases/latest"
_USER_AGENT = f"GravityNexus/{__version__}"


def _github_headers(token: str = "") -> dict[str, str]:
    """Build GitHub API request headers, preferring an explicit token over env vars."""
    headers: dict[str, str] = {"User-Agent": _USER_AGENT}
    resolved = token or os.environ.get("GRAVITY_NEXUS_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if resolved:
        headers["Authorization"] = f"Bearer {resolved}"
    return headers


def _parse_version(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.lstrip("v").split("."))


class _UpdateCheckerThread(QThread):
    """Background thread: fetches latest GitHub release and compares to current version."""

    result = Signal(str, str)  # (version, download_url)
    no_update = Signal()
    error = Signal(str)

    def __init__(self, token: str = "", parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._token = token

    def run(self) -> None:
        try:
            resp = requests.get(
                _GITHUB_API_URL,
                headers=_github_headers(self._token),
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            tag = data.get("tag_name", "")
            latest = tag.lstrip("v")
            if not latest:
                self.error.emit("Invalid release tag in GitHub response")
                return

            try:
                latest_tuple = _parse_version(latest)
                current_tuple = _parse_version(__version__)
            except (ValueError, AttributeError) as exc:
                self.error.emit(f"Version parse error: {exc}")
                return

            if latest_tuple <= current_tuple:
                self.no_update.emit()
                return

            # Find the Windows installer asset
            assets = data.get("assets", [])
            download_url = ""
            for asset in assets:
                name = asset.get("name", "")
                if name.startswith("GravityNexus_Setup_") and name.endswith(".exe"):
                    download_url = asset.get("browser_download_url", "")
                    break

            if not download_url:
                self.error.emit(f"No Windows installer asset found for release {latest}")
                return

            self.result.emit(latest, download_url)

        except requests.RequestException as exc:
            self.error.emit(f"Network error during update check: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.error.emit(f"Update check failed: {exc}")


class _UpdateDownloaderThread(QThread):
    """Background thread: streams installer download to a temp directory."""

    progress = Signal(int)  # 0–100
    done = Signal(str)      # absolute path to installer
    error = Signal(str)

    def __init__(self, version: str, url: str, token: str = "", parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._version = version
        self._url = url
        self._token = token

    def run(self) -> None:
        try:
            dest_dir = Path(tempfile.gettempdir()) / "gravity_nexus_update"
            dest_dir.mkdir(exist_ok=True)
            dest = dest_dir / f"GravityNexus_Setup_{self._version}.exe"

            resp = requests.get(
                self._url,
                headers=_github_headers(self._token),
                stream=True,
                timeout=120,
            )
            resp.raise_for_status()

            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0

            with dest.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            self.progress.emit(int(downloaded * 100 / total))

            self.progress.emit(100)
            self.done.emit(str(dest))

        except requests.RequestException as exc:
            self.error.emit(f"Download failed: {exc}")
        except OSError as exc:
            self.error.emit(f"File error during download: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.error.emit(f"Unexpected download error: {exc}")


class UpdateService(QObject):
    """Manages application update checking and installation.

    Lifecycle:
        1. ``start()`` — call after the main window is visible; schedules the
           first background check based on ``update_check_interval_hours``.
        2. ``check_for_updates()`` — fires ``_UpdateCheckerThread`` immediately.
        3. ``download_update(version, url)`` — fires ``_UpdateDownloaderThread``.
        4. ``install_and_restart(path)`` — launches installer silently then emits
           ``restart_requested`` so the composition root can call
           ``window.force_quit()``.
        5. ``shutdown()`` — stop all background threads on app close.
    """

    update_available = Signal(str, str)   # (version, download_url)
    update_downloaded = Signal(str, str)  # (version, installer_path)
    download_progress = Signal(int)       # 0–100
    update_status = Signal(str)
    update_error = Signal(str)
    restart_requested = Signal()

    def __init__(self, settings_svc) -> None:
        super().__init__()
        self._settings_svc = settings_svc
        self._checker: Optional[_UpdateCheckerThread] = None
        self._downloader: Optional[_UpdateDownloaderThread] = None
        self._schedule_timer: Optional[QTimer] = None

    # ── Public API ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Schedule or immediately run the first update check."""
        if not self._settings_svc.settings.general.check_for_updates:
            return

        general = self._settings_svc.settings.general
        elapsed = time.time() - general.last_update_check_timestamp
        interval_secs = general.update_check_interval_hours * 3600

        if elapsed >= interval_secs:
            self.check_for_updates()
        else:
            delay_ms = int((interval_secs - elapsed) * 1000)
            self._schedule_timer = QTimer(self)
            self._schedule_timer.setSingleShot(True)
            self._schedule_timer.timeout.connect(self.check_for_updates)
            self._schedule_timer.start(delay_ms)
            log.debug(
                "Update check scheduled in %.1f hours",
                (interval_secs - elapsed) / 3600,
            )

    def check_for_updates(self) -> None:
        """Immediately trigger an update check. No-op if one is already running."""
        if self._checker is not None:
            return

        log.info("Checking for updates (current: v%s)", __version__)

        token = self._settings_svc.settings.general.github_token
        self._checker = _UpdateCheckerThread(token=token, parent=self)
        self._checker.result.connect(self._on_update_found)
        self._checker.no_update.connect(self._on_no_update)
        self._checker.error.connect(self._on_check_error)
        self._checker.finished.connect(self._on_checker_finished)
        self._checker.start()

    def download_update(self, version: str, url: str) -> None:
        """Start downloading the installer for *version* from *url*."""
        if self._downloader is not None:
            return

        log.info("Downloading update v%s", version)
        self.update_status.emit(f"Downloading v{version}…")

        token = self._settings_svc.settings.general.github_token
        self._downloader = _UpdateDownloaderThread(version, url, token=token, parent=self)
        self._downloader.progress.connect(self.download_progress)
        self._downloader.done.connect(lambda path: self._on_download_done(version, path))
        self._downloader.error.connect(self._on_download_error)
        self._downloader.finished.connect(self._on_downloader_finished)
        self._downloader.start()

    def install_and_restart(self, installer_path: str) -> None:
        """Save settings, launch the installer silently, then signal force-quit."""
        log.info("Launching installer: %s", installer_path)
        self._settings_svc.save()

        flags = 0
        if sys.platform == "win32":
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

        try:
            subprocess.Popen(
                [installer_path, "/SILENT", "/NORESTART"],
                creationflags=flags,
            )
        except OSError as exc:
            log.error("Failed to launch installer: %s", exc)
            self.update_error.emit(f"Could not launch installer: {exc}")
            return

        self.restart_requested.emit()

    def shutdown(self) -> None:
        """Stop all background threads before the application exits."""
        if self._schedule_timer is not None:
            self._schedule_timer.stop()
        if self._checker is not None:
            self._checker.quit()
            self._checker.wait(2000)
        if self._downloader is not None:
            self._downloader.quit()
            self._downloader.wait(2000)

    # ── Internal slots ─────────────────────────────────────────────────────────

    @Slot(str, str)
    def _on_update_found(self, version: str, url: str) -> None:
        log.info("Update available: v%s", version)
        self._record_check_timestamp()
        self.update_available.emit(version, url)
        self.update_status.emit(f"Update available: v{version}")

    @Slot()
    def _on_no_update(self) -> None:
        log.info("No update available (current: v%s)", __version__)
        self._record_check_timestamp()
        self.update_status.emit(f"Up to date (v{__version__})")

    @Slot(str)
    def _on_check_error(self, msg: str) -> None:
        log.warning("Update check error: %s", msg)
        self.update_error.emit(msg)
        self.update_status.emit("Update check failed")

    @Slot(str, str)
    def _on_download_done(self, version: str, path: str) -> None:
        log.info("Update downloaded: v%s → %s", version, path)
        self.update_downloaded.emit(version, path)
        self.update_status.emit(f"v{version} ready to install")

    @Slot(str)
    def _on_download_error(self, msg: str) -> None:
        log.error("Download error: %s", msg)
        self.update_error.emit(msg)
        self.update_status.emit("Download failed")

    @Slot()
    def _on_checker_finished(self) -> None:
        if self._checker is not None:
            self._checker.deleteLater()
            self._checker = None

    @Slot()
    def _on_downloader_finished(self) -> None:
        if self._downloader is not None:
            self._downloader.deleteLater()
            self._downloader = None

    def _record_check_timestamp(self) -> None:
        self._settings_svc.settings.general.last_update_check_timestamp = time.time()
        self._settings_svc.save()
