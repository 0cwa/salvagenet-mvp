# Headscale laboratory

The lab uses pinned Headscale 0.28.0 with SQLite. It is disposable testing
infrastructure, not production guidance.

## Start

```sh
cp lab/headscale/.env.example lab/headscale/.env
# Set HEADSCALE_PUBLIC_URL to a LAN URL reachable by the phone.
make lab-up
make lab-keys
make lab-status
```

Before starting containers, the renderer rejects placeholders, loopback,
unspecified, and documentation-only IP addresses. The container then runs
Headscale's `configtest`, starts the service, and exposes its health check.
Open the health URL from the phone before assigning Tailscale work to an agent.

`make lab-keys` creates a laboratory user and mints separate one-use tagged keys
for controller, Android host, and VM guest. The values are written under ignored
`lab/headscale/secrets/` and never printed or placed in context packs.

## Optional Linux clients

`lab/headscale/scripts/start-userspace-client.sh` runs a Tailscale client in
userspace networking mode when a local `tailscale` binary is installed. Physical
Android testing still needs the phone's one-time VPN approval.

## Reset

```sh
make lab-down
lab/headscale/scripts/reset.sh
```

The laboratory policy is intentionally permissive only among
`tag:node-controller`, `tag:node-host`, and `tag:node-worker` identities.
