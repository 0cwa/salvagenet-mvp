# embedded Tailscale implementation instructions

- The pinned official Android-aware libtailscale/VpnService lifecycle is authoritative; do not substitute generic Linux or unadapted `tsnet` assumptions.
- Keep the `HostMesh` public surface typed and provider-minimal. Internal packages may separate `runtime`, `localapi`, `vpn`, `platform`, and `persistence` without creating processes.
- Enrollment deadlines use a monotonic clock and are independent of status-poll frequency.
- Never log or stringify one-use auth keys, LocalAPI authorization, private node state, or unredacted backend errors.
- Delete one-use material only after confirmed enrollment; preserve recovery state on ambiguous failure.
- Release builds reject cleartext control URLs. Debug-lab exceptions remain explicit and test-only.
- VPN consent, service recreation, network transitions, direct/relay paths, memory, and wakeups require physical evidence before reliability claims.
