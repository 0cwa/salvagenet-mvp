# Device compatibility-wrapper instructions

`tests/hil/` is the authoritative physical-device runner. Keep this directory limited to backwards-compatible entry points and focused one-off device-fact helpers.

- Do not add a second lifecycle test implementation here.
- Do not claim `force-stop`, Activity removal, service death, QEMU death, and reboot are equivalent disturbances.
- Physical evidence follows `tests/hil/AGENTS.md` and must identify the exact scenario actually exercised.
