# Development-tool instructions

- Tools here orchestrate existing checks; they do not redefine acceptance gates.
- Missing optional environments produce explicit `SKIP`, never a synthetic pass.
- Reports must be deterministic apart from timestamps/durations and stay under ignored `.local/` paths.
- Do not embed secrets, live enrollment material, ADB serials, or unredacted command output.
- Keep the runner standard-library-only so it works before the Python environment is provisioned.
