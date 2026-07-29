# mesh-tailscale

Android-aware embedded host-mesh adapter built against the pinned official
`libtailscale` gomobile binding.

`LibtailscaleHostMesh` validates and persists the Headscale control URL,
hostname, and one-use auth key in Android Keystore-backed AES-GCM state. It
reports only the typed `HostMeshStatus` contract. The key remains available for
retry until LocalAPI reports `Running`, then is atomically removed. Confirmed
VPN revocation also removes the key. Logout must succeed before local
identity/configuration state is cleared.

`NodeTailscaleVpnService` adapts the official Android hooks: VPN builder,
interface/DNS platform callbacks, underlying-network socket binding, foreground
lifecycle, service reconnect, revoke, and bounded sticky restart handling.
Callers must obtain user VPN approval with `VpnService.prepare`; without it,
`start()` reports `NEEDS_PERMISSION` and does not redeem the key.

LocalAPI calls have a five-second deadline, 4 KiB request and 64 KiB response
limits. Status address output is capped at 16 entries. Native upstream logs are
suppressed in release builds; debug lines are redacted and capped at 1 KiB.
Diagnostic failures are classified without including enrollment material.
