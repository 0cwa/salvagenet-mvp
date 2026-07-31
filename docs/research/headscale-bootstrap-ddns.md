# First-node Headscale bootstrap through dynamic DNS

## Question

Can SalvageNet offer an optional setup path where a user's first eligible node starts Headscale, registers a dynamic DNS name, and becomes discoverable to an intermittently connected controller—without requiring an existing Headscale server or a SalvageNet-operated service?

## Why this is useful

The current MVP assumes a prepared Headscale service. That is appropriate for physical validation, but it leaves a bootstrapping gap for a new self-hoster:

```text
controller needs private node connectivity
        ↓
node needs a Headscale control URL to join
        ↓
user does not yet run Headscale
```

An eligible first node could provide the coordination service before it joins the resulting tailnet. The controller would reach it through ordinary public DNS/HTTPS for initial provisioning, then move normal management onto the private overlay.

This remains lower priority than proving the existing-server path and the first external orchestrator attachment.

## Headscale constraints

Current Headscale documentation assumes:

- a server with a public IP address;
- HTTPS on TCP port 443;
- a modern Linux or BSD system;
- persistent state for private keys, policy, and the database;
- additional public ports when embedded DERP/STUN or remote gRPC is enabled.

References:

- <https://headscale.net/stable/setup/requirements/>
- <https://headscale.net/stable/usage/getting-started/>
- <https://headscale.net/stable/ref/integration/reverse-proxy/>

Therefore dynamic DNS is only name-to-address maintenance. It does not create inbound reachability through CGNAT, blocked ports, carrier filtering, or a router without forwarding.

## Eligible first nodes

Potential hosts, in preference order for this feature:

1. SBC or stable Linux host with a public/reachable address;
2. patched Android native backend with reliable boot/service/storage behavior and configured inbound reachability;
3. stock Android QEMU guest only after sustained runtime, storage, and inbound-routing behavior are qualified;
4. WSL or a laptop only when the user accepts that coordination disappears with that host.

Eligibility must be capability-based, not platform-name-based:

```text
public IPv4 and/or globally reachable IPv6
TCP 443 reachable from controller/test probe
persistent storage and backup path
trusted TLS issuance path
stable enough power and lifecycle policy
sufficient trust tier
known update/rollback behavior
```

A phone behind ordinary residential CGNAT is not eligible merely because it can update a DNS record.

## Proposed bootstrap flow

### 1. Generate the bootstrap authority

The controller creates:

- a Headscale service identity;
- a provider-scoped DDNS update credential or a one-use exchange reference;
- expected domain and certificate policy;
- encrypted service backup material;
- a signed bootstrap capsule limited to the coordination role.

No permanent DNS provider administrator credential should be included in a QR code or guest image.

### 2. Probe reachability before installation

The node and controller cooperate through ordinary Internet paths to establish:

- detected public addresses;
- IPv4/IPv6 availability;
- port-forwarding/manual-router requirements;
- whether TCP 443 can be reached from an external probe;
- whether UDP 3478 is available if embedded DERP is requested;
- address stability and DNS TTL policy.

The UI must distinguish:

```text
Eligible directly
Eligible after router configuration
Eligible through globally reachable IPv6
Not eligible because of CGNAT or blocked inbound traffic
Unknown; manual verification required
```

### 3. Register dynamic DNS

Use a provider-neutral `DnsRecordProvider` boundary with the minimum operations:

```text
create or claim record
update A/AAAA values
read current values
rotate/revoke update credential
remove record
export/migrate record configuration
```

Begin with one established DDNS provider or an RFC-compatible DNS update mechanism. A SalvageNet-operated community provider is a later adapter, not a protocol requirement.

### 4. Issue trusted TLS

Prefer ACME with a public CA. Support HTTP-01 only when port 80 is deliberately exposed; DNS-01 may be appropriate when the DNS provider supports narrowly scoped automation.

Record:

- domain;
- issuer;
- certificate identity and expiry;
- renewal status;
- exact service endpoint;
- whether a reverse proxy terminates TLS.

