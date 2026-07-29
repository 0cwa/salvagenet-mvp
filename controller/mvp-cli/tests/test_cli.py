from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from nodehost_mvp.cli import _load_json_object, build_parser


class CliTest(unittest.TestCase):
    def test_all_openapi_operations_have_commands(self) -> None:
        cases = {
            "status": ["status"], "capabilities": ["capabilities"],
            "profiles": ["profiles"], "images": ["images"],
            "import-image": ["import-image", "request.json"],
            "vms": ["vms"], "get-vm": ["get-vm", "default"],
            "apply-vm": ["apply-vm", "default", "request.json"],
            "remove-vm": ["remove-vm", "default"], "operations": ["operations"],
            "operation": ["operation", "op-1"],
            "cancel-operation": ["cancel-operation", "op-1"],
            "diagnostics": ["diagnostics"],
            "revoke-controller": ["revoke-controller", "controller-1"],
            "proxy-ssh": ["proxy-ssh", "default"],
        }
        for expected, arguments in cases.items():
            with self.subTest(expected):
                args = build_parser().parse_args(arguments)
                self.assertEqual(args.command, expected)

    def test_request_file_must_be_bounded_object(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "object"): _load_json_object(str(path))
            path.write_text(json.dumps({"value": "x" * 1024 * 1024}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "1 MiB"): _load_json_object(str(path))


if __name__ == "__main__": unittest.main()
