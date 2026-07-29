from __future__ import annotations

import unittest

from nodehost_mvp.client import NodeHostClient


class ClientTest(unittest.TestCase):
    def test_path_segment_is_escaped(self) -> None:
        self.assertEqual(NodeHostClient._segment("vm/default"), "vm%2Fdefault")

    def test_empty_segment_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            NodeHostClient._segment("")


if __name__ == "__main__":
    unittest.main()
