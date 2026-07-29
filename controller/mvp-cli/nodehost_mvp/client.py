from __future__ import annotations

from collections.abc import Mapping
import json
import ssl
import time
from typing import Any
import urllib.error
import urllib.request
from urllib.parse import quote

from .config import ControllerConfig


class ApiError(RuntimeError):
    """A bounded, redacted Host API failure."""


class NodeHostClient:
    TERMINAL_OPERATION_STATES = {
        "SUCCEEDED",
        "FAILED_PERMANENT",
        "CANCELLED",
        "ROLLED_BACK",
    }

    def __init__(self, config: ControllerConfig):
        self.config = config
        self._ssl_context = (
            ssl.create_default_context(cafile=config.ca_file)
            if config.ca_file
            else ssl.create_default_context()
        )

    @staticmethod
    def _segment(value: str) -> str:
        if not value:
            raise ValueError("resource identifier must not be empty")
        return quote(value, safe="")

    def request(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        if not path.startswith("/"):
            raise ValueError("Host API path must start with '/'")

        payload = None
        if body is not None:
            payload = json.dumps(body, separators=(",", ":")).encode("utf-8")

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.config.capability}",
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        request = urllib.request.Request(
            self.config.endpoint + path,
            data=payload,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(
                request,
                context=self._ssl_context,
                timeout=self.config.request_timeout_seconds,
            ) as response:
                raw = response.read()
                if not raw:
                    return None
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # Never include request headers or configuration in the exception.
            detail = exc.read(4096).decode("utf-8", errors="replace")
            raise ApiError(f"Host API returned HTTP {exc.code}: {detail}") from None
        except urllib.error.URLError as exc:
            raise ApiError(f"Host API connection failed: {exc.reason}") from None
        except json.JSONDecodeError as exc:
            raise ApiError(f"Host API returned invalid JSON: {exc.msg}") from None

    def status(self) -> Any:
        return self.request("GET", "/v1/status")

    def apply_vm(
        self,
        vm_id: str,
        spec: Mapping[str, Any],
        idempotency_key: str,
    ) -> Any:
        return self.request(
            "PUT",
            f"/v1/vms/{self._segment(vm_id)}",
            spec,
            idempotency_key,
        )

    def operation(self, operation_id: str) -> Any:
        return self.request(
            "GET",
            f"/v1/operations/{self._segment(operation_id)}",
        )

    def wait(self, operation_id: str, timeout: float = 600.0) -> Mapping[str, Any]:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            operation = self.operation(operation_id)
            if not isinstance(operation, Mapping):
                raise ApiError("Host API operation response is not an object")
            state = operation.get("state")
            if not isinstance(state, str):
                raise ApiError("Host API operation response has no string state")
            if state in self.TERMINAL_OPERATION_STATES:
                return operation
            time.sleep(self.config.poll_interval_seconds)
        raise TimeoutError(operation_id)
