from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class ControllerConfig:
    """Validated local configuration for the disposable MVP controller."""

    endpoint: str
    capability: str
    ca_file: str | None
    poll_interval_seconds: float = 1.0
    request_timeout_seconds: float = 30.0

    @classmethod
    def load(cls, path: str | None) -> "ControllerConfig":
        config_path: Path | None = None
        if path:
            config_path = Path(path).expanduser().resolve()
            data: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("controller config must be a JSON object")
        else:
            data = {
                "endpoint": os.environ.get("NODEHOST_ENDPOINT"),
                "controllerCapability": os.environ.get("NODEHOST_CONTROLLER_CAPABILITY"),
                "tls": {"caFile": os.environ.get("NODEHOST_CA_FILE")},
            }

        unknown = set(data) - {
            "endpoint", "controllerCapability", "tls",
            "pollIntervalSeconds", "requestTimeoutSeconds",
        }
        if unknown:
            raise ValueError(f"unsupported controller setting(s): {', '.join(sorted(unknown))}")

        endpoint_value = data.get("endpoint")
        if not isinstance(endpoint_value, str):
            raise ValueError("endpoint must be a string")
        endpoint = endpoint_value.rstrip("/")
        parsed = urlparse(endpoint)
        if parsed.scheme != "https":
            raise ValueError("controller endpoint must use https")
        if not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("controller endpoint must contain only a host and optional port")
        try:
            parsed.port
        except ValueError as exc:
            raise ValueError("controller endpoint has an invalid port") from exc
        if parsed.path not in ("", "/") or parsed.params or parsed.query or parsed.fragment:
            raise ValueError("controller endpoint must not contain a path, query, or fragment")

        capability = data.get("controllerCapability")
        if not isinstance(capability, str) or not 24 <= len(capability) <= 512:
            raise ValueError("controller capability must contain 24..512 characters")
        if any(ord(character) < 0x21 or ord(character) > 0x7E for character in capability):
            raise ValueError("controller capability must contain printable ASCII without spaces")

        tls = data.get("tls") or {}
        if not isinstance(tls, dict):
            raise ValueError("tls must be an object")
        unsupported = set(tls) - {"caFile"}
        if unsupported:
            names = ", ".join(sorted(unsupported))
            raise ValueError(f"unsupported MVP TLS setting(s): {names}")

        ca_file = tls.get("caFile")
        if ca_file is not None and not isinstance(ca_file, str):
            raise ValueError("tls.caFile must be a string or null")
        if ca_file:
            ca_path = Path(ca_file).expanduser()
            if not ca_path.is_absolute() and config_path is not None:
                ca_path = config_path.parent / ca_path
            ca_path = ca_path.resolve()
            if not ca_path.is_file():
                raise ValueError("tls.caFile must identify a readable file")
            ca_file = str(ca_path)

        poll_interval = cls._bounded_number(data.get("pollIntervalSeconds", 1.0), "pollIntervalSeconds", 0.05, 60)
        request_timeout = cls._bounded_number(data.get("requestTimeoutSeconds", 30.0), "requestTimeoutSeconds", 1, 300)
        return cls(endpoint, capability, ca_file, poll_interval, request_timeout)

    @staticmethod
    def _bounded_number(value: object, name: str, minimum: float, maximum: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be numeric")
        result = float(value)
        if not math.isfinite(result) or not minimum <= result <= maximum:
            raise ValueError(f"{name} must be in [{minimum}, {maximum}]")
        return result
