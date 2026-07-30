# H04 — HIL evidence hardening

## Status

**MERGED — complete at `1f127ef8b5fcf04762a0cc4dd15f8313df23839e`.**

## Outcome

Harden the single `tests/hil/` runner so scarce borrowed or streamed device sessions produce exact, reviewable gate evidence without adding a second physical-test implementation.

## Acceptance result

- SSH known-host state is isolated per run.
- Headscale assertions use exact structured identity matching with an allowed FQDN suffix.
- Controller-silent smoke and actual controller/network-unavailable evidence are distinct; only the latter may support B17.
- Remote ADB command prefixes are supported while preserving exact serial selection and exit 77 behavior.
- Interrupted runs retain bounded redacted diagnostics but cannot emit PASS.
- Reviewed HIL output can be validated and promoted through existing evidence tooling.

## Handoff

H04 is historical. `tests/hil/` remains the sole physical runner. Any further HIL behavior change requires a new scoped task with gate-specific acceptance criteria; do not reopen or extend H04 silently.
