import importlib.util, unittest
from pathlib import Path
MODULE=Path(__file__).resolve().parents[2]/'lab/qemu/scripts/report.py'; spec=importlib.util.spec_from_file_location('qemu_report',MODULE); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
class ReportTest(unittest.TestCase):
    def test_sha_missing_is_none(self): self.assertIsNone(m.sha(Path('/definitely/missing')))
    def test_qmp_missing_is_bounded(self): self.assertEqual({'connected':False,'status':None},m.qmp_status(Path('/definitely/missing')))
if __name__=='__main__': unittest.main()
