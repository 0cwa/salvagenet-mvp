# Controller instructions

The Python controller is an MVP test client, not the permanent controller architecture. Keep it dependency-light and aligned with `control/openapi.yaml`. It may call the Host API and act as an SSH ProxyCommand; it must not become a scheduler or hide guest provisioning logic.
