# Control-plane boundaries

## Host API owns

- enrollment/status/capabilities;
- image import and verification;
- VM desired generation;
- start, stop, reset-system, and remove operations;
- operation status/cancellation;
- controller revocation;
- diagnostics;
- authenticated recovery SSH tunnel.

## SSH owns

- guest package installation;
- Ansible/Nix execution;
- Docker, K3s, Swarm, or Nomad setup;
- service configuration;
- interactive guest troubleshooting.

## Host API does not expose

- arbitrary shell strings;
- raw QMP;
- raw QEMU/kernel arguments;
- Kubernetes, Nomad, Swarm, or Compose objects;
- unrestricted TCP forwarding;
- Headscale administrative operations.

## MVP authentication adapter

The permanent port is `ControllerAuthenticator`. The overnight implementation may use a high-entropy imported controller capability and device-pinned HTTPS, reachable only through the host tailnet. This is classified as an MVP hack and must be replaceable by mTLS/principal authorization without changing use cases or API resources.

## API contract

`control/openapi.yaml` is authoritative. Mutations require an idempotency key and a monotonically increasing desired generation where applicable. Long operations return `202 Accepted` and a stable operation resource.
