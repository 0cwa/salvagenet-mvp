from __future__ import annotations

import select
import socket
import ssl
import sys
from urllib.parse import urlparse

from .config import ControllerConfig


def proxy_ssh(config: ControllerConfig, vm_id: str) -> int:
    """Bridge stdin/stdout to the MVP HTTP CONNECT-like recovery endpoint."""
    parsed = urlparse(config.endpoint)
    if not parsed.hostname:
        raise ValueError("controller endpoint must include a hostname")

    raw = socket.create_connection((parsed.hostname, parsed.port or 443), timeout=30)
    context = (
        ssl.create_default_context(cafile=config.ca_file)
        if config.ca_file
        else ssl.create_default_context()
    )
    sock = context.wrap_socket(raw, server_hostname=parsed.hostname)
    request = (
        f"CONNECT /v1/vms/{vm_id}/ssh HTTP/1.1\r\n"
        f"Host: {parsed.netloc}\r\n"
        f"Authorization: Bearer {config.capability}\r\n"
        "Connection: keep-alive\r\n"
        "\r\n"
    ).encode()
    sock.sendall(request)

    response = b""
    while b"\r\n\r\n" not in response:
        chunk = sock.recv(4096)
        if not chunk:
            raise RuntimeError("tunnel closed during handshake")
        response += chunk
        if len(response) > 65536:
            raise RuntimeError("oversized tunnel response")

    head, remaining = response.split(b"\r\n\r\n", 1)
    status_line = head.splitlines()[0] if head else b""
    if b" 200 " not in status_line:
        raise RuntimeError(f"recovery tunnel rejected: {status_line!r}")

    if remaining:
        sys.stdout.buffer.write(remaining)
        sys.stdout.buffer.flush()

    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    stdin_open = True
    while True:
        watch = [sock]
        if stdin_open:
            watch.append(stdin)
        ready, _, _ = select.select(watch, [], [])
        if sock in ready:
            data = sock.recv(65536)
            if not data:
                return 0
            stdout.write(data)
            stdout.flush()
        if stdin_open and stdin in ready:
            data = stdin.read1(65536)
            if not data:
                stdin_open = False
                sock.shutdown(socket.SHUT_WR)
            else:
                sock.sendall(data)
