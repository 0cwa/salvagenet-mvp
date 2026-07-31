import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ContextPackTest(unittest.TestCase):
    def test_t01_pack(self):
        process = subprocess.run(
            ["python3", "tools/agents/context-pack.py", "T01"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        text = (ROOT / ".local/context/T01.md").read_text()
        self.assertIn("docs/product/north-star.md", text)
        self.assertIn("GOAL.md", text)
        self.assertIn("AGENTS.md", text)
        self.assertLess(
            text.index("docs/product/north-star.md"),
            text.index("GOAL.md"),
        )
        self.assertNotIn("lab/headscale/secrets", text)


if __name__ == "__main__":
    unittest.main()
