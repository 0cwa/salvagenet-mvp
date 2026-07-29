# Layers, reconciliation, and events

## Onion layers

### Domain (`node-model`)

Pure values and state transitions: node IDs, runtime specs, desired generations, observations, operations, profile descriptors, capability facts. No I/O.

### Application (`node-core`)

Use cases and ports: import enrollment, apply VM spec, reconcile, cancel operation, revoke controller, query status. It chooses plans but does not know Android or QEMU command syntax.

### Adapters

Room, QEMU, Tailscale, HTTP, Android Keystore, filesystem, clock, and imported Podroid logic.

### Composition (`node-shell`)

Creates the single graph, binds adapters, owns Android lifecycle, and translates platform callbacks into typed observations.

## Reconciliation loop

```text
wake reason
  -> load desired generation and operation state
  -> observe mesh/artifacts/QEMU/guest
  -> plan one or more stable steps
  -> persist next intended step
  -> execute through a port
  -> observe result
  -> persist result and publish snapshot
```

Only one reconciler actor mutates runtime desired/observed state. Bounded channels serialize wake reasons; duplicate wake events coalesce.

## Event classes

Events are facts, not commands:

- `AndroidUserUnlocked`
- `PackageUpdated`
- `NetworkChanged`
- `HostMeshStateChanged`
- `QemuProcessStarted`
- `QemuProcessExited`
- `QmpEventObserved`
- `ArtifactProgressObserved`
- `GuestBootstrapReady`
- `StoragePressureObserved`
- `ThermalStateObserved`

Commands are explicit use cases:

- `ImportEnrollment`
- `ApplyRuntimeGeneration`
- `CancelOperation`
- `RevokeController`

## Side-effect rule

A command handler never calls QEMU, Tailscale, or filesystems directly. It changes desired state or creates an operation, then wakes reconciliation. This makes API retry and process recovery tractable.

## MVP simplification

The initial implementation may reconcile in one coroutine with a mutex and polling probes. Keep the ports and durable step IDs even when the scheduler is simple.
