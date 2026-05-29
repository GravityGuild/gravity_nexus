"""PopupSearchBar — frameless popup input with optional autocomplete list."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.search_box import SearchBox


class _SuggestionList(QListWidget):
    """Internal autocomplete list — click emits item_submitted."""

    item_submitted = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("PopupSuggestionList")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.itemClicked.connect(self._on_click)

    def _on_click(self, item: QListWidgetItem) -> None:
        self.item_submitted.emit(item.text())


DEFAULT_SEARCH_BAR_WIDTH = 500


class PopupSearchBar(QWidget):
    """Frameless popup search bar with optional autocomplete.

    Usage::

        bar = PopupSearchBar(placeholder="Find character…")
        bar.text_changed.connect(lambda t: bar.set_suggestions(my_lookup(t)))
        bar.submitted.connect(handle_result)
        bar.show_at(QPoint(x, y))

    Signals
    -------
    submitted(str):
        User confirmed a value — Enter/Return, Tab on a single match, or clicking
        a suggestion row.
    text_changed(str):
        Every keystroke in the input. Connect to a slot that calls
        ``set_suggestions()`` to drive live autocomplete.
    closed():
        Emitted after the popup hides (Escape, outside-click, or post-submit).
    """

    submitted = Signal(str)
    text_changed = Signal(str)
    closed = Signal()

    def __init__(
        self,
        placeholder: str = "Search…",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setObjectName("PopupSearchBar")

        self._placeholder = placeholder
        self._anchor_pos: QPoint = QPoint(0, 0)
        self._list_above: bool = False
        self._has_suggestions: bool = False

        self._build_ui()
        self._connect_signals()

    # ── Public API ─────────────────────────────────────────────────────────────

    def show_at(self, global_pos: QPoint, width: int = DEFAULT_SEARCH_BAR_WIDTH) -> None:
        """Position and show the popup with the input anchored at global_pos.

        Parameters
        ----------
        global_pos:
            Desired top-left corner of the popup in global screen coordinates.
        width:
            Pixel width of the popup.
        """
        self._anchor_pos = global_pos
        self.setFixedWidth(width)
        self._search_box.clear()
        self.set_suggestions([])
        self._reposition()
        self.show()
        self._search_box._edit.setFocus(Qt.FocusReason.OtherFocusReason)

    def show_saved(self, width: int = DEFAULT_SEARCH_BAR_WIDTH) -> None:
        """Show at the position saved via the overlay positioning system.

        Reads ``overlay.positions["search_bar"]`` from ``ISettingsService``.
        Falls back to centering on the primary screen if no position has been
        saved yet.
        """
        from core.registry import registry          # noqa: PLC0415
        from services.protocols import ISettingsService  # noqa: PLC0415
        svc = registry.get(ISettingsService)
        saved = svc.settings.overlay.positions.get("search_bar")
        if saved:
            pos = QPoint(saved[0], saved[1])
            if saved[2] > 0:
                width = saved[2]
        else:
            from ui.overlays.overlay_config import OVERLAY_CONFIG_MAP, resolve_default_position  # noqa: PLC0415
            geom = QApplication.primaryScreen().availableGeometry()
            cfg = OVERLAY_CONFIG_MAP["search_bar"]
            px, py = resolve_default_position(cfg, width, self.sizeHint().height(), geom)
            pos = QPoint(px, py)
        self.show_at(pos, width=width)

    def set_suggestions(self, suggestions: list[str]) -> None:
        """Replace the autocomplete suggestion list. Pass [] to hide it."""
        self._list.clear()
        for text in suggestions:
            self._list.addItem(text)
        self._list.clearSelection()
        self._has_suggestions = bool(suggestions)

        if suggestions:
            self._list.setVisible(True)
            row_h = self._list.sizeHintForRow(0)
            if row_h < 1:
                row_h = 34
            n = min(len(suggestions), 8)
            self._list.setFixedHeight(row_h * n + 10)
        else:
            self._list.setVisible(False)

        self._reposition()

    def clear(self) -> None:
        """Clear the input and hide suggestions."""
        self._search_box.clear()
        self.set_suggestions([])

    def text(self) -> str:
        return self._search_box.text()

    # ── Private — UI construction ──────────────────────────────────────────────

    def _build_ui(self) -> None:
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self._layout.setSpacing(6)

        self._search_box = SearchBox(self._placeholder)
        self._list = _SuggestionList()
        self._list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._list.hide()

        self._layout.addWidget(self._search_box)
        self._layout.addWidget(self._list)

    def _connect_signals(self) -> None:
        self._search_box.text_changed.connect(self.text_changed)
        self._search_box.search_submitted.connect(self._on_submit)
        self._list.item_submitted.connect(self._on_submit)
        self._search_box._edit.installEventFilter(self)

    # ── Private — positioning ──────────────────────────────────────────────────

    def _reposition(self) -> None:
        screen = QApplication.screenAt(self._anchor_pos) or QApplication.primaryScreen()
        if screen is None:
            return
        avail = screen.availableGeometry()
        screen_mid_y = avail.center().y()

        new_above = self._anchor_pos.y() > screen_mid_y
        if new_above != self._list_above:
            self._list_above = new_above
            self._set_layout_order(list_on_top=self._list_above)

        self.adjustSize()

        list_h = self._list.height() if self._has_suggestions else 0
        spacing = self._layout.spacing() if list_h > 0 else 0

        win_y = (
            self._anchor_pos.y() - list_h - spacing
            if self._list_above
            else self._anchor_pos.y()
        )

        win_x = min(self._anchor_pos.x(), avail.right() - self.width())
        win_x = max(win_x, avail.left())
        win_y = max(win_y, avail.top())

        self.move(win_x, win_y)

    def _set_layout_order(self, list_on_top: bool) -> None:
        self._layout.removeWidget(self._list)
        self._layout.removeWidget(self._search_box)
        if list_on_top:
            self._layout.addWidget(self._list)
            self._layout.addWidget(self._search_box)
        else:
            self._layout.addWidget(self._search_box)
            self._layout.addWidget(self._list)

    # ── Private — submission ───────────────────────────────────────────────────

    def _on_submit(self, text: str) -> None:
        if text:
            self.submitted.emit(text)
        self.hide()

    # ── Event filter — keyboard navigation ────────────────────────────────────

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: ANN001
        if (
            obj is self._search_box._edit
            and isinstance(event, QKeyEvent)
            and event.type() == QEvent.Type.KeyPress
        ):
            key = event.key()

            if key == Qt.Key.Key_Escape:
                self.hide()
                return True

            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                current = self._list.currentItem()
                if current and self._has_suggestions:
                    self._on_submit(current.text())
                else:
                    self._on_submit(self._search_box.text())
                return True

            if key == Qt.Key.Key_Tab:
                if self._list.count() == 1:
                    only = self._list.item(0)
                    if only:
                        self._search_box.set_text(only.text())
                return True

            if key == Qt.Key.Key_Down and self._has_suggestions:
                count = self._list.count()
                if count:
                    row = self._list.currentRow()
                    next_row = 0 if row == count - 1 else max(0, row + 1)
                    self._list.setCurrentRow(next_row)
                return True

            if key == Qt.Key.Key_Up and self._has_suggestions:
                count = self._list.count()
                if count:
                    row = self._list.currentRow()
                    prev_row = count - 1 if row <= 0 else row - 1
                    self._list.setCurrentRow(prev_row)
                return True

        return super().eventFilter(obj, event)

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def hideEvent(self, event) -> None:  # noqa: ANN001
        self.closed.emit()
        super().hideEvent(event)

    # ── Painting ───────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:  # noqa: ANN001
        from theme.colors import NAVY_BG_RGB, ACCENT_CYAN_RGB  # noqa: PLC0415
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(*NAVY_BG_RGB, 242))
        p.setPen(QColor(*ACCENT_CYAN_RGB, 80))
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 10, 10)
        p.end()
