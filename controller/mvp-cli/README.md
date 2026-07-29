# `phonectl-mvp`

This dependency-light Python client is a disposable API exerciser and OpenSSH
`ProxyCommand`, not the permanent controller implementation.

```sh
cp controller.example.json controller.json
# Replace endpoint/capability and optionally provide a CA file.
./bin/phonectl-mvp --config controller.json status
./bin/phonectl-mvp --config controller.json import-image image-import.json
./bin/phonectl-mvp --config controller.json apply-vm default request.json
./bin/phonectl-mvp --config controller.json operations
./bin/phonectl-mvp --config controller.json wait <operation-id>

Every OpenAPI resource is available as a command; run `phonectl-mvp --help` for
the bounded list. Instead of `--config`, `NODEHOST_ENDPOINT`,
`NODEHOST_CONTROLLER_CAPABILITY`, and optionally `NODEHOST_CA_FILE` may be used.
```

The MVP client accepts only HTTPS. It uses the configured CA or the platform
trust store. SPKI pinning belongs to enrollment but is intentionally not
pretended by this small client; an unknown TLS key in `controller.json` is
rejected.

Recovery SSH:

```sshconfig
Host phone-default-recovery
  ProxyCommand /path/to/phonectl-mvp --config /path/to/controller.json proxy-ssh default
  User nodeadmin
```

Never commit `controller.json`; it contains a bearer capability and is ignored.
