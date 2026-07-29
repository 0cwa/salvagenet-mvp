# VM profiles

The registry contains exactly three versioned v1alpha1 profiles. Every `profile.json` is a complete document that validates to the same typed model; `metadata.extends` records lineage but deployment never depends on an implicit merge.

- `alpine-direct-qualification` preserves the Podroid direct-kernel path.
- `ubuntu-2404-arm64-uefi` proves distribution independence.
- `k3s-worker-lab` derives from Ubuntu hardware and emits prerequisite evidence only. It does not install or join K3s.

Profiles reference artifact IDs from `locks/images.lock.json`, never mutable URLs. The artifact adapter must resolve an ID to a digest and expected byte size before activation.

Run `tools/profiles/validate.py` or `make validate`.
