from __future__ import annotations

import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nodehost_mvp.client import ApiError, NodeHostClient, RetryableOperationError
from nodehost_mvp.config import ControllerConfig


class _Response:
    def __init__(self, data: bytes):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, count: int = -1) -> bytes:
        return self.data[:count]


class ClientTest(unittest.TestCase):
    def setUp(self) -> None:
        self.capability = "secret-controller-capability-value"
        self.client = NodeHostClient(
            ControllerConfig("https://node.invalid", self.capability, None)
        )

    def test_path_segment_is_escaped(self) -> None:
        self.assertEqual(NodeHostClient._segment("vm/default"), "vm%2Fdefault")

    def test_empty_and_oversized_segments_are_rejected(self) -> None:
        for value in ("", "x" * 129):
            with self.assertRaises(ValueError):
                NodeHostClient._segment(value)

    @mock.patch("urllib.request.urlopen")
    def test_all_mutation_headers_are_sent(self, urlopen: mock.Mock) -> None:
        urlopen.return_value = _Response(b'{"id":"op-1"}')
        result = self.client.remove_vm("default", "0123456789abcdef")
        request = urlopen.call_args.args[0]
        self.assertEqual(result["id"], "op-1")
        self.assertEqual(request.get_header("Idempotency-key"), "0123456789abcdef")
        self.assertEqual(
            request.get_header("Authorization"), f"Bearer {self.capability}"
        )

    @mock.patch("urllib.request.urlopen")
    def test_chunk_request_sends_raw_bytes_and_digest(self, urlopen: mock.Mock) -> None:
        urlopen.return_value = _Response(b'{"committedBytes":3}')
        result = self.client.put_artifact_chunk(
            "upload-abc",
            0,
            b"abc",
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )
        request = urlopen.call_args.args[0]
        self.assertEqual(3, result["committedBytes"])
        self.assertEqual(b"abc", request.data)
        self.assertEqual("application/octet-stream", request.get_header("Content-type"))
        self.assertEqual(
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            request.get_header("Content-sha256"),
        )

    def test_upload_file_resumes_from_host_progress(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image"
            contents = b"abcdefgh"
            path.write_bytes(contents)
            digest = hashlib.sha256(contents).hexdigest()
            create = {
                "id": "upload-abc",
                "artifactId": "image",
                "sha256": digest,
                "expectedSizeBytes": 8,
                "state": "OPEN",
                "committedBytes": 3,
            }

            def chunk_response(_id: str, offset: int, payload: bytes, _sha: str):
                return {
                    **create,
                    "committedBytes": offset + len(payload),
                }

            complete_response = {"id": "image", "sha256": digest, "sizeBytes": 8}
            with (
                mock.patch.object(
                    self.client, "create_artifact_upload", return_value=create
                ),
                mock.patch.object(
                    self.client, "put_artifact_chunk", side_effect=chunk_response
                ) as chunks,
                mock.patch.object(
                    self.client,
                    "complete_artifact_upload",
                    return_value=complete_response,
                ) as complete,
            ):
                result = self.client.upload_file("image", path, chunk_size=2)

            self.assertEqual(complete_response, result)
            self.assertEqual([3, 5, 7], [call.args[1] for call in chunks.call_args_list])
            complete.assert_called_once_with("upload-abc")

    def test_upload_rejects_changed_host_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image"
            contents = b"abcdefgh"
            path.write_bytes(contents)
            digest = hashlib.sha256(contents).hexdigest()
            create = {
                "id": "upload-abc",
                "artifactId": "other-image",
                "sha256": digest,
                "expectedSizeBytes": 8,
                "state": "OPEN",
                "committedBytes": 0,
            }
            with mock.patch.object(
                self.client, "create_artifact_upload", return_value=create
            ):
                with self.assertRaisesRegex(ApiError, "artifact identity"):
                    self.client.upload_file("image", path)

    def test_upload_rejects_changed_completion_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image"
            contents = b"abcdefgh"
            path.write_bytes(contents)
            digest = hashlib.sha256(contents).hexdigest()
            create = {
                "id": "upload-abc",
                "artifactId": "image",
                "sha256": digest,
                "expectedSizeBytes": 8,
                "state": "COMPLETED",
                "committedBytes": 8,
            }
            complete = {"id": "image", "sha256": "0" * 64, "sizeBytes": 8}
            with (
                mock.patch.object(
                    self.client, "create_artifact_upload", return_value=create
                ),
                mock.patch.object(
                    self.client, "complete_artifact_upload", return_value=complete
                ),
            ):
                with self.assertRaisesRegex(ApiError, "artifact digest"):
                    self.client.upload_file("image", path)

    def test_upload_rejects_invalid_expected_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image"
            path.write_bytes(b"abcdefgh")
            with self.assertRaisesRegex(ValueError, "invalid expected"):
                self.client.upload_file("image", path, expected_sha256="bad")

    @mock.patch("urllib.request.urlopen")
    def test_oversized_response_is_rejected(self, urlopen: mock.Mock) -> None:
        urlopen.return_value = _Response(b"x" * (NodeHostClient.MAX_RESPONSE_BYTES + 1))
        with self.assertRaisesRegex(ApiError, "exceeds"):
            self.client.status()

    @mock.patch("urllib.request.urlopen")
    def test_http_error_redacts_reflected_capability(self, urlopen: mock.Mock) -> None:
        urlopen.side_effect = urllib.error.HTTPError(
            "https://node.invalid/v1/status",
            401,
            "no",
            {},
            io.BytesIO(self.capability.encode()),
        )
        with self.assertRaises(ApiError) as caught:
            self.client.status()
        self.assertNotIn(self.capability, str(caught.exception))
        self.assertIn("[REDACTED]", str(caught.exception))

    @mock.patch("urllib.request.urlopen")
    def test_http_error_redacts_reflected_idempotency_key(
        self, urlopen: mock.Mock
    ) -> None:
        key = "private-idempotency-key"
        urlopen.side_effect = urllib.error.HTTPError(
            "https://node.invalid/v1/artifact-uploads",
            409,
            "no",
            {},
            io.BytesIO(key.encode()),
        )
        with self.assertRaises(ApiError) as caught:
            self.client.create_artifact_upload({}, key)
        self.assertNotIn(key, str(caught.exception))
        self.assertIn("[REDACTED]", str(caught.exception))

    def test_wait_reports_failed_retryable_without_timing_out(self) -> None:
        operation = {
            "id": "op-1",
            "state": "FAILED_RETRYABLE",
            "errorCode": "NETWORK_UNAVAILABLE",
        }
        with mock.patch.object(self.client, "operation", return_value=operation):
            with self.assertRaises(RetryableOperationError) as caught:
                self.client.wait("op-1", timeout=600)
        self.assertIs(caught.exception.operation, operation)

    def test_rejects_oversized_request_and_short_key(self) -> None:
        with self.assertRaisesRegex(ValueError, "1 MiB"):
            self.client.request(
                "POST", "/v1/image-imports", {"x": "y" * 1024 * 1024}
            )
        with self.assertRaisesRegex(ValueError, "16..200"):
            self.client.remove_vm("default", "short")


if __name__ == "__main__":
    unittest.main()
