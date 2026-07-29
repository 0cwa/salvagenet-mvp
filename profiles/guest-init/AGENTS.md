# Guest-init instructions

Scripts are trusted profile code, must be idempotent, and must never contain reusable keys. Fetch one-time secrets from the host metadata endpoint, erase them after use, disable password SSH, and emit bounded machine-readable readiness/qualification results.
