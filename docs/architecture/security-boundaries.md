# Security boundaries

## Trust zones

```text
Controller authority
    |
    | authenticated Host API
    v
Android supervisor + Keystore + journal
    |
    | narrow runtime adapter
    v
QEMU process (same UID in MVP)
    |
    v
Guest OS and workloads (least trusted)
```

## Base invariants

- Headscale administrative API keys never leave the controller/lab host.
- Host and guest pre-authentication keys are single-use and short-lived.
- Controller credentials are stored through Android Keystore-backed storage where practical.
- Guest bootstrap receives no controller private key.
- QMP and QEMU sockets remain app-private.
- Recovery SSH forwarding binds loopback and is controller-authorized.
- No default password or password SSH authentication.
- Imported config is data, never executable shell or argv.
- Diagnostics redact secrets and guest user data.

## Known MVP limitation

QEMU initially runs under the application UID. Therefore only project-qualified guest profiles are in scope. Stronger QEMU UID/process isolation is a post-MVP security gate before claiming hostile arbitrary-image support.

## Enrollment file

The example enrollment contains placeholders only. Live enrollment files are ignored by Git. The parser validates version, expiry, URL schemes, key sizes, tags, and resource limits before storing anything.
