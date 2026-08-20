# VM profile instructions

- Profiles describe virtual hardware, boot, initialization, artifacts, and qualification—not workloads.
- JSON and the generated packaged index are the canonical production profile registry and must validate against `profiles/schema/vm-profile.schema.json`.
- The Android runtime verifies index, schema, profile, and vendor-data digests before parsing; do not preserve or recreate a second complete Kotlin definition.
- Unknown fields, unsupported versions, unavailable `derivedFrom` references, inconsistent packaged digests, missing trusted bootstrap assets, invalid artifact references, and traversal-capable guest-init paths fail before runtime/filesystem effects.
- `derivedFrom` records provenance only; it does not perform runtime inheritance or merging.
- Every non-Podroid artifact requires an active manifest. Only the three pinned Podroid qualification assets use the narrowly scoped packaged bare-file plus `.sha256` adapter.
- No raw host QEMU or kernel argv.
- Remote artifacts are referenced through the lock file; mutable URLs are pinning inputs only.
- Bootstrap scripts are trusted project code, tightly scoped, packaged with the referencing profile, and idempotent.
- H02A qualifies Ubuntu boot/NoCloud/SSH independently of guest mesh. Do not add Headscale/Tailscale behavior to H02A profile assets.
- K3s-lab only qualifies prerequisites; it does not install or join a cluster in the base MVP.
- A profile test must distinguish schema validity, resolver semantics, package presence, host-QEMU evidence, and physical runtime evidence.
