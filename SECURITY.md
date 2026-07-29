# Security policy

The MVP is a research-grade node host, not a production security boundary.

Report security issues privately to the project owner. Do not publish live enrollment tokens, Headscale API keys, SSH private keys, Android signing keys, VM disks, controller bearer capabilities, or diagnostic bundles containing personal data.

Base security invariants:

- no default password;
- no arbitrary shell endpoint in the Android host API;
- no raw remote QMP endpoint;
- no Headscale administrative API key on a phone or guest;
- host and guest mesh identities are separate;
- recovery access remains host-mediated;
- imported secrets are never committed;
- debug-only bypasses are excluded from release variants.

See `docs/architecture/security-boundaries.md` and `docs/testing/security-checks.md`.
