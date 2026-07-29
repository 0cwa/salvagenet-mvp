import unittest

from nodehost_mvp.cli import build_parser


class CliTest(unittest.TestCase):
    def test_apply_parser(self) -> None:
        args = build_parser().parse_args(
            ["--config", "c.json", "apply-vm", "default", "request.json"]
        )
        self.assertEqual(args.vm_id, "default")


if __name__ == "__main__":
    unittest.main()
