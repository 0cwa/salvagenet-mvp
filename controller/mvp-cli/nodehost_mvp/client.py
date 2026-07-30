from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
import re
import ssl
import time
from typing import Any
import urllib.error
import urllib.request
from urllib.parse import quote

from .config import ControllerConfig


class ApiError(RuntimeError):
    """A bounded, redacted Host API failure."""


class RetryableOperationError(ApiError):
    """The host stopped an operation at an explicit retry boundary."""

    def __init__(self, operation: Mapping[str, Any]):
        operation_id = operation.get("id", "unknown")
        error_code = operation.get("errorCode") or "UNSPECIFIED"
        super().__init__(f"operation {operation_id} failed retryably: {error_code}")
        self.operation = operation


class NodeHostClient:
    MAX_RESPONSE_BYTES = 2 * 1024 * 1024
    MAX_REQUEST_BYTES = 1024 * 1024
    ARTIFACT_ID = re.compile(r"^[a-z0-9][a-z0-9.-]{0,127}$")
    SHA256 = re.compile(r"^[a-f0-9]{64}$")
    TERMINAL_OPERATION_STATES = {
        "SUCCEEDED", "FAILED_PERMANENT", "CANCELLED", "ROLLED_BACK",
    }

    def __init__(self, config: ControllerConfig):
        self.config = config
        self._ssl_context = ssl.create_default_context(cafile=config.ca_file) if config.ca_file else ssl.create_default_context()

    @staticmethod
    def _segment(value: str) -> str:
        if not value or len(value) > 128:
            raise ValueError("resource identifier must contain 1..128 characters")
        return quote(value, safe="")

    def _redact(self, value: str) -> str:
        return value.replace(self.config.capability, "[REDACTED]")

    def _perform(
        self,
        method: str,
        path: str,
        payload: bytes | None = None,
        *,
        content_type: str | None = None,
        idempotency_key: str | None = None,
        extra_headers: Mapping[str, str] | None = None,
    ) -> Any:
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("Host API path must be absolute")
        if idempotency_key is not None and not 16 <= len(idempotency_key) <= 200:
            raise ValueError("idempotency key must contain 16..200 characters")
        if payload is not None and len(payload) > self.MAX_REQUEST_BYTES:
            raise ValueError("request body exceeds 1 MiB")
        headers = {"Accept": "application/json", "Authorization": f"Bearer {self.config.capability}"}
        if payload is not None:
            headers["Content-Type"] = content_type or "application/octet-stream"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        if extra_headers:
            for name, value in extra_headers.items():
                if name.lower() in {"authorization", "idempotency-key", "content-length"}:
                    raise ValueError(f"reserved request header: {name}")
                headers[name] = value
        request = urllib.request.Request(
            self.config.endpoint + path,
            data=payload,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, context=self._ssl_context, timeout=self.config.request_timeout_seconds) as response:
                raw = response.read(self.MAX_RESPONSE_BYTES + 1)
                if len(raw) > self.MAX_RESPONSE_BYTES:
                    raise ApiError("Host API response exceeds 2 MiB")
                if not raw:
                    return None
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read(4097)
            suffix = " [truncated]" if len(detail) > 4096 else ""
            safe = detail[:4096].decode("utf-8", errors="replace")
            raise ApiError(self._redact(f"Host API returned HTTP {exc.code}: {safe}{suffix}")) from None
        except urllib.error.URLError as exc:
            raise ApiError(self._redact(f"Host API connection failed: {exc.reason}")) from None
        except UnicodeDecodeError:
            raise ApiError("Host API returned non-UTF-8 JSON") from None
        except json.JSONDecodeError as exc:
            raise ApiError(f"Host API returned invalid JSON: {exc.msg}") from None

    def request(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        payload = None
        if body is not None:
            payload = json.dumps(body, separators=(",", ":")).encode("utf-8")
        return self._perform(
            method,
            path,
            payload,
            content_type="application/json" if payload is not None else None,
            idempotency_key=idempotency_key,
        )

    def request_bytes(
        self,
        method: str,
        path: str,
        payload: bytes,
        *,
        content_type: str,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        return self._perform(method, path, payload, content_type=content_type, extra_headers=headers)

    def status(self) -> Any: return self.request("GET", "/v1/status")
    def capabilities(self) -> Any: return self.request("GET", "/v1/capabilities")
    def profiles(self) -> Any: return self.request("GET", "/v1/profiles")
    def images(self) -> Any: return self.request("GET", "/v1/images")
    def import_image(self, request: Mapping[str, Any], idempotency_key: str) -> Any:
        return self.request("POST", "/v1/image-imports", request, idempotency_key)

    def create_artifact_upload(self, request: Mapping[str, Any], idempotency_key: str) -> Any:
        return self.request("POST", "/v1/artifact-uploads", request, idempotency_key)

    def artifact_upload(self, upload_id: str) -> Any:
        return self.request("GET", f"/v1/artifact-uploads/{self._segment(upload_id)}")

    def put_artifact_chunk(self, upload_id: str, offset: int, payload: bytes, chunk_sha256: str) -> Any:
        if offset < 0:
            raise ValueError("upload offset must be non-negative")
        if not self.SHA256.fullmatch(chunk_sha256):
            raise ValueError("invalid chunk SHA-256")
        return self.request_bytes(
            "PUT",
            f"/v1/artifact-uploads/{self._segment(upload_id)}/chunks/{offset}",
            payload,
            content_type="application/octet-stream",
            headers={"Content-SHA256": chunk_sha256},
        )

    def complete_artifact_upload(self, upload_id: str) -> Any:
        return self.request("POST", f"/v1/artifact-uploads/{self._segment(upload_id)}/complete")

    def cancel_artifact_upload(self, upload_id: str) -> Any:
        return self.request("DELETE", f"/v1/artifact-uploads/{self._segment(upload_id)}")

    def upload_file(
        self,
        artifact_id: str,
        path: Path,
        *,
        expected_sha256: str | None = None,
        idempotency_key: str | None = None,
        chunk_size: int = MAX_REQUEST_BYTES,
    ) -> Any:
        if not self.ARTIFACT_ID.fullmatch(artifact_id):
            raise ValueError("invalid artifact id")
        if chunk_size <= 0 or chunk_size > self.MAX_REQUEST_BYTES:
            raise ValueError("chunk size must be in 1..1048576")
        if not path.is_file():
            raise ValueError(f"artifact file not found: {path}")
        size = path.stat().st_size
        if size <= 0 or size > 64 * 1024 * 1024 * 1024:
            raise ValueError("artifact file size is out of range")
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(self.MAX_REQUEST_BYTES), b""):
                digest.update(chunk)
        whole_sha256 = digest.hexdigest()
        if expected_sha256 is not None and expected_sha256 != whole_sha256:
            raise ValueError("artifact file digest does not match --sha256")
        identity = hashlib.sha256(f"{artifact_id}:{whole_sha256}:{size}".encode()).hexdigest()
        key = idempotency_key or f"upload-{identity}"
        upload = self.create_artifact_upload(
            {"artifactId": artifact_id, "sha256": whole_sha256, "expectedSizeBytes": size},
            key,
        )
        if not isinstance(upload, Mapping) or not isinstance(upload.get("id"), str):
            raise ApiError("Host API upload response has no id")
        upload_id = upload["id"]
        state = upload.get("state")
        if state == "CANCELLED":
            raise ApiError(f"artifact upload is cancelled: {upload_id}")
        committed = upload.get("committedBytes")
        if not isinstance(committed, int) or committed < 0 or committed > size:
            raise ApiError("Host API upload response has invalid progress")
        if state != "COMPLETED":
            with path.open("rb") as handle:
                handle.seek(committed)
                offset = committed
                while offset < size:
                    chunk = handle.read(min(chunk_size, size - offset))
                    if not chunk:
                        raise OSError("artifact file ended before expected size")
                    result = self.put_artifact_chunk(upload_id, offset, chunk, hashlib.sha256(chunk).hexdigest())
                    offset += len(chunk)
                    if not isinstance(result, Mapping) or result.get("committedBytes") != offset:
                        raise ApiError("Host API upload progress did not advance as expected")
        return self.complete_artifact_upload(upload_id)

    def vms(self) -> Any: return self.request("GET", "/v1/vms")
    def vm(self, vm_id: str) -> Any: return self.request("GET", f"/v1/vms/{self._segment(vm_id)}")
    def apply_vm(self, vm_id: str, spec: Mapping[str, Any], idempotency_key: str) -> Any:
        return self.request("PUT", f"/v1/vms/{self._segment(vm_id)}", spec, idempotency_key)
    def remove_vm(self, vm_id: str, idempotency_key: str) -> Any:
        return self.request("DELETE", f"/v1/vms/{self._segment(vm_id)}", idempotency_key=idempotency_key)
    def operations(self) -> Any: return self.request("GET", "/v1/operations")
    def operation(self, operation_id: str) -> Any:
        return self.request("GET", f"/v1/operations/{self._segment(operation_id)}")
    def cancel_operation(self, operation_id: str, idempotency_key: str) -> Any:
        return self.request("POST", f"/v1/operations/{self._segment(operation_id)}/cancel", idempotency_key=idempotency_key)
    def diagnostics(self) -> Any: return self.request("GET", "/v1/diagnostics")
    def revoke_controller(self, controller_id: str, idempotency_key: str) -> Any:
        return self.request("DELETE", f"/v1/controllers/{self._segment(controller_id)}", idempotency_key=idempotency_key)

    def wait(self, operation_id: str, timeout: float = 600.0) -> Mapping[str, Any]:
        if timeout <= 0 or timeout > 86400:
            raise ValueError("timeout must be in (0, 86400]")
        deadline = time.monotonic() + timeout
        while True:
            operation = self.operation(operation_id)
            if not isinstance(operation, Mapping):
                raise ApiError("Host API operation response is not an object")
            state = operation.get("state")
            if not isinstance(state, str):
                raise ApiError("Host API operation response has no string state")
            if state == "FAILED_RETRYABLE":
                raise RetryableOperationError(operation)
            if state in self.TERMINAL_OPERATION_STATES:
                return operation
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(operation_id)
            time.sleep(min(self.config.poll_interval_seconds, remaining))
