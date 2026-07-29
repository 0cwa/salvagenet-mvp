# mesh-tailscale instructions

- Derive from official Android libtailscale/VpnService hooks, not generic desktop `tsnet` assumptions.
- Expose only typed status, addresses, configure/start/stop/clear operations.
- Delete one-use auth keys after confirmed enrollment.
- Never store a Headscale administrative API key.
- Physical VPN permission/restart behavior requires explicit device evidence.
