from __future__ import annotations

import unittest

from nodehost_mvp.proxy import _ChunkedReader


class _Socket:
    def __init__(self, chunks: list[bytes]): self.chunks = chunks
    def recv(self, _count: int) -> bytes: return self.chunks.pop(0) if self.chunks else b""


class ProxyTest(unittest.TestCase):
    def test_decodes_bounded_http_chunks(self) -> None:
        reader = _ChunkedReader(_Socket([b"llo\r\n0\r\n\r\n"]), b"5\r\nhe")  # type: ignore[arg-type]
        self.assertEqual(reader.read_chunk(), b"hello")
        self.assertIsNone(reader.read_chunk())

    def test_rejects_oversized_chunk(self) -> None:
        reader = _ChunkedReader(_Socket([]), b"10001\r\n")  # type: ignore[arg-type]
        with self.assertRaisesRegex(RuntimeError, "64 KiB"): reader.read_chunk()


if __name__ == "__main__": unittest.main()
