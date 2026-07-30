# Control-plane boundaries

## Host API owns

- enrollment, status, and capabilities;
- public HTTPS image import with enrolled-origin and SSRF protections;
- authenticated resumable controller artifact upload;
- artifact verification and active-manifest publication;
- VM desired generation;
- start, stop, reset-system, and remove operations;
- operation status and cancellation;
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
- raw QEMU or kernel arguments;
- arbitrary host file paths;
- Kubernetes, Nomad, Swarm, or Compose objects;
- unrestricted TCP forwarding;
- Headscale administrative operations.

## Artifact-resource separation

Public HTTPS import and controller upload are separate resources:

- public import accepts only the enrolled HTTPS origin/path and retains redirect, DNS-rebinding, deadline, size, digest, cancellation, and atomic-publication checks;
- controller upload is authenticated, sequential, resumable, chunk-bounded, digest-verified, and idempotent;
- both publish through one explicit serialized active-manifest policy;
- runtime consumers must use the same strict versioned artifact-manifest contract established by F01 rather than independently interpreting JSON.

## MVP authentication adapter

The permanent port is `ControllerAuthenticator`. The MVP may use a high-entropy imported controller capability and device-pinned HTTPS, reachable only through the host tailnet. This is a replaceable MVP hack; a reviewed mTLS/principal model may replace it without changing use cases or resource shapes.

## API contract

`control/openapi.yaml` is authoritative. Mutations require an idempotency key and a monotonically increasing desired generation where applicable. Long operations return `202 Accepted` and a stable operation resource. Upload state, offset, replay, capacity, and idempotency conflicts are typed `409` responses; missing upload resources are `404`.
