# Feature Flags

`app/feature_flags.py` holds `FEATURE_REGISTRY` — the single source of truth for all in-development features.

To add a flag:
1. Append a `FeatureFlag(key, label, description, default)` to `FEATURE_REGISTRY`.
2. Check it anywhere with `feature_enabled("flag_key", settings)`.

Flags auto-appear in the Feature Flags dev page with no extra wiring.
