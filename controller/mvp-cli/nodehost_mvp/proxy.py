from __future__ import annotations

import select
import socket
import ssl
import sys
from urllib.parse import quote, urlparse

from .config import ControllerConfig

_MAX_CHUNK = 64 * 1024
_MAX_HEADERS = 64 * 1024


class _ChunkedReader:
    def __init__(self, sock: ssl.SSLSocket, initial: bytes):
        self.sock = sock
        self.buffer = bytearray(initial)

    def _exact(self, count: int) -> bytes:
        while len(self.buffer) < count:
            chunk = self.sock.recv(min(_MAX_CHUNK, count - len(self.buffer)))
            if not chunk:
                raise RuntimeError("recovery tunnel closed inside HTTP chunk")
            self.buffer.extend(chunk)
        result = bytes(self.buffer[:count])
        del self.buffer[:count]
        return result

    def read_chunk(self) -> bytes | None:
        while b"\r\n" not in self.buffer:
            if len(self.buffer) > 128:
                raise RuntimeError("invalid recovery tunnel chunk header")
            chunk = self.sock.recv(128)
            if not chunk:
                raise RuntimeError("recovery tunnel closed before final HTTP chunk")
            self.buffer.extend(chunk)
        line, _, rest = self.buffer.partition(b"\r\n")
        self.buffer = bytearray(rest)
        try:
            size = int(line.split(b";", 1)[0], 16)
        except ValueError:
            raise RuntimeError("invalid recovery tunnel chunk size") from None
        if size < 0 or size > _MAX_CHUNK:
            raise RuntimeError("recovery tunnel chunk exceeds 64 KiB")
        if size == 0:
            return None
        data = self._exact(size)
        if self._exact(2) != b"\r\n":
            raise RuntimeError("invalid recovery tunnel chunk terminator")
        return data


def proxy_ssh(config: ControllerConfig, vm_id: str) -> int:
    """Bridge stdin/stdout only to the authenticated VM-scoped recovery endpoint."""
    parsed = urlparse(config.endpoint)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("controller endpoint must be HTTPS and include a hostname")
    if not vm_id or len(vm_id) > 63:
        raise ValueError("VM identifier must contain 1..63 characters")

    raw: socket.socket | None = None
    sock: ssl.SSLSocket | None = None
    try:
        raw = socket.create_connection(
            (parsed.hostname, parsed.port or 443),
            timeout=config.request_timeout_seconds,
        )
        context = (
            ssl.create_default_context(cafile=config.ca_file)
            if config.ca_file
            else ssl.create_default_context()
        )
        sock = context.wrap_socket(raw, server_hostname=parsed.hostname)
        raw = None  # Ownership transferred to SSLSocket.
        path_id = quote(vm_id, safe="")
        request = (
            f"CONNECT /v1/vms/{path_id}/ssh HTTP/1.1\r\n"
            f"Host: {parsed.netloc}\r\n"
            f"Authorization: Bearer {config.capability}\r\n"
            "Transfer-Encoding: chunked\r\n"
            "Connection: keep-alive\r\n\r\n"
        ).encode("ascii")
        sock.sendall(request)

        response = bytearray()
        while b"\r\n\r\n" not in response:
            chunk = sock.recv(4096)
            if not chunk:
                raise RuntimeError("recovery tunnel closed during handshake")
            response.extend(chunk)
            if len(response) > _MAX_HEADERS:
                raise RuntimeError("oversized recovery tunnel response headers")

        head, remaining = bytes(response).split(b"\r\n\r\n", 1)
        lines = head.split(b"\r\n")
        status_parts = lines[0].split(b" ", 2) if lines else []
        if len(status_parts) < 2 or status_parts[1] != b"200":
            status = status_parts[1].decode("ascii", "replace") if len(status_parts) > 1 else "invalid"
            raise RuntimeError(f"recovery tunnel rejected with HTTP {status}")
        headers: dict[bytes, bytes] = {}
        for line in lines[1:]:
            name, separator, value = line.partition(b":")
            if not separator:
                raise RuntimeError("invalid recovery tunnel response header")
            headers[name.strip().lower()] = value.strip().lower()
        chunked = b"chunked" in headers.get(b"transfer-encoding", b"")
        reader = _ChunkedReader(sock, remaining) if chunked else None

        stdin = sys.stdin.buffer
        stdout = sys.stdout.buffer
        stdin_open = True
        sock.settimeout(None)
        while True:
            watch: list[object] = [sock]
            if stdin_open:
                watch.append(stdin)
            ready, _, _ = select.select(watch, [], [])
            if sock in ready:
                data = reader.read_chunk() if reader else sock.recv(_MAX_CHUNK)
                if data is None or data == b"":
                    return 0
                stdout.write(data)
                stdout.flush()
            if stdin_open and stdin in ready:
                data = stdin.read1(_MAX_CHUNK)
                if not data:
                    stdin_open = False
                    sock.sendall(b"0\r\n\r\n")
                else:
                    sock.sendall(f"{len(data):x}\r\n".encode("ascii") + data + b"\r\n")
    finally:
        if sock is not None:
            sock.close()
        elif raw is not None:
            raw.close()
