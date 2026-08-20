# QEMU runtime implementation instructions

- Preserve the upstream compatibility argv fixture separately from the normalized production command.
- Public code consumes typed launch/profile values only; raw QEMU/kernel strings remain debug fixtures and never cross the Host API.
- QMP readiness requires greeting, `qmp_capabilities`, and a bounded `query-status`; a socket file alone is not readiness.
- QMP remains app-private and is never remotely exposed.
- Management forwards bind loopback unless a separately authenticated policy says otherwise.
- Disk mutation is offline and explicit. Do not claim qcow2 backing-overlay semantics while merely copying a mutable image.
- Keep launcher spawn and process reap on the dedicated lifetime thread until a physical A/B test proves replacement safe.
- Removing a production option requires golden-command tests plus device boot evidence.
