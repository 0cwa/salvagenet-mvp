# Control-plane boundaries

## Scope

This page defines the current stock-Android/QEMU Host API. The later signed-capsule and native orchestrator-attachment model is defined in `docs/architecture/turnkey-cluster-boundary.md`.

The current API remains intentionally VM-shaped through physical validation. PLAT-16 owns an additive execution-environment vocabulary before structurally different backends depend on it.

## Current Host API owns

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

## Guest-native tools own

- guest package installation;
- SSH, Ansible, and Nix execution;
- Docker Engine, K3s, Kubernetes, Swarm, or Nomad setup;
- native agent configuration and join operations;
- workloads, services, jobs, deployments, and cluster policy;
- interactive guest troubleshooting.

## Host API does not expose

- arbitrary shell strings;
- raw QMP;
- raw QEMU or kernel arguments;
- arbitrary host file paths;
- Kubernetes, Nomad, Swarm, Compose, Nix, or OpenTofu workload objects;
- unrestricted TCP forwarding;
- Headscale administrative operations;
- a custom scheduler or cluster desired-state database.

## Future provisioning capsule

After the current substrate milestone, one signed capsule may reference:

- controller/authority trust;
- runtime backend/profile;
- native overlay configuration;
- native orchestrator attachment configuration;
- named host policy;
- immutable artifact and secret references.

The capsule is applied through typed host resources. It does not turn the Host API into a universal configuration schema. A generic external-provisioner mode may expose stable inventory and SSH/recovery so ordinary OpenTofu, Nix, Ansible, or another native client performs unsupported setup.

## Artifact-resource separation

Public HTTPS import and controller upload are separate resources:

- public import accepts only the enrolled HTTPS origin/path and retains redirect, DNS-rebinding, deadline, size, digest, cancellation, and atomic-publication checks;
- controller upload is authenticated, sequential, resumable, chunk-bounded, digest-verified, and idempotent;
- both publish through one explicit serialized active-manifest policy;
- runtime consumers must use the same strict versioned artifact-manifest contract rather than independently interpreting JSON.

Future OCI/ORAS transport or peer caches remain artifact sources. Signature, digest, type, size, and policy verification occur before publication into the same normalized store.

## Authentication adapters

The permanent port is `ControllerAuthenticator`. The current milestone may use a high-entropy imported controller capability and device-pinned HTTPS, reachable only through the host tailnet. This is a replaceable MVP adapter.

Later reviewed principal authorization may add:

- hardware-backed controller and node keys;
- mTLS or sender-constrained credentials;
- multiple controllers and delegated authorities;
- revocation and recovery;
- signed capsule issuer policy;
- device attestation as admission evidence.

Those changes should not require workload or orchestrator resources in the Host API.

## API contract

`control/openapi.yaml` is authoritative for the current candidate. Mutations require an idempotency key and a monotonically increasing desired generation where applicable. Long operations return `202 Accepted` and a stable operation resource. Upload state, offset, replay, capacity, and idempotency conflicts are typed `409` responses; missing upload resources are `404`.

Do not rename current resources during H02A merely to anticipate later platforms. Before a second backend ships, PLAT-16 should define a reviewed additive migration from VM-specific to execution-environment resources, with compatibility only for real released users.
