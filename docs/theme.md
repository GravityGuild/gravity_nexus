# Theme System

`ThemeManager` (singleton, `app/theme/theme_manager.py`) generates and applies QSS from `ColorRole` / `FontRole` enums defined in `app/theme/spec.py`.

All colour constants are in `app/theme/colors.py` — never hardcode colour values in widgets. Reference them via `ColorRole` or the named constants when building QSS in `app/theme/qss_builder.py`.
