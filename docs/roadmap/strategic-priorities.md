# Strategic roadmap priorities

## Purpose

This page connects the durable product north star to the GitHub issue roadmap without changing current implementation authorization. It records what should be proved first, why later work is ordered as it is, and which attractive ideas are deliberately held.

The live GitHub issue graph owns planned outcomes and dependency links after apply. `agents/task-dag.json` remains the sole active authorization. At the time of this realignment, H02A/GUEST-01 remains the only active product task.

## Priority rule

Choose the smallest next phase that proves or falsifies the highest-value product assumption.

Do not prioritize by architectural elegance, quantity of available agent work, or how much can be implemented without hardware. Prefer evidence that turns unknown product behavior into a clear decision.

## Immediate path: finish preflight, then test the phone

### 1. Bound H02A

Finish the canonical Ubuntu host-QEMU qualification already in progress. Its purpose is to remove guest-boot ambiguity before phone debugging, not to become a permanent qualification framework for every future backend.

Stop adding host-QEMU sophistication once the reviewed run proves:

- exact image/profile/firmware identities;
- QMP-running state;
- NoCloud completion;
- key-only loopback SSH;
- one guest reboot and one complete stop/start;
- bounded secret-hygiene evidence and cleanup.

Further host-lab work requires a failure discovered in the physical path or a direct release/security blocker.

### 2. Execute the physical substrate sequence

Use the new development VM and the single `tests/hil/` runner to close, in order:

1. `DEVICE-01`: APK-native QEMU, host Headscale, authenticated Host API;
2. `GUEST-02` only where it materially reduces the next physical ambiguity;
3. `DEVICE-02`: controller-delivered Ubuntu, separate guest identity, ordinary SSH;
4. `DEVICE-03`: recovery while guest mesh is unavailable;
5. `DEVICE-04`: Activity, service, process, reboot, and controller-offline durability;
6. `RELEASE-01`: one exact candidate and evidence set.

A diagnostic run during a changing phase is valuable, but the final seal must rerun gate-relevant scenarios against one exact APK and source identity.

### 3. Do not activate strategic expansion work yet

The strategic catalog makes later work visible to humans and agents. It does not add any item to the active DAG. Do not begin Slint, Nix/OpenTofu, Swarm, Zenoh, patched Android, Linux, DDNS, or community infrastructure while the current physical path can proceed, unless a phase review demonstrates that one is the blocker.

## First product proof: turnkey cluster MVP

The current B01–B20 milestone validates a useful node host. The next milestone proves the product users actually want.

### MVP-01 — signed provisioning capsule

Define one small authenticated envelope that composes existing native formats. This is the highest-priority architectural addition after the substrate because every UI, declarative tool, platform, and orchestrator otherwise risks inventing a different setup model.

The common layer owns only runtime, connectivity, attachment, host policy, trust, and immutable references. It does not own workloads.

### MVP-02 — Docker Engine Swarm mode

Use Swarm first because an official worker join is small, certificates and placement are upstream behavior, and the proof can be completed without importing a new workload schema. Target Docker Engine Swarm mode, not raw SwarmKit.

Success includes real placement, configuration-laptop interruption, drain, leave, replacement, and rejoin.

This does not make Swarm the permanent preferred orchestrator. It validates the attachment boundary before adding K3s and Nomad complexity.

### MVP-03 — thin Slint controller

Build the polished controller around real capsule and Host API contracts. Keep the existing Android UI/lifecycle implementation until device semantics settle. The Slint controller should launch native SSH, OpenTofu, Nix, Docker, Kubernetes, or Nomad tools instead of reproducing them.

### MVP-04 — Nix and OpenTofu composition

Provide reproducible expert workflows alongside the guided UI:

- Nix composes builds, profiles, native configuration, patched-system modules, and capsules.
- OpenTofu modules use existing providers and assign or publish the resulting intent.
- Do not build a provider until enrolled-node assignment, attestation, update rings, or another real remote resource exists.

### MVP-05 — unattended safety floor

Before public early access, establish the minimum phone safety and continuity floor:

- screen-off and Doze;
- explicit wake policy;
- charging loss and recovery;
- thermal reduction and emergency stop;
- storage reserve and full-disk behavior;
- process death and restart;
- network and configuration-authority absence;
- a bounded soak on the primary device.

