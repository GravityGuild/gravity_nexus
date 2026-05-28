"""FakeLogService — writes synthetic EQ log lines to a temp file for testing.

Architecture
------------
Creates a temporary directory containing a single fake EQ log file named
``eqlog_TestDummy_project1999.txt``.  Calling ``start(parser_svc)`` redirects
the ``LogParserService`` to tail this file so every injected line propagates
through the full matcher pipeline.

Calling ``stop()`` stops the parser and removes the temp directory.

Usage
-----
    from services.fake_log_service import FakeLogService

    svc = FakeLogService()
    svc.start(parser_svc)
    svc.inject_line("You have entered Plane of Time.")
    svc.inject_preset("guild_burst")
    svc.replay_lines(my_lines, interval_ms=150)
    ...
    svc.stop()
"""
from __future__ import annotations

import logging
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QTimer, Signal

log = logging.getLogger(__name__)

# ── EQ timestamp format ────────────────────────────────────────────────────────
_EQ_TS_FMT = "%a %b %d %H:%M:%S %Y"

# ── Preset log-line scenarios ──────────────────────────────────────────────────
PRESETS: dict[str, list[str]] = {
    "Raid Logs": [
        "nexusraidlog is not online at this time.",
        "Players on EverQuest:",
        "---------------------------",
        "[60 Grandmaster] Pandemick (Iksar) <Gravity>  LFG",
        "[60 Assassin] Flipsides (Gnome) <Gravity>",
        "[60 Assassin] Daelthar (Dwarf) <Gravity>",
        "[60 Warlord] Nodtveidt (Dark Elf) <Gravity>",
        "[60 Grandmaster] Diikembe (Iksar) <Gravity>",
        "[60 Assassin] Roging (Dwarf) <Gravity>",
        "[60 High Priest] Healii (Dwarf) <Gravity>",
        "[60 Assassin] Spineshank (Halfling) <Gravity>",
        "[60 High Priest] Agsafety (Halfling) <Gravity>",
        "[60 High Priest] Eusebio (Halfling) <Gravity>",
        "[60 Grandmaster] Lanneth (Human) <Gravity>",
        "[60 High Priest] Belshazar (Human) <Gravity>",
        "[60 Warlord] Allishya (Dark Elf) <Gravity>",
        "[60 High Priest] Sinaelr (Dark Elf) <Gravity>",
        "[60 Warlord] Dubbstep (Gnome) <Gravity>",
        "[60 Phantasmist] Amfar (Iksar) <Gravity>",
        "[60 Grandmaster] Daewen (Human) <Gravity>",
        "[54 Vicar] Awaloo (Gnome) <Gravity>",
        "[60 High Priest] Bellossom (Gnome) <Gravity>",
        "[59 Templar] Naughity (Dark Elf) <Gravity>",
        "[60 High Priest] Heelur (Dark Elf) <Gravity>",
        "There are 21 players in The Plane of Hate.",
    ],
    "Who Logs": [
        "Players on EverQuest:",
        "---------------------------",
        "[1 Cleric] Chealin (Dwarf) <South Qeynos Bait and Tackle>",
        "[18 Shaman] Liyankaro (Barbarian)",
        "[60 Warlord] Krayziefoo (Barbarian) <The Second Sons>",
        "AFK [ANONYMOUS] Horza",
        "[50 Necromancer] Shoza (Gnome)",
        "[60 Virtuoso] Media (Half Elf) <The Second Sons>",
        "[ANONYMOUS] Antheri",
        "[5 Bard] Hoarsemule (Human) <Riot>",
        "[ANONYMOUS] Sugarfoot  <Fuse>",
        "[60 Warlord] Satoshibtc (Barbarian) <Gravity>",
        "[2 Bard] Zerotone (Half Elf)",
        "AFK [1 Warrior] Potiondealer (Human) <Dungeon Homies>",
        "[ANONYMOUS] Ozium  <Dawn Believers>",
        "[6 Bard] Traderpop (Half Elf)",
        "[10 Cleric] Lillymoon (Gnome) <The Second Sons>",
        "[5 Bard] Rurg (Human) <Gravity>",
        "There are 16 players in East Commonlands.",
    ],
    "/who heelur": [
        "Players on EverQuest:",
        "---------------------------",
        "[60 High Priest] Heelur (Dark Elf) <Gravity>",
        "There is 1 player in Temple of Veeshan.",
    ],
    "/who lyle": [
        "Players on EverQuest:",
        "---------------------------",
        "[60 Phantasmist] Lyle (Dark Elf) <Gravity>",
        "There is 1 player in Temple of Veeshan.",
    ],
    "/who timmin": [
        "Players on EverQuest:",
        "---------------------------",
        "[ANONYMOUS] Timmin  <Gravity>",
        "There is 1 player in West Commonlands.",
    ],
    "Zone In — Plane of Time": [
        "You have entered Plane of Time.",
    ],
    "Zone In — Nexus": [
        "You have entered The Nexus.",
    ],
    "Zone In — Plane of Fear": [
        "You have entered The Plane of Fear.",
    ],
    "Zone Hop (3 zones)": [
        "You have entered East Commonlands.",
        "You have entered West Karana.",
        "You have entered Qeynos Hills.",
    ],
    "Guild Chat — single": [
        "Zandakon tells the guild, 'All raid members get to the arena!'",
    ],
    "Guild Chat — burst": [
        "Zandakon tells the guild, 'All raid members get to the arena!'",
        "Sylvindra tells the guild, 'On my way!'",
        "Vaelthor tells the guild, 'Ready at the entrance.'",
        "Drakonis tells the guild, 'Be there in 30 seconds.'",
        "Thalenos tells the guild, 'Ready!'",
        "Lumarei tells the guild, 'Coming!'",
    ],
    "Death Messages": [
        "Drakonis has been slain by Nagafen!",
        "Vaelthor has been slain by Nagafen!",
        "Syvaris has been slain by Nagafen!",
    ],
    "Random Tells": [
        "Minstrelina tells you, 'Hey, can you group?'",
        "Gordrake tells you, 'Good kill on that patrol.'",
    ],
    "Mixed Activity": [
        "You have entered Plane of Hate.",
        "Zandakon tells the guild, 'Pulling in 10 seconds!'",
        "Vaelthor tells the guild, 'OOM — please med.'",
        "Sylvindra tells the guild, 'Ready!'",
        "Drakonis has been slain by Master of Terror!",
        "Zandakon tells the guild, 'Recover and rebuff.'",
    ],
}


