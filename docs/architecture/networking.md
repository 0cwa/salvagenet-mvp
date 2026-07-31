# Networking architecture

## Scope

The current milestone uses Android/Tailscale host management, a separate Linux guest Tailscale identity, and host-mediated recovery. The durable networking direction keeps physical underlay, private overlay, bootstrap/discovery, orchestrator control, workload traffic, and recovery as separate planes.

## Current four planes

| Plane | Current implementation | Owner |
|---|---|---|
| Physical underlay | Android Wi-Fi/cellular/Ethernet | Android OS |
| Host management mesh | embedded Android-aware libtailscale + Headscale | Android node |
| Guest workload/administration mesh | ordinary Linux Tailscale client + Headscale | VM guest |
| Recovery path | Host API tunnel to loopback-only QEMU SSH forward | Android node |

Host and guest receive separate identities and tags. The controller keeps the Headscale administrative API credential; the phone receives only one-use registration material.

## Durable plane separation

Later platforms and transports should preserve:

1. **Physical underlay:** Wi-Fi, cellular, Ethernet, USB, or another link.
2. **Private overlay:** Tailscale/Headscale initially; another provider only after a real second adapter proves the boundary.
3. **Bootstrap/discovery:** signed capsule delivery, node discovery, bounded status, and immutable-object location before or outside the overlay.
4. **Host management/recovery:** typed authenticated host operations and a narrow repair channel.
5. **Orchestrator control:** Docker, Kubernetes/K3s, Nomad, or another upstream manager/server protocol.
6. **Workload network:** Docker overlay, Kubernetes CNI, application protocols, ingress, storage, and service traffic.

Do not use one transport's convenience to merge identity, authority, or failure domains across these planes.

## Host mesh adapter

The first adapter is derived from the official Tailscale Android integration rather than generic desktop `tsnet`. It must provide Android interface/DNS callbacks, encrypted state storage, `VpnService`, socket protection, LocalAPI access, restart behavior, and custom control URL/auth key/hostname setup.

The `HostMesh` port exposes state and addresses, not Tailscale-specific netmap models.

On native Linux, patched Android, SBC, and WSL environments, prefer the official Linux Tailscale client and kernel TUN path where supported.

## Guest enrollment

The controller mints a short-lived, audience-bound, one-use bootstrap redemption token for exactly one intended guest identity, profile, and control-plane enrollment purpose. The token has a narrow expiry and nonce, is presented to the host metadata endpoint, and is redeemed through an atomic consume-once operation that cannot return the overlay pre-authentication key twice.

Cloud-init receives only that scoped redemption token, never the controller's administrative credential or a reusable overlay key. After successful or terminally failed redemption, the guest and host must erase the token from generated NoCloud media, cloud-init instance data, process environments, temporary files, and retained logs. Logs record only a redacted token identifier and redemption result. A process that reads bootstrap state before redemption must not obtain material reusable for another guest, profile, audience, or later attempt.

The guest uses the redeemed short-lived overlay key to enroll, erases that key and all transient exchange material, and posts readiness. Replay, expired, wrong-audience, wrong-device, and already-redeemed requests fail visibly.

Future provisioning capsules should contain one-use enrollment references or recipient-bound scoped exchange material, not permanent overlay credentials.

## Recovery

QEMU binds guest SSH forwarding to `127.0.0.1`. The Host API authenticates a controller and proxies an approved byte stream. `phonectl` presents this as an OpenSSH ProxyCommand.

A future backend may provide a different native recovery mechanism, but it must remain independent from guest/workload overlay health.

## Zenoh research boundary

PLAT-24 evaluates Zenoh only after the stock and first orchestrator proofs. Potential uses are:

- peer/client/router discovery;
- node liveliness;
- bounded status queries;
- cell gateways;
- peer-assisted retrieval of signed immutable capsules or artifacts;
- intermittent configuration-authority reconnect.

Zenoh does not replace Tailscale/Headscale, orchestrator desired state, workload networks, or application storage by default. Adoption requires an explicit ADR from Android/Linux footprint, lifecycle, security, and recovery evidence.

## First-node Headscale and dynamic DNS

PLAT-25 investigates an optional bootstrap path where a public-reachable first node runs Headscale and registers a dynamic DNS name. This is pre-overlay public HTTPS bootstrap, not a tailnet operation.

Requirements and caveats are in `docs/research/headscale-bootstrap-ddns.md`:

- public reachability and trusted HTTPS on port 443;
- external reachability probe before installation;
- dynamic DNS provider abstraction;
- certificate issuance/renewal;
- state backup and restore to another node;
- controller rediscovery after address changes;
- clear rejection/fallback for CGNAT and blocked inbound ports.

Dynamic DNS does not provide NAT traversal. A future community DDNS service is an optional provider, never a dependency of the node architecture.

## Orchestrator networking

The attachment adapter must preserve each upstream system's network model. SalvageNet may configure native interfaces, addresses, MTU, routes, and labels based on measured underlays, but it must not create a universal CNI/overlay abstraction.

For nested overlays, qualification must measure:

- direct versus relayed underlay paths;
- effective MTU and fragmentation;
- DNS behavior;
- reconnect and address change;
- controller/coordination interruption;
- service and recovery reachability.

## MVP+ USB

USB is a separate physical-link adapter:

```text
Linux node-linkd -> AOA bulk stream -> Android bridge -> QEMU stream netdev -> guest eth1
```

It remains outside the base build and task DAG until the acceptance ledger says every base gate is green.

Patched Android may later use native USB Ethernet where the system backend and kernel allow it. Stock Android AOA and native USB Ethernet are separate adapters. Both must retain SLIRP/ordinary-network fallback and host recovery.
