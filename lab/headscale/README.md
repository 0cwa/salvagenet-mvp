# Disposable Headscale 0.28 lab

```sh
cp .env.example .env
# Replace HEADSCALE_PUBLIC_URL with this host's LAN URL.
scripts/up.sh
scripts/create-keys.sh
scripts/status.sh
```

The renderer refuses placeholders, localhost, unspecified addresses, and
RFC-documentation addresses by default because an Android phone must be able to
reach the configured control URL. `HEADSCALE_HOST_PORT` must match that URL and
can be changed when port 8080 is occupied. Configuration is written atomically.
The scripts use Docker Compose or Podman Compose when available, and fall back
to direct Podman for this single-container lab.

Keys are written to ignored `secrets/` files and never printed. The control
server uses HTTP only inside this isolated laboratory; this is not production
deployment guidance.
