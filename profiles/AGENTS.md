# VM profile instructions

- Profiles describe virtual hardware, boot, initialization, artifacts, and qualification—not workloads.
- JSON is the canonical format and must validate against `schema/vm-profile.schema.json`.
- During F01, make the validated packaged JSON the Android production source; do not preserve a second complete Kotlin definition as a fallback.
- Unknown fields, unsupported versions, unresolved inheritance, missing trusted bootstrap assets, and invalid artifact references fail before runtime/filesystem effects.
- No raw host QEMU or kernel argv.
- Remote artifacts are referenced through the lock file; mutable URLs are pinning inputs only.
- Bootstrap scripts are trusted project code, tightly scoped, packaged with the referencing profile, and idempotent.
- K3s-lab only qualifies prerequisites; it does not install or join a cluster in the base MVP.
- A profile test must distinguish schema validity, resolver semantics, package presence, and physical runtime evidence.
