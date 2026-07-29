from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class ControllerConfig:
    """Local configuration for the disposable MVP controller client.

    The permanent enrollment protocol may pin an SPKI. This small client does not
    implement SPKI pinning; it relies on the configured CA file or the platform
    trust store and fails closed on non-HTTPS endpoints.
    """

    endpoint: str
    capability: str
    ca_file: str | None
    poll_interval_seconds: float = 1.0
    request_timeout_seconds: float = 30.0

    @classmethod
    def load(cls, path: str) -> "ControllerConfig":
        config_path = Path(path).expanduser().resolve()
        data = json.loads(config_path.read_text(encoding="utf-8"))

        endpoint = str(data["endpoint"]).rstrip("/")
        parsed = urlparse(endpoint)
        if parsed.scheme != "https":
            raise ValueError("controller endpoint must use https")
        if not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("controller endpoint must contain only a host and optional port")
        if parsed.path not in ("", "/") or parsed.params or parsed.query or parsed.fragment:
            raise ValueError("controller endpoint must not contain a path, query, or fragment")

        capability = str(data["controllerCapability"])
        if len(capability) < 24:
            raise ValueError("controller capability must contain at least 24 characters")

        tls = data.get("tls") or {}
        unsupported = set(tls) - {"caFile"}
        if unsupported:
            names = ", ".join(sorted(unsupported))
            raise ValueError(f"unsupported MVP TLS setting(s): {names}")

        ca_file = tls.get("caFile")
        if ca_file:
            ca_path = Path(str(ca_file)).expanduser()
            if not ca_path.is_absolute():
                ca_path = config_path.parent / ca_path
            ca_file = str(ca_path.resolve())

        poll_interval = float(data.get("pollIntervalSeconds", 1.0))
        request_timeout = float(data.get("requestTimeoutSeconds", 30.0))
        if poll_interval <= 0:
            raise ValueError("pollIntervalSeconds must be positive")
        if request_timeout <= 0:
            raise ValueError("requestTimeoutSeconds must be positive")

        return cls(
            endpoint=endpoint,
            capability=capability,
            ca_file=ca_file,
            poll_interval_seconds=poll_interval,
            request_timeout_seconds=request_timeout,
        )
