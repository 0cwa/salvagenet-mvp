import subprocess, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class ContextPackTest(unittest.TestCase):
    def test_t01_pack(self):
        p=subprocess.run(["python3","tools/agents/context-pack.py","T01"],cwd=ROOT,text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
        text=(ROOT/".local/context/T01.md").read_text()
        self.assertIn("GOAL.md",text); self.assertNotIn("lab/headscale/secrets",text)
if __name__=='__main__': unittest.main()
