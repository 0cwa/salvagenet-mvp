# H02A — canonical Ubuntu guest boot qualification

Status: **PLANNED** after F01 merge.

```sh
make context TASK=H02A
```

This is the sole candidate for the next active phase. It proves canonical UEFI/QMP, NoCloud, key-only loopback SSH, restart, and secret hygiene under Linux host QEMU. It does not include Headscale/Tailscale guest enrollment and cannot close Android acceptance gates.
