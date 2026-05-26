"""UpdateService — checks Gravity Bot API for new versions and manages installation."""
from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import requests

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from _version import __version__

if TYPE_CHECKING:
    from auth.api_client import ApiClient

log = logging.getLogger(__name__)

_LATEST_PATH = "/api/v1/updates/latest"
_DOWNLOAD_PATH = "/api/v1/updates/download/v{version}"
_USER_AGENT = f"GravityNexus/{__version__}"


def _parse_version(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.lstrip("v").split("."))


class _UpdateCheckerThread(QThread):
    """Background thread: fetches latest release from Gravity Bot API and compares versions."""

    result = Signal(str, str)  # (version, asset_name)
    no_update = Signal()
    error = Signal(str)

    def __init__(self, base_url: str, token: str, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._base_url = base_url
        self._token = token

    def run(self) -> None:
        try:
            url = f"{self._base_url}{_LATEST_PATH}"
            headers = {
                "User-Agent": _USER_AGENT,
                "Authorization": f"Bearer {self._token}",
            }
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            tag = data.get("version", "")
            latest = tag.lstrip("v")
            if not latest:
                self.error.emit("Invalid version in API response")
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

            assets = data.get("assets", [])
            asset_name = ""
            for asset in assets:
                name = asset.get("name", "")
                if name.startswith("GravityNexus_Setup_") and name.endswith(".exe"):
                    asset_name = name
                    break

            if not asset_name:
                self.error.emit(f"No Windows installer asset found for release {latest}")
                return

            self.result.emit(latest, asset_name)

        except requests.RequestException as exc:
            self.error.emit(f"Network error during update check: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.error.emit(f"Update check failed: {exc}")


class _UpdateDownloaderThread(QThread):
    """Background thread: streams installer download to a temp directory."""

    progress = Signal(int)  # 0–100
    done = Signal(str)      # absolute path to installer
    error = Signal(str)

    def __init__(
        self,
        version: str,
        asset_name: str,
        base_url: str,
        token: str,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._version = version
        self._asset_name = asset_name
        self._base_url = base_url
        self._token = token

    def run(self) -> None:
        try:
            dest_dir = Path(tempfile.gettempdir()) / "gravity_nexus_update"
            dest_dir.mkdir(exist_ok=True)
            dest = dest_dir / f"GravityNexus_Setup_{self._version}.exe"

            url = f"{self._base_url}{_DOWNLOAD_PATH.format(version=self._version)}"
            headers = {
                "User-Agent": _USER_AGENT,
                "Authorization": f"Bearer {self._token}",
            }
            resp = requests.get(
                url,
                headers=headers,
                params={"asset": self._asset_name},
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
        1. ``set_api_client(api)`` — call after the ApiClient is created to wire up
           the authenticated HTTP client.
        2. ``start()`` — call after the main window is visible; schedules the
           first background check based on ``update_check_interval_hours``.
        3. ``check_for_updates()`` — fires ``_UpdateCheckerThread`` immediately.
        4. ``download_update(version, asset_name)`` — fires ``_UpdateDownloaderThread``.
        5. ``install_and_restart(path)`` — launches installer silently then emits
           ``restart_requested`` so the composition root can call
           ``window.force_quit()``.
        6. ``shutdown()`` — stop all background threads on app close.
    """

    update_available = Signal(str, str)   # (version, asset_name)
    update_downloaded = Signal(str, str)  # (version, installer_path)
    download_progress = Signal(int)       # 0–100
    update_status = Signal(str)
    update_error = Signal(str)
    restart_requested = Signal()

    def __init__(self, settings_svc) -> None:
        super().__init__()
        self._settings_svc = settings_svc
        self._api_client: Optional[ApiClient] = None
        self._checker: Optional[_UpdateCheckerThread] = None
        self._downloader: Optional[_UpdateDownloaderThread] = None
        self._schedule_timer: Optional[QTimer] = None

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_api_client(self, api_client: ApiClient) -> None:
        self._api_client = api_client

    def start(self) -> None:
        """Schedule or immediately run the first update check."""
        if not self._settings_svc.settings.general.check_for_updates:
            return
        if self._api_client is None:
            log.warning("UpdateService.start() called before set_api_client()")
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
        if self._api_client is None:
            log.warning("check_for_updates() called before set_api_client()")
            return

        log.info("Checking for updates (current: v%s)", __version__)

        base_url = self._api_client.base_url
        token = self._api_client._auth.get_access_token() or ""
        self._checker = _UpdateCheckerThread(base_url=base_url, token=token, parent=self)
        self._checker.result.connect(self._on_update_found)
        self._checker.no_update.connect(self._on_no_update)
        self._checker.error.connect(self._on_check_error)
        self._checker.finished.connect(self._on_checker_finished)
        self._checker.start()

    def download_update(self, version: str, asset_name: str) -> None:
        """Start downloading the installer for *version* identified by *asset_name*."""
        if self._downloader is not None:
            return
        if self._api_client is None:
            log.warning("download_update() called before set_api_client()")
            return

        log.info("Downloading update v%s (%s)", version, asset_name)
        self.update_status.emit(f"Downloading v{version}…")

        base_url = self._api_client.base_url
        token = self._api_client._auth.get_access_token() or ""
        self._downloader = _UpdateDownloaderThread(
            version, asset_name, base_url, token=token, parent=self
        )
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
    def _on_update_found(self, version: str, asset_name: str) -> None:
        log.info("Update available: v%s", version)
        self._record_check_timestamp()
        self.update_available.emit(version, asset_name)
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
