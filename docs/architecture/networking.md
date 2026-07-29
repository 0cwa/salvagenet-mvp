# Networking architecture

## Four distinct planes

| Plane | MVP implementation | Owner |
|---|---|---|
| Physical underlay | Android Wi-Fi/cellular/Ethernet | Android OS |
| Host management mesh | embedded Android-aware libtailscale + Headscale | Android node |
| Guest workload/administration mesh | ordinary Linux Tailscale client + Headscale | VM guest |
| Recovery path | Host API tunnel to loopback-only QEMU SSH forward | Android node |

Host and guest receive separate identities and tags. The controller keeps the Headscale administrative API credential; the phone receives only one-use registration material.

## Host mesh adapter

The first adapter is derived from the official Tailscale Android integration rather than generic desktop `tsnet`. It must provide Android interface/DNS callbacks, encrypted state storage, `VpnService`, socket protection, LocalAPI access, restart behavior, and custom control URL/auth key/hostname setup.

The `HostMesh` port exposes state and addresses, not Tailscale-specific netmap models.

## Guest enrollment

The controller mints a short-lived one-use guest pre-authentication key. Cloud-init receives a one-time bootstrap redemption token; the guest fetches the key from the host metadata endpoint, enrolls, deletes transient material, and posts readiness.

## Recovery

QEMU binds guest SSH forwarding to `127.0.0.1`. The Host API authenticates a controller and proxies an approved byte stream. `phonectl` presents this as an OpenSSH ProxyCommand.

## MVP+ USB

USB is a separate physical-link adapter:

```text
Linux node-linkd -> AOA bulk stream -> Android bridge -> QEMU stream netdev -> guest eth1
```

It remains outside the base build and task DAG until the acceptance ledger says every base gate is green.