Do not automatically disable certificate verification to make bootstrap appear successful.

### 5. Start Headscale

Materialize the native Headscale configuration and service using ordinary Linux mechanisms. Persist:

- database;
- private keys;
- policy;
- service configuration;
- update/backup metadata.

The Headscale service remains upstream software. SalvageNet should own setup, health, backup, recovery, and role policy—not reimplement the coordination protocol.

### 6. Publish signed bootstrap discovery

The controller must discover the service before a tailnet exists. Options to evaluate:

- the configured FQDN carried in the original signed capsule;
- a small signed discovery object at a known HTTPS path;
- DNS TXT/SVCB/HTTPS records with a signed object digest;
- later, Zenoh or another reachable bootstrap fabric where already available.

DNS alone authenticates neither the node nor configuration authority. The controller verifies the signed capsule/discovery object and trusted TLS identity.

### 7. Enroll nodes

After Headscale health passes:

- create a narrow user/namespace and one-use pre-authentication key;
- enroll the host management identity;
- enroll the guest/upstream-agent identity separately where the current architecture requires it;
- erase transient enrollment material;
- move ordinary management to the private path;
- retain public HTTPS only for the Headscale control service and explicit recovery.

### 8. Back up and recover

The first coordination node is a potential single point of failure. The feature must include:

- encrypted backup of Headscale state;
- documented restore to another eligible node;
- DNS cutover;
- certificate renewal/cutover;
- version compatibility checks;
- recovery when the original node is lost;
- migration to an external provider or another self-hosted node.

This feature simplifies first setup; it does not by itself make Headscale highly available.

## Relationship to orchestrator HA

Headscale coordination is separate from Docker Swarm, K3s, or Nomad control-plane quorum.

A first node may initially host both services for a tiny setup, but the UI must show the resulting shared failure domain. The recommended resilient layout later separates or replicates stable roles across eligible SBC/Linux/patched nodes according to the upstream system's rules.

## Relationship to Zenoh

Zenoh might later help with local discovery, status, and signed-object retrieval when the controller or public Internet is intermittent. It does not remove the need for a publicly reachable Headscale endpoint during ordinary Tailscale client coordination, and it should not become a hidden dependency of the DDNS path.

## Community DDNS option

A future community service could provide delegated names for users who do not want a commercial DDNS account. Requirements before operation include:

- open protocol and provider-neutral node adapter;
- scoped update credentials;
- rate limits and abuse controls;
- privacy and minimal logging;
- domain/record deletion;
- zone or record export;
- migration to another provider;
- service outage behavior;
- funding and operator responsibility;
- clear statement that DNS does not provide NAT traversal.

The community service must never be required for SalvageNet, Headscale, or existing provider support.

## Experiments

| ID | Experiment | Closure evidence |
|---|---|---|
| DDNS-01 | Public IPv4 and forwarded 443 | External health probe, address change, DNS update, TLS renewal |
| DDNS-02 | Globally reachable IPv6 | External IPv6 health probe, prefix/address change, DNS update |
| DDNS-03 | CGNAT detection | Repeatable negative classification and useful fallback guidance |
| DDNS-04 | DNS provider abstraction | Two structurally different providers or one provider plus standards-based dynamic update |
| DDNS-05 | Headscale install and restore | Exact state backup, destruction, restore to another node, DNS cutover |
| DDNS-06 | Controller rediscovery | Controller offline during address change, then reconnects through verified discovery |
| DDNS-07 | Shared-role failure | Headscale and orchestrator manager co-located; UI reports the failure-domain risk |

## Adopt criteria

Implement the feature when:

- the existing Headscale path and first orchestrator proof pass;
- at least one target node class is demonstrably public-reachable and stable;
- backup/restore and trusted TLS can be automated safely;
- the UX can identify ineligible CGNAT cases before destructive setup;
- the added maintenance is lower than the onboarding value.

Otherwise retain it as documented manual guidance and recommend an external reachable Headscale host.