class FakeLogService(QObject):
    """Manages a temporary EQ log file for testing purposes.

    Signals
    -------
    line_injected(str):
        Emitted each time a line is written to the fake log.
    replay_started():
        Emitted when a timed replay begins.
    replay_finished():
        Emitted when a timed replay completes (or is cancelled).
    replay_progress(int, int):
        ``(current_index, total_lines)`` emitted after each line during replay.
    session_started():
        Emitted when the fake-log session starts (parser redirected).
    session_stopped():
        Emitted when the fake-log session ends.
    """

    line_injected = Signal(str)
    replay_started = Signal()
    replay_finished = Signal()
    replay_progress = Signal(int, int)   # (current, total)
    session_started = Signal()
    session_stopped = Signal()

    _DEFAULT_CHAR_NAME = "TestDummy"

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._temp_dir: Optional[Path] = None
        self._log_path: Optional[Path] = None
        self._fh = None  # open file handle for appending
        self._char_name = self._DEFAULT_CHAR_NAME

        self._parser_svc = None  # set by start()

        # Replay state
        self._replay_lines: list[str] = []
        self._replay_idx: int = 0
        self._replay_timer = QTimer(self)
        self._replay_timer.setSingleShot(False)
        self._replay_timer.timeout.connect(self._on_replay_tick)

    # ── Properties ─────────────────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        """True while the fake log temp directory exists and is being tailed."""
        return self._temp_dir is not None

    @property
    def is_replaying(self) -> bool:
        """True while a timed replay is running."""
        return self._replay_timer.isActive()

    @property
    def character_name(self) -> str:
        return self._char_name

    # ── Session control ────────────────────────────────────────────────────────

    def start(self, parser_svc, character_name: str = "") -> None:  # noqa: ANN001
        """Create the temp log file and redirect *parser_svc* to tail it.

        *character_name* controls the log filename (and therefore the character
        name the parser reports via ``active_file_changed``).  Defaults to
        ``"TestDummy"`` when empty or not provided.

        If a session is already active it is stopped first.
        """
        if self.is_active:
            self.stop()

        self._char_name = (character_name.strip() or self._DEFAULT_CHAR_NAME)
        self._parser_svc = parser_svc

        # Create temp directory + empty log file
        tmp = tempfile.mkdtemp(prefix="gravity_nexus_fakelog_")
        self._temp_dir = Path(tmp)
        self._log_path = self._temp_dir / f"eqlog_{self._char_name}_project1999.txt"
        self._log_path.touch()

        # Open an append handle (kept open so writes are cheap)
        self._fh = self._log_path.open("a", encoding="utf-8")

        log.info("FakeLogService: temp log at %s", self._log_path)
        self._parser_svc.start(str(self._temp_dir))
        self.session_started.emit()

    def stop(self) -> None:
        """Stop any running replay, close the file handle, and clean up."""
        self.stop_replay()

        if self._fh is not None:
            try:
                self._fh.close()
            except Exception:  # noqa: BLE001
                pass
            self._fh = None

        if self._parser_svc is not None:
            try:
                self._parser_svc.stop()
            except Exception:  # noqa: BLE001
                pass
            self._parser_svc = None

        if self._temp_dir is not None:
            try:
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            except Exception:  # noqa: BLE001
                pass
            self._temp_dir = None
            self._log_path = None

        self.session_stopped.emit()
        log.info("FakeLogService: session stopped")

    # ── Line injection ─────────────────────────────────────────────────────────

    def inject_line(self, text: str) -> None:
        """Write *text* as a new EQ log line with the current timestamp.

        The EQ timestamp bracket ``[Day Mon DD HH:MM:SS YYYY]`` is added
        automatically.  *text* should be just the message body.
        """
        ts = datetime.now().strftime(_EQ_TS_FMT)
        raw = f"[{ts}] {text}"
        self._write(raw)

    def inject_raw(self, raw: str) -> None:
        """Write *raw* exactly as provided (no timestamp added)."""
        self._write(raw)

    def inject_preset(self, preset_name: str) -> None:
        """Inject all lines from the named preset immediately (no delay).

        Each line gets a fresh timestamp as it is injected.
        """
        lines = PRESETS.get(preset_name)
        if lines is None:
            log.warning("FakeLogService: unknown preset %r", preset_name)
            return
        for line in lines:
            self.inject_line(line)

    def clear(self) -> None:
        """Truncate the fake log file (history is erased; parser keeps running)."""
        if self._fh is not None:
            self._fh.close()
        if self._log_path is not None:
            self._log_path.write_text("", encoding="utf-8")
            self._fh = self._log_path.open("a", encoding="utf-8")
        log.debug("FakeLogService: log cleared")

    # ── Timed replay ───────────────────────────────────────────────────────────

    def replay_lines(self, lines: list[str], interval_ms: int = 500) -> None:
        """Replay *lines* one at a time, *interval_ms* apart.

        Each line is treated as a raw body — a timestamp is added automatically.
        Calling this while a replay is already running cancels the previous one.
        """
        self.stop_replay()
        if not lines:
            return

        self._replay_lines = list(lines)
        self._replay_idx = 0
        self._replay_timer.setInterval(max(10, interval_ms))
        self.replay_started.emit()
        self._replay_timer.start()

    def stop_replay(self) -> None:
        """Cancel any running replay and emit ``replay_finished``."""
        if self._replay_timer.isActive():
            self._replay_timer.stop()
            self.replay_finished.emit()

    # ── Internal ───────────────────────────────────────────────────────────────

    def _write(self, raw: str) -> None:
        """Append *raw* (plus newline) to the fake log file."""
        if not self.is_active or self._fh is None:
            log.warning("FakeLogService.inject called with no active session — ignored")
            return
        self._fh.write(raw + "\n")
        self._fh.flush()
        self.line_injected.emit(raw)

    def _on_replay_tick(self) -> None:
        """Called by the replay timer: write one line then advance."""
        if self._replay_idx >= len(self._replay_lines):
            self._replay_timer.stop()
            self.replay_finished.emit()
            return

        line = self._replay_lines[self._replay_idx]
        self.inject_line(line)
        self._replay_idx += 1
        self.replay_progress.emit(self._replay_idx, len(self._replay_lines))

        if self._replay_idx >= len(self._replay_lines):
            self._replay_timer.stop()
            self.replay_finished.emit()

