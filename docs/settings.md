# Settings

`SettingsService` (`app/services/settings_service.py`) wraps `QSettings("GravityNexus", "GravityNexus")` (Windows registry).

The in-memory model is `AppSettings` (`app/models/settings_model.py`) — a tree of typed dataclasses with safe defaults. Always call `settings_svc.save()` after mutating the model.
