# Minimum security checks

- Reject enrollment documents with unknown fields, expired timestamps, weak/empty credentials, disallowed URL schemes, or excessive resource requests.
- Confirm Headscale API/admin keys never appear in Android files, guest seed, logs, diagnostics, or source.
- Confirm one-use host/guest keys are deleted after successful enrollment.
- Confirm SSH password authentication and default passwords are disabled.
- Confirm recovery host forwarding binds loopback.
- Confirm Host API rejects missing/wrong controller capability and idempotency reuse with a different body.
- Confirm raw QMP, shell, QEMU argv, and kernel argv are not API fields.
- Confirm release manifest does not export debug activities/providers/fault injectors.
- Confirm diagnostic redaction covers enrollment tokens, auth keys, controller capabilities, private keys, and HTTP authorization headers.
