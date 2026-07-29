# Agent tooling instructions

Scripts must be deterministic, non-interactive by default, stdlib-only where practical, and safe to run repeatedly. They may not read secrets into generated context packs. Add parsing/scope tests under `tests/tools/`.
