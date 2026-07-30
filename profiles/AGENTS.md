# VM profile instructions

- Profiles describe virtual hardware, boot, initialization, artifacts, and qualification—not workloads.
- JSON is the canonical production format and must validate against `profiles/schema/vm-profile.schema.json`.
- The Android runtime packages and parses the validated JSON; do not preserve or recreate a second complete Kotlin definition.
- Unknown fields, unsupported versions, unresolved inheritance, missing trusted bootstrap assets, invalid artifact references, and traversal-capable guest-init paths fail before runtime/filesystem effects.
- Every non-Podroid artifact requires an active manifest. Only the three pinned Podroid qualification assets use bare files plus `.sha256`.
- No raw host QEMU or kernel argv.
- Remote artifacts are referenced through the lock file; mutable URLs are pinning inputs only.
- Bootstrap scripts are trusted project code, tightly scoped, packaged with the referencing profile, and idempotent.
- H02A qualifies Ubuntu boot/NoCloud/SSH independently of guest mesh. Do not add Headscale/Tailscale behavior to H02A profile assets.
- K3s-lab only qualifies prerequisites; it does not install or join a cluster in the base MVP.
- A profile test must distinguish schema validity, resolver semantics, package presence, host-QEMU evidence, and physical runtime evidence.
