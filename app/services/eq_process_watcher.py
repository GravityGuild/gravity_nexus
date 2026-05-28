"""EqProcessWatcher — detects eqgame.exe crashes that produce no dbg.txt event.

When EQ starts, dbg.txt records "Starting EverQuest (Build ...)".  Normal exits
all write a final line that the DisconnectDbgMatcher or CampDbgMatcher catches.
A crash skips that line entirely.

After the startup dbg.txt scan, ``on_startup_scan_complete`` reconciles state:
if eqgame.exe is not running, any character state set during the scan is stale
(left over from a pre-crash session) and ``game_crashed`` is emitted to clear
it.  If EQ is running but ``game_started`` was outside the scan window, the
watcher is armed retroactively.

Usage (in main.py)::

    watcher = EqProcessWatcher()
    log_parser_svc.game_started.connect(watcher.on_game_started)
    log_parser_svc.startup_scan_complete.connect(watcher.on_startup_scan_complete)
    log_parser_svc.character_offline.connect(watcher.on_clean_exit)
    watcher.game_crashed.connect(lambda: gravity_bot_svc.set_character(NO_CHARACTER))
    ...
    watcher.stop()  # on app shutdown
"""
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal, Slot

log = logging.getLogger(__name__)

_PROCESS_NAME = "eqgame.exe"


def _find_eq_process():
    """Return a psutil.Process for eqgame.exe, or None if not running."""
    try:
        import psutil
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() == _PROCESS_NAME:
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as exc:  # noqa: BLE001
        log.warning("EqProcessWatcher: process scan failed: %s", exc)
    return None


class _WatchThread(QThread):
    """Polls until the watched PID is no longer in the process list, then emits
    ``process_exited``.

    Uses ``psutil.pid_exists()`` rather than ``proc.wait()`` because the latter
    requires ``PROCESS_QUERY_INFORMATION`` access, which may be denied for game
    processes.  ``pid_exists()`` queries the system-wide process list and needs
    no per-process handle.  Checks every second so the thread can exit cleanly
    on app shutdown without waiting for eqgame.exe.
    """

    process_exited = Signal()

    def __init__(self, pid: int, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._pid = pid
        self._running = True

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        try:
            import psutil
            while self._running:
                if not psutil.pid_exists(self._pid):
                    break
                self.msleep(1_000)
        except Exception as exc:  # noqa: BLE001
            log.warning("EqProcessWatcher: watch thread error (pid=%d): %r", self._pid, exc)
            return

        if self._running:
            self.process_exited.emit()


class EqProcessWatcher(QObject):
    """Detects eqgame.exe crashes that write no cleanup event to dbg.txt."""

    game_crashed = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._watch_thread: Optional[_WatchThread] = None
        self._clean_exit_seen = False

    @Slot()
    def on_game_started(self) -> None:
        """Called when dbg.txt records EQ launching.  Arms the process watcher."""
        self._stop_watcher()
        self._clean_exit_seen = False

        proc = _find_eq_process()
        if proc is None:
            log.debug("EqProcessWatcher: game_started fired but eqgame.exe not found (historical scan?)")
            return

        self._arm(proc)

    @Slot()
    def on_startup_scan_complete(self) -> None:
        """Called after the dbg.txt historical scan finishes.

        Reconciles the character state set during the scan against actual
        process state.  Two cases handled:

        - EQ is running but the watcher isn't armed (``game_started`` was
          beyond the scan window) → arm it now so future crashes are caught.
        - EQ is not running → the scan replayed stale state from before a
          crash; emit ``game_crashed`` to clear character state.
        """
        proc = _find_eq_process()
        if proc is None:
            log.info("EqProcessWatcher: eqgame.exe not running after startup scan — clearing stale character state")
            self.game_crashed.emit()
        elif self._watch_thread is None:
            log.info(
                "EqProcessWatcher: eqgame.exe running (pid=%d) but not yet watched — arming now",
                proc.pid,
            )
            self._clean_exit_seen = False
            self._arm(proc)

    @Slot()
    def on_clean_exit(self) -> None:
        """Called when dbg.txt records a clean disconnect.  Disarms the watcher."""
        if self._watch_thread is not None:
            log.debug("EqProcessWatcher: clean exit — disarming watcher")
            self._clean_exit_seen = True
            self._stop_watcher()

    def stop(self) -> None:
        """Shut down the watcher thread.  Call from the app shutdown path."""
        self._stop_watcher()

    def _arm(self, proc) -> None:
        log.info("EqProcessWatcher: armed for eqgame.exe (pid=%d)", proc.pid)
        self._watch_thread = _WatchThread(proc.pid, self)
        self._watch_thread.process_exited.connect(self._on_process_exited)
        self._watch_thread.start()

    def _stop_watcher(self) -> None:
        if self._watch_thread is not None:
            self._watch_thread.stop()
            self._watch_thread.wait(2_000)
            self._watch_thread = None

    @Slot()
    def _on_process_exited(self) -> None:
        self._watch_thread = None
        if self._clean_exit_seen:
            return
        log.warning("EqProcessWatcher: eqgame.exe exited without a clean disconnect — emitting game_crashed")
        self.game_crashed.emit()
