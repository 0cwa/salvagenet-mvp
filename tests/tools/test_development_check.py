import importlib.util, sys, unittest
from pathlib import Path
MODULE=Path(__file__).resolve().parents[2]/'tools/development/check.py'; spec=importlib.util.spec_from_file_location('development_check',MODULE); m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m)
class DevelopmentCheckTest(unittest.TestCase):
    def test_quick_plan_has_required_checks(self): self.assertEqual(['validate','guest'],[c.name for c in m.plan('quick')])
    def test_full_plan_reports_gradle_as_optional(self): self.assertFalse({c.name:c for c in m.plan('full')}['jvm'].required)
    def test_qemu_plan_is_optional(self): self.assertFalse(next(c for c in m.plan('quick',True) if c.name=='qemu-lab').required)
if __name__=='__main__': unittest.main()