Broader OEM and performance claims remain M3 reliability work.

## Platform expansion order

### B. Patched Android

After stock Android is proven, generalize the public runtime vocabulary just enough for a second backend, then implement the `my-avbroot-setup` system service and native Linux/container path. Attestation follows the real patch/build pipeline so it measures actual artifacts rather than a hypothetical design.

### C. SBC

Add the native SBC agent next. It provides stable orchestrator managers, ingress, artifact caches, optional Headscale/Zenoh services, and USB peers. This is the preferred stable-control-plane class for small deployments.

### D. Existing Linux

Extend the same agent to older Linux machines with native, container, VM, and microsandbox envelopes. This is also the second non-Android platform that tests whether the common contracts are genuinely portable.

### E. Custom Linux appliance

Build a dedicated image only after native Linux requirements, artifact trust, update, rollback, and recovery are evidenced. Evaluate existing declarative OS foundations first.

### F. WSL

Reuse the Linux agent inside WSL with a narrow Windows setup/lifecycle bridge. It remains lower priority because it adds less unique capability than old phones, patched phones, SBCs, and existing Linux.

## Orchestrator breadth

Order after Swarm:

1. real K3s worker qualification through existing PLAT-05;
2. Nomad client attachment through PLAT-23;
3. generic external-provisioner mode for unsupported systems;
4. first-class adapters only when join/leave/health/recovery integration creates material value.

Every adapter must keep native configuration authoritative and avoid cluster objects in the Host API.

## Zenoh decision

Build current HTTPS/Tailscale contracts so transport is replaceable, but do not implement Zenoh before the stock and Swarm proofs.

PLAT-24 should answer a bounded question: does Zenoh materially improve intermittent-controller, local-cell, peer-assisted immutable-object retrieval, liveliness, and query behavior at acceptable Android/Linux complexity?

Adopt only a narrow subset if the answer is yes. Reject uses that duplicate:

- Tailscale private connectivity;
- orchestrator desired state;
- artifact signatures and immutable identity;
- workload/application data protocols;
- a database or CRDT state engine.

## First-node Headscale and dynamic DNS

PLAT-25 is intentionally held. It is useful onboarding, not a prerequisite for the first proof.

The preferred flow is:

1. probe whether the selected first node has stable public reachability or configured inbound forwarding;
2. register/update a provider-neutral dynamic DNS record;
3. obtain trusted TLS and start Headscale on port 443;
4. publish signed health/discovery information outside the new tailnet;
5. let the controller discover and verify the service;
6. enroll later nodes;
7. preserve export, backup, recovery, and migration.

Dynamic DNS maps a changing address to a name; it does not solve CGNAT or blocked inbound ports. Ineligible networks must receive a clear fallback such as an existing Headscale/Tailscale service, a reachable SBC/VPS, or a future reviewed relay design.

A community DDNS service is a later optional provider and must not become a hard dependency.

## Community infrastructure

Only after production identity and platform foundations:

- signed scoped QR invitations and account-linked device keys;
- explicit consent and revocation;
- user-owned storage locality policies expressed through native orchestrator/storage mechanisms;
- optional community DDNS;
- no permanent secrets in QR codes;
- no custom distributed filesystem by default.

## Parallel work policy

A path-disjoint documentation, website, release-compliance, or tooling task may run in parallel only when:

- it has a reviewed packet and no ownership conflict;
- it cannot delay the physical or turnkey critical path;
- it makes no unsupported acceptance claim;
- it has a finite user or development outcome;
- its maintenance cost is lower than the ambiguity it removes.

The presence of unused agent capacity is not sufficient reason to activate speculative work.

## Phase-boundary questions

Before every new active phase, ask:

1. What highest-value uncertainty remains?
2. Can a physical or integration experiment answer it before more architecture is added?
3. Does the proposed task prove user value, reduce a present safety/correctness risk, or unblock the next proof?
4. Is an upstream tool or native format already responsible for this behavior?
5. Will the task make a future platform pretend to be a QEMU VM or another current implementation detail?
6. Does it alter the north star, current milestone, roadmap, authorization, or acceptance authority—and are those changes explicit?
7. What stops the work from expanding after its evidence question is answered?
