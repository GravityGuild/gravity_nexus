"""QuickToolbarOverlay — customizable always-on-top quick-action toolbar.

Collapsed
---------
Shrinks to a single  ◈  icon button (≈ 40 × 40 px) that can be clicked to
expand again.  Position is locked by default; use the "Position Overlays"
button in the Overlays settings page to reposition it.

Expanded
--------
Shows a thin control strip (collapse chevron + gear) plus a row or column of
quick-action buttons whose visibility is configurable via the ⚙ dialog.

Orientation ("horizontal" | "vertical") and collapsed state are persisted in
``AppSettings.toolbar`` and can be changed live via the ⚙ config dialog.

Architecture
------------
Subclasses ``BaseOverlayWindow`` and overrides:
  * ``_build_ui``          — installs icon badge + expanded frame (no drag area).
  * ``_build_corner_grips`` — no-op; position/size is controlled externally.
"""
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from theme.colors import ACCENT_CYAN_RGB
from ui.overlays.base_overlay_window import BaseOverlayWindow
from ui.widgets import icon_pixmap, AppIcon
from ui.widgets.themed_button import ThemedButton

log = logging.getLogger(__name__)

# ── Layout constants ───────────────────────────────────────────────────────────
_BTN_H             = 32   # button height
_BTN_W             = 90   # button width in horizontal mode
_BAR_H             = _BTN_H + 12 + 40   # 44 px — consistent toolbar height (incl. 6 px shadow margins top+bottom)
_COLLAPSED_ICON_SZ = _BTN_H - 2    # 30 px — icon inside the collapsed badge button
_GAP               = 6    # spacing between buttons

# ── Available quick-action registry ───────────────────────────────────────────
# key → (display_label, tooltip)
_AVAILABLE_ACTIONS: dict[str, tuple[str, str]] = {
    "placeholder": ("Placeholder", "Placeholder quick-action button"),
}

_DEFAULT_BUTTONS: list[str] = ["placeholder"]


# ── Config dialog ──────────────────────────────────────────────────────────────

class ToolbarConfigDialog(QDialog):
    """Small dialog for configuring orientation and visible buttons.

    Signals
    -------
    orientation_changed(str):
        Emitted immediately on every combo change for live toolbar reflow.
    """

    orientation_changed = Signal(str)

    def __init__(
        self,
        current_orientation: str,
        enabled_keys: list[str],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowTitle("Configure Quick Toolbar")
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint
        )
        self._original_orientation = current_orientation
        self._current_orientation = current_orientation
        self._checkboxes: dict[str, QCheckBox] = {}
        self._build_ui(current_orientation, enabled_keys)

    def _build_ui(self, orientation: str, enabled_keys: list[str]) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        form = QFormLayout()
        form.setHorizontalSpacing(12)
        self._orientation_combo = QComboBox()
        self._orientation_combo.addItem("Horizontal", "horizontal")
        self._orientation_combo.addItem("Vertical", "vertical")
        self._orientation_combo.setCurrentIndex(0 if orientation == "horizontal" else 1)
        self._orientation_combo.currentIndexChanged.connect(self._on_orientation_changed)
        form.addRow("Orientation:", self._orientation_combo)
        root.addLayout(form)

        root.addWidget(QLabel("Available Buttons:"))
        for key, (label, tooltip) in _AVAILABLE_ACTIONS.items():
            cb = QCheckBox(label)
            cb.setToolTip(tooltip)
            cb.setChecked(key in enabled_keys)
            self._checkboxes[key] = cb
            root.addWidget(cb)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self._on_cancel)
        root.addWidget(btns)

        self.setMinimumWidth(270)

    def _on_orientation_changed(self, _idx: int) -> None:
        self._current_orientation = self._orientation_combo.currentData()
        self.orientation_changed.emit(self._current_orientation)

    def _on_cancel(self) -> None:
        """Revert any live orientation preview before rejecting."""
        if self._current_orientation != self._original_orientation:
            self.orientation_changed.emit(self._original_orientation)
        self.reject()

    @property
    def selected_orientation(self) -> str:
        return self._orientation_combo.currentData()

    @property
    def enabled_button_keys(self) -> list[str]:
        return [k for k, cb in self._checkboxes.items() if cb.isChecked()]


# ── Main overlay ───────────────────────────────────────────────────────────────

