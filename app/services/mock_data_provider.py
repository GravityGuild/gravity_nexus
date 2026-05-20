"""MockDataProvider — emits realistic mock EverQuest combat data.

Drives the OverlayPreview widget with simulated real-time updates.
No actual parser logic is implemented here.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from PySide6.QtCore import QObject, QTimer, Signal


@dataclass
class CombatantEntry:
    name: str
    dps: int
    total_damage: int
    percent: float  # 0.0 – 1.0 relative to top parse
    class_abbr: str  # e.g. "WAR", "ROG", "WIZ"


@dataclass
class HealerEntry:
    name: str
    hps: int
    total_heals: int
    percent: float
    class_abbr: str


@dataclass
class CombatLogLine:
    text: str
    color_key: str = "normal"  # normal | crit | death | buff | debuff


@dataclass
class RaidTimer:
    label: str
    seconds_remaining: int
    max_seconds: int
    color_key: str = "normal"  # normal | warning | danger


@dataclass
class MockSnapshot:
    """A complete snapshot of mock overlay data."""

    dps_entries: list[CombatantEntry] = field(default_factory=list)
    healer_entries: list[HealerEntry] = field(default_factory=list)
    combat_log: list[CombatLogLine] = field(default_factory=list)
    raid_timers: list[RaidTimer] = field(default_factory=list)
    fight_name: str = "The Sleeper's Tomb"
    fight_duration: int = 0  # seconds


_DPS_ROSTER: list[tuple[str, str, int]] = [
    ("Zandakon", "WIZ", 52000),
    ("Thalenos", "ROG", 47000),
    ("Vaelthor", "MNK", 41000),
    ("Drakonis", "BER", 38000),
    ("Syvaris", "MAG", 34000),
    ("Lumarei", "RNG", 29000),
]

_HEALER_ROSTER: list[tuple[str, str, int]] = [
    ("Sylvindra", "CLR", 22000),
    ("Orvindal", "SHM", 16000),
    ("Tyrael", "DRU", 12000),
]

_LOG_TEMPLATES: list[tuple[str, str]] = [
    ("{attacker} hits {target} for {dmg} points of damage.", "normal"),
    ("{attacker} critically hits {target} for {dmg} points!", "crit"),
    ("{attacker} slashes {target} for {dmg} damage.", "normal"),
    ("{healer} heals {target} for {heal} points.", "buff"),
    ("{target} has been slain!", "death"),
    ("{mob} begins to cast a spell!", "debuff"),
    ("{attacker} fires an arrow at {target} for {dmg} damage.", "normal"),
    ("You resist the {mob}'s spell!", "buff"),
    ("{mob} engulfs {target} in flames for {dmg} damage!", "crit"),
]

_NAMES = ["Zandakon", "Thalenos", "Vaelthor", "Drakonis", "Syvaris", "Sylvindra"]
_MOBS = ["The Progenitor", "Vox", "Nagafen", "Trakanon", "Gorenaire"]


class MockDataProvider(QObject):
    """Periodically emits updated mock combat data.

    Signals
    -------
    data_updated(MockSnapshot):
        Fired every *update_interval_ms* milliseconds.
    """

    data_updated = Signal(object)  # MockSnapshot

    def __init__(
        self, update_interval_ms: int = 2000, parent: Optional[QObject] = None
    ) -> None:
        super().__init__(parent)
        self._interval = update_interval_ms
        self._timer = QTimer(self)
        self._timer.setInterval(self._interval)
        self._timer.timeout.connect(self._emit_update)

        self._fight_elapsed = 0
        self._log_lines: list[CombatLogLine] = []
        self._timers: list[RaidTimer] = [
            RaidTimer("Fippy Darkpaw Repop", 154, 300),
            RaidTimer("Chain stun immunity", 17, 60),
            RaidTimer("AE Rampage window", 73, 120),
        ]

    # ── Control ────────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def get_initial_snapshot(self) -> MockSnapshot:
        return self._build_snapshot()

    # ── Private ────────────────────────────────────────────────────────────────

    def _emit_update(self) -> None:
        self._fight_elapsed += self._interval // 1000
        self._tick_timers()
        self._add_log_line()
        self.data_updated.emit(self._build_snapshot())

    def _build_snapshot(self) -> MockSnapshot:
        dps_entries = self._build_dps()
        healer_entries = self._build_healers()
        return MockSnapshot(
            dps_entries=dps_entries,
            healer_entries=healer_entries,
            combat_log=list(self._log_lines[-12:]),
            raid_timers=list(self._timers),
            fight_duration=self._fight_elapsed,
        )

    def _build_dps(self) -> list[CombatantEntry]:
        entries: list[CombatantEntry] = []
        for name, cls, base_dps in _DPS_ROSTER:
            variation = random.uniform(0.88, 1.12)
            dps = int(base_dps * variation)
            entries.append(
                CombatantEntry(
                    name=name,
                    dps=dps,
                    total_damage=dps * self._fight_elapsed,
                    percent=0.0,
                    class_abbr=cls,
                )
            )
        if entries:
            top = max(e.dps for e in entries) or 1
            for e in entries:
                e.percent = e.dps / top
        entries.sort(key=lambda x: x.dps, reverse=True)
        return entries

    def _build_healers(self) -> list[HealerEntry]:
        entries: list[HealerEntry] = []
        for name, cls, base_hps in _HEALER_ROSTER:
            variation = random.uniform(0.88, 1.12)
            hps = int(base_hps * variation)
            entries.append(
                HealerEntry(
                    name=name,
                    hps=hps,
                    total_heals=hps * self._fight_elapsed,
                    percent=0.0,
                    class_abbr=cls,
                )
            )
        if entries:
            top = max(e.hps for e in entries) or 1
            for e in entries:
                e.percent = e.hps / top
        entries.sort(key=lambda x: x.hps, reverse=True)
        return entries

    def _add_log_line(self) -> None:
        template, color = random.choice(_LOG_TEMPLATES)
        text = template.format(
            attacker=random.choice(_NAMES),
            target=random.choice(_NAMES),
            healer=random.choice(_NAMES[:3]),
            mob=random.choice(_MOBS),
            dmg=f"{random.randint(500, 12000):,}",
            heal=f"{random.randint(800, 6000):,}",
        )
        self._log_lines.append(CombatLogLine(text=text, color_key=color))
        if len(self._log_lines) > 50:
            self._log_lines.pop(0)

    def _tick_timers(self) -> None:
        for t in self._timers:
            t.seconds_remaining = max(0, t.seconds_remaining - (self._interval // 1000))
            if t.seconds_remaining == 0:
                t.seconds_remaining = t.max_seconds  # auto-reset for demo
            ratio = t.seconds_remaining / t.max_seconds
            if ratio < 0.15:
                t.color_key = "danger"
            elif ratio < 0.35:
                t.color_key = "warning"
            else:
                t.color_key = "normal"

