"""PositioningOverlayManager — owns overlay-positioning mode lifecycle."""
from __future__ import annotations

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

from feature_flags import feature_enabled
from services.protocols import ISettingsService
from ui.overlays.overlay_config import OVERLAY_CONFIGS, OverlayConfig, resolve_default_position
from ui.overlays.positioning_overlay import PositioningOverlay


class PositioningOverlayManager:
    """Manages the drag-to-reposition mode for all registered overlays.

    Owns the list of live PositioningOverlay placeholders and the position
    snapshot used to implement Cancel.  MainWindow wires signals and calls
    ``set_toolbar_overlay`` once the toolbar window exists.
    """

    def __init__(
        self,
        svc: ISettingsService,
        overlay_configs: list[OverlayConfig] = None,
    ) -> None:
        self._svc = svc
        self._overlay_configs = overlay_configs or OVERLAY_CONFIGS
        self._positioning_overlays: list[PositioningOverlay] = []
        self._position_snapshot: dict[str, tuple[int, int, int, int]] = {}
        self._toolbar_overlay = None  # set via set_toolbar_overlay after creation
        self._all_closed_callback = None  # called when all placeholders are dismissed

    def set_toolbar_overlay(self, overlay) -> None:  # QuickToolbarOverlay | None
        self._toolbar_overlay = overlay

    def set_all_closed_callback(self, callback) -> None:
        self._all_closed_callback = callback

    @property
    def active_overlays(self) -> list[PositioningOverlay]:
        return self._positioning_overlays

    # ── Public slot targets ────────────────────────────────────────────────────

    def on_requested(self, active: bool) -> None:
        if active:
            self._show_positioning_overlays()
        else:
            self.save_and_close()

    def save_and_close(self) -> None:
        """Persist current geometry for all placeholders and close them."""
        for w in self._positioning_overlays:
            try:
                p = w.pos()
                sz = w.size()
                self._svc.settings.overlay.positions[w.overlay_key] = (
                    p.x(), p.y(), sz.width(), sz.height()
                )
                w.close()
            except RuntimeError:
                pass
        self._positioning_overlays.clear()
        self._position_snapshot.clear()
        self._svc.save()
        self._restore_toolbar_position()

    def cancel(self) -> None:
        """Close placeholders and restore positions only for overlays still showing."""
        for w in self._positioning_overlays:
            key = w.overlay_key
            try:
                w.close()
            except RuntimeError:
                pass
            if key in self._position_snapshot:
                self._svc.settings.overlay.positions[key] = self._position_snapshot[key]
            else:
                self._svc.settings.overlay.positions.pop(key, None)
        self._positioning_overlays.clear()
        self._position_snapshot.clear()
        self._svc.save()
        self._restore_toolbar_position()

    # ── Per-overlay save / cancel ──────────────────────────────────────────────

    def _on_overlay_individually_saved(self, key: str) -> None:
        overlay = next((w for w in self._positioning_overlays if w.overlay_key == key), None)
        if overlay is None:
            return
        try:
            p = overlay.pos()
            sz = overlay.size()
            self._svc.settings.overlay.positions[key] = (p.x(), p.y(), sz.width(), sz.height())
            overlay.close()
        except RuntimeError:
            pass
        self._positioning_overlays = [w for w in self._positioning_overlays if w.overlay_key != key]
        self._check_all_dismissed()

    def _on_overlay_individually_cancelled(self, key: str) -> None:
        overlay = next((w for w in self._positioning_overlays if w.overlay_key == key), None)
        if overlay is None:
            return
        if key in self._position_snapshot:
            self._svc.settings.overlay.positions[key] = self._position_snapshot[key]
        else:
            self._svc.settings.overlay.positions.pop(key, None)
        try:
            overlay.close()
        except RuntimeError:
            pass
        self._positioning_overlays = [w for w in self._positioning_overlays if w.overlay_key != key]
        self._check_all_dismissed()

    def _check_all_dismissed(self) -> None:
        if self._positioning_overlays:
            return
        self._position_snapshot.clear()
        self._svc.save()
        self._restore_toolbar_position()
        if self._all_closed_callback is not None:
            self._all_closed_callback()

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _show_positioning_overlays(self) -> None:
        self.save_and_close()  # clear any leftovers

        if self._toolbar_overlay is not None:
            try:
                self._toolbar_overlay.hide()
            except RuntimeError:
                pass

        self._position_snapshot = dict(self._svc.settings.overlay.positions)

        screen = QApplication.primaryScreen().geometry()
        for cfg in self._overlay_configs:
            if cfg.feature_flag and not feature_enabled(cfg.feature_flag, self._svc.settings):
                continue
            min_size = None
            if cfg.min_width is not None or cfg.min_height is not None:
                min_size = (
                    cfg.min_width if cfg.min_width is not None else cfg.default_size[0],
                    cfg.min_height if cfg.min_height is not None else cfg.default_size[1],
                )
            w = PositioningOverlay(
                cfg.key,
                cfg.label,
                cfg.default_size,
                show_body=cfg.show_body,
                min_size=min_size,
            )
            # Apply opacity/scale FIRST so _base_size is captured from the natural
            # default size.  The saved size is then applied as a hard override
            # afterwards, preventing compounding growth on each save/restore cycle.
            w.set_overlay_opacity(self._svc.settings.overlay.opacity)
            w.set_overlay_scale(self._svc.settings.overlay.scale)
            saved = self._svc.settings.overlay.positions.get(cfg.key)
            if saved:
                x, y, sw, sh = saved
                if sw > 0 and sh > 0:
                    w.resize(sw, sh)
                w.move(x, y)
            else:
                x, y = resolve_default_position(cfg, w.width(), w.height(), screen)
                w.move(x, y)
            w.saved.connect(self._on_overlay_individually_saved)
            w.cancelled.connect(self._on_overlay_individually_cancelled)
            w.show()
            self._positioning_overlays.append(w)

    def _restore_toolbar_position(self) -> None:
        if self._toolbar_overlay is None:
            return
        try:
            saved = self._svc.settings.overlay.positions.get("toolbar")
            if saved:
                self._toolbar_overlay.move(saved[0], saved[1])
            self._toolbar_overlay.show()
        except RuntimeError:
            pass

    @staticmethod
    def clamp_to_screen(x: int, y: int, w: int, h: int) -> tuple[int, int]:
        """Return (x, y) clamped so a w×h overlay stays on a visible screen."""
        screen = QApplication.screenAt(QPoint(x + w // 2, y + h // 2))
        if screen is None:
            screen = QApplication.primaryScreen()
        avail = screen.availableGeometry()
        x = max(avail.left(), min(x, avail.right() - max(w, 50)))
        y = max(avail.top(), min(y, avail.bottom() - max(h, 50)))
        return x, y
