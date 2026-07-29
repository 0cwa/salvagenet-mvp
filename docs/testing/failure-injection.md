# Failure injection

Inject failures at stable operation boundaries:

- download interrupted before/after fsync;
- digest mismatch;
- storage full while staging;
- process death after desired state persisted but before QEMU start;
- process death after QEMU start but before observed state persisted;
- stale Unix sockets;
- QMP disconnect and reconnect;
- guest cloud-init failure;
- guest Headscale key expired or already consumed;
- host mesh disconnected;
- controller retries the same idempotency key;
- controller submits an older generation;
- graceful shutdown timeout;
- Android service killed;
- Activity destroyed/swiped;
- reboot before and after first unlock.

Debug fault controls must live in debug/test source sets and be excluded from release. Each fault test asserts both durable operation state and external observed state.
