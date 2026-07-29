# VM profile instructions

- Profiles describe virtual hardware, boot, initialization, artifacts, and qualification—not workloads.
- JSON is canonical and must validate against `schema/vm-profile.schema.json`.
- No raw host QEMU/kernel argv.
- Remote artifacts are referenced through the lock file; mutable URLs are pinning inputs only.
- Bootstrap scripts are trusted project code, tightly scoped, and idempotent.
- K3s-lab only qualifies prerequisites; it does not install/join a cluster in base MVP.
