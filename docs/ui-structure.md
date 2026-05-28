# UI Structure

`MainWindow` (`app/ui/main_window.py`) — frameless `QWidget` containing:
- `TitleBar` — draggable, custom window controls
- `Sidebar` — animated navigation
- `QStackedWidget` — lazy-loaded pages (declared as `PageConfig` dataclasses: label, icon, factory)
- `StatusBar` — bottom status strip

## Overlays

Overlays (`app/ui/overlays/`) extend `BaseOverlayWindow` — frameless, translucent, always-on-top. Click-through uses `WS_EX_TRANSPARENT` via ctypes (Windows only). Subclasses add content to `self.content_layout`.