class QuickToolbarOverlay(BaseOverlayWindow):
    """Frameless always-on-top quick-action toolbar.

    Collapsed: single ◈ icon — click to expand.
    Expanded:  thin control strip (▾ collapse / ⚙ gear) + button row or column.

    Position is locked by default.  Move it via the "Position Overlays" button
    in the Overlays settings page.

    """

    # ── Init ──────────────────────────────────────────────────────────────────

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        # Load persisted values BEFORE super().__init__ because that call
        # invokes self._build_ui(), which reads these attributes.
        self._orientation: str = "horizontal"
        self._collapsed: bool = False
        self._button_keys: list[str] = list(_DEFAULT_BUTTONS)

        try:
            from core.registry import registry
            from services.protocols import ISettingsService

            ts = registry.get(ISettingsService).settings.toolbar
            self._orientation = ts.orientation
            self._collapsed = ts.collapsed
            self._button_keys = (
                list(ts.button_keys) if ts.button_keys else list(_DEFAULT_BUTTONS)
            )
        except Exception:
            log.debug(
                "QuickToolbarOverlay: could not read toolbar settings — using defaults"
            )

        # Icons for the toggle button (small, in-toolbar) and collapsed button (large).
        # Must be set before super().__init__ which invokes _build_ui → _populate_button_body.
        self._horizontal_open_icon = QIcon(icon_pixmap(AppIcon.CHEVRON_RIGHT_BOX_OUTLINE, size=ThemedButton.ICON_SIZE))
        self._horizontal_close_icon = QIcon(icon_pixmap(AppIcon.CHEVRON_LEFT_BOX_OUTLINE,  size=ThemedButton.ICON_SIZE))
        self._vertical_open_icon = QIcon(icon_pixmap(AppIcon.CHEVRON_DOWN_BOX_OUTLINE,  size=ThemedButton.ICON_SIZE))
        self._vertical_close_icon = QIcon(icon_pixmap(AppIcon.CHEVRON_UP_BOX_OUTLINE,    size=ThemedButton.ICON_SIZE))

        # Larger variants rendered at _COLLAPSED_ICON_SZ for the collapsed badge button.
        self._collapsed_h_icon = QIcon(icon_pixmap(AppIcon.CHEVRON_RIGHT_BOX_OUTLINE, size=_COLLAPSED_ICON_SZ))
        self._collapsed_v_icon = QIcon(icon_pixmap(AppIcon.CHEVRON_DOWN_BOX_OUTLINE,  size=_COLLAPSED_ICON_SZ))

        self._toggle_btn: Optional[QToolButton] = None

        super().__init__("Quick Toolbar", parent)
        self._apply_collapsed_state()

    # ── Override base class hooks ─────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Install collapsed icon + expanded frame (no drag, no title)."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(0)

        # ── Collapsed badge ─────────────────────────────────────────────────
        self._icon_btn = QToolButton()
        self._icon_btn.setToolTip("Quick Toolbar — click to expand")
        self._icon_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._icon_btn.clicked.connect(self.toggle_collapsed)
        outer.addWidget(self._icon_btn)

        # ── Expanded frame ──────────────────────────────────────────────────
        self._frame = QWidget()
        self._frame.setObjectName("BaseOverlay")
        frame_layout = QVBoxLayout(self._frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        # Content wrapper (base class expects content_layout to exist)
        self._content_widget = QWidget()
        self.content_layout = QVBoxLayout(self._content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # Button body — rebuilt on orientation change
        self._button_body = QWidget()
        self._populate_button_body()
        self.content_layout.addWidget(self._button_body)

        frame_layout.addWidget(self._content_widget)
        outer.addWidget(self._frame)

    def _build_corner_grips(self) -> None:
        """No-op — position and size are locked; no resize grips needed."""

    # ── Button body ───────────────────────────────────────────────────────────

    def _populate_button_body(self) -> None:
        """Populate *self._button_body* with buttons for the current orientation."""
        if self._orientation == "horizontal":
            body_layout = QHBoxLayout(self._button_body)
        else:
            body_layout = QVBoxLayout(self._button_body)

        body_layout.setContentsMargins(6, 6, 6, 6)
        body_layout.setSpacing(_GAP)
        body_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # ── Toggle (collapse/expand) button — always first ─────────────────
        self._toggle_btn = ThemedButton()
        self._toggle_btn.setFixedSize(_BAR_H, _BAR_H)
        self._toggle_btn.setIconSize(QSize(_BAR_H, _BAR_H))
        self._toggle_btn.clicked.connect(self.toggle_collapsed)
        self._update_toggle_icon()
        body_layout.addWidget(self._toggle_btn)

        # ── Action buttons ─────────────────────────────────────────────────
        for key in self._button_keys:
            info = _AVAILABLE_ACTIONS.get(key)
            if info is None:
                continue
            label, tooltip = info
            btn = ThemedButton(label)
            btn.setToolTip(tooltip)
            if self._orientation == "horizontal":
                btn.setFixedHeight(_BAR_H)
            else:
                btn.setFixedHeight(_BTN_H)
                btn.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
                )
            body_layout.addWidget(btn)

        if self._orientation == "horizontal":
            body_layout.addStretch()

    def _rebuild_button_body(self) -> None:
        """Destroy and recreate the button body for the current orientation."""
        self.content_layout.removeWidget(self._button_body)
        self._button_body.deleteLater()
        self._button_body = QWidget()
        self._populate_button_body()
        self.content_layout.addWidget(self._button_body)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_orientation(self, orientation: str) -> None:
        """Switch orientation and immediately reflow the button body."""
        if orientation not in ("horizontal", "vertical"):
            log.warning("QuickToolbarOverlay: invalid orientation %r", orientation)
            return
        if orientation == self._orientation:
            return
        self._orientation = orientation
        self._rebuild_button_body()
        if not self._collapsed:
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16_777_215, 16_777_215)

            self.setFixedHeight(_BAR_H)
            if orientation == "horizontal":
                self.setFixedHeight(_BAR_H)

            self.adjustSize()
        self._save_settings()
        log.debug("QuickToolbarOverlay: orientation → %s", orientation)

    def toggle_collapsed(self) -> None:
        """Toggle between the collapsed icon and the expanded toolbar."""
        self._collapsed = not self._collapsed
        self._apply_collapsed_state()
        self._save_settings()

    def update_button_keys(self, keys: list[str]) -> None:
        """Replace the set of visible buttons and rebuild the body."""
        self._button_keys = list(keys)
        self._rebuild_button_body()
        if not self._collapsed:
            self.adjustSize()
        self._save_settings()

    # ── Collapsed state ───────────────────────────────────────────────────────

    @staticmethod
    def _accent_btn_style(radius: int = 8) -> str:
        """Return a QSS snippet that gives a button the cyan accent look.

        The explicit background also prevents WA_TranslucentBackground
        click-through on Windows.
        """
        r, g, b = ACCENT_CYAN_RGB
        return f"""
            QToolButton {{
                background-color: rgba({r}, {g}, {b}, 35);
                border: 1px solid rgba({r}, {g}, {b}, 110);
                border-radius: {radius}px;
            }}
            QToolButton:hover {{
                background-color: rgba({r}, {g}, {b}, 60);
                border-color: rgba({r}, {g}, {b}, 180);
            }}
            QToolButton:pressed {{
                background-color: rgba({r}, {g}, {b}, 85);
            }}
        """

    def _apply_collapsed_state(self) -> None:
        """Sync widget visibility and window size with *self._collapsed*."""
        if self._collapsed:
            icon = self._collapsed_h_icon if self._orientation == "horizontal" else self._collapsed_v_icon
            self._icon_btn.setIcon(icon)
            self._icon_btn.setIconSize(QSize(_COLLAPSED_ICON_SZ, _COLLAPSED_ICON_SZ))
            self._icon_btn.setStyleSheet(self._accent_btn_style(radius=8))
            self._frame.hide()
            self._icon_btn.show()
            # Zero outer margins so the button occupies the full window area.
            self.layout().setContentsMargins(0, 0, 0, 0)
            self._icon_btn.setFixedSize(_BAR_H, _BAR_H)
            self.setFixedSize(_BAR_H, _BAR_H)
        else:
            self._icon_btn.setStyleSheet("")
            self._icon_btn.setFixedSize(0, 0)
            self._icon_btn.hide()
            self._frame.show()
            # Restore shadow margins.
            self.layout().setContentsMargins(6, 6, 6, 6)
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16_777_215, 16_777_215)
            # Lock height to _BAR_H only in horizontal mode; vertical mode grows with buttons.
            if self._orientation == "horizontal":
                self.adjustSize()
                self.setFixedHeight(_BAR_H)
            else:
                self.adjustSize()

        self._update_toggle_icon()

    def _update_toggle_icon(self) -> None:
        """Update the toggle button icon to reflect the current orientation and state."""
        if self._toggle_btn is None:
            return
        if self._orientation == "horizontal":
            icon = self._horizontal_open_icon if self._collapsed else self._horizontal_close_icon
        else:
            icon = self._vertical_open_icon if self._collapsed else self._vertical_close_icon
        self._toggle_btn.setIcon(icon)
        self._toggle_btn.setToolTip("Expand toolbar" if self._collapsed else "Collapse toolbar")

    # ── Config dialog ─────────────────────────────────────────────────────────

    def _open_config_dialog(self) -> None:
        dlg = ToolbarConfigDialog(
            current_orientation=self._orientation,
            enabled_keys=self._button_keys,
            parent=self,
        )
        dlg.orientation_changed.connect(self._on_live_orientation_change)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            final_orientation = dlg.selected_orientation
            if final_orientation != self._orientation:
                self.set_orientation(final_orientation)

            final_keys = dlg.enabled_button_keys
            if final_keys != self._button_keys:
                self.update_button_keys(final_keys)

    def _on_live_orientation_change(self, orientation: str) -> None:
        """Apply orientation live (preview from config dialog — not yet saved)."""
        if orientation == self._orientation:
            return
        self._orientation = orientation
        self._rebuild_button_body()
        if not self._collapsed:
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16_777_215, 16_777_215)
            self.adjustSize()
            if orientation == "horizontal":
                self.setFixedHeight(_BAR_H)

    # ── Settings ──────────────────────────────────────────────────────────────

    def _save_settings(self) -> None:
        try:
            from core.registry import registry
            from services.protocols import ISettingsService

            svc = registry.get(ISettingsService)
            ts = svc.settings.toolbar
            ts.orientation = self._orientation
            ts.collapsed = self._collapsed
            ts.button_keys = list(self._button_keys)
            svc.save()
        except Exception:
            log.debug("QuickToolbarOverlay: could not save toolbar settings")

    # ── Events ────────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:  # noqa: ANN001
        self._save_settings()
        super().closeEvent(event)

