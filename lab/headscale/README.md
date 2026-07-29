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
reach the configured control URL. It writes generated configuration atomically.

Keys are written to ignored `secrets/` files and never printed. The control
server uses HTTP only inside this isolated laboratory; this is not production
deployment guidance.
