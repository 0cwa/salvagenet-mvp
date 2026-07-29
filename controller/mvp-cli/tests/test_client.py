from __future__ import annotations

import io
import json
import unittest
from unittest import mock
import urllib.error

from nodehost_mvp.client import ApiError, NodeHostClient
from nodehost_mvp.config import ControllerConfig


class _Response:
    def __init__(self, data: bytes): self.data = data
    def __enter__(self): return self
    def __exit__(self, *_args): return None
    def read(self, count: int = -1) -> bytes: return self.data[:count]


class ClientTest(unittest.TestCase):
    def setUp(self) -> None:
        self.capability = "secret-controller-capability-value"
        self.client = NodeHostClient(ControllerConfig("https://node.invalid", self.capability, None))

    def test_path_segment_is_escaped(self) -> None:
        self.assertEqual(NodeHostClient._segment("vm/default"), "vm%2Fdefault")

    def test_empty_and_oversized_segments_are_rejected(self) -> None:
        for value in ("", "x" * 129):
            with self.assertRaises(ValueError): NodeHostClient._segment(value)

    @mock.patch("urllib.request.urlopen")
    def test_all_mutation_headers_are_sent(self, urlopen: mock.Mock) -> None:
        urlopen.return_value = _Response(b'{"id":"op-1"}')
        result = self.client.remove_vm("default", "0123456789abcdef")
        request = urlopen.call_args.args[0]
        self.assertEqual(result["id"], "op-1")
        self.assertEqual(request.get_header("Idempotency-key"), "0123456789abcdef")
        self.assertEqual(request.get_header("Authorization"), f"Bearer {self.capability}")

    @mock.patch("urllib.request.urlopen")
    def test_oversized_response_is_rejected(self, urlopen: mock.Mock) -> None:
        urlopen.return_value = _Response(b"x" * (NodeHostClient.MAX_RESPONSE_BYTES + 1))
        with self.assertRaisesRegex(ApiError, "exceeds"): self.client.status()

    @mock.patch("urllib.request.urlopen")
    def test_http_error_redacts_reflected_capability(self, urlopen: mock.Mock) -> None:
        urlopen.side_effect = urllib.error.HTTPError(
            "https://node.invalid/v1/status", 401, "no", {}, io.BytesIO(self.capability.encode())
        )
        with self.assertRaises(ApiError) as caught: self.client.status()
        self.assertNotIn(self.capability, str(caught.exception))
        self.assertIn("[REDACTED]", str(caught.exception))

    def test_rejects_oversized_request_and_short_key(self) -> None:
        with self.assertRaisesRegex(ValueError, "1 MiB"):
            self.client.request("POST", "/v1/image-imports", {"x": "y" * 1024 * 1024})
        with self.assertRaisesRegex(ValueError, "16..200"):
            self.client.remove_vm("default", "short")


if __name__ == "__main__": unittest.main()
