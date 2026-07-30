import importlib.util, unittest
from pathlib import Path
MODULE=Path(__file__).resolve().parents[2]/'tools/agents/new-task.py'; spec=importlib.util.spec_from_file_location('new_task',MODULE); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
class Args:
    id='H99'; slug='sample-task'; name='Sample task'; outcome='Outcome'; group=9; depends_on=[]; allowed_path=['sample/**']; context=[]; acceptance=['It works.']; mvp_plus=False
class NewTaskTest(unittest.TestCase):
    def test_rejects_bad_id(self):
        a=Args(); a.id='bad'
        with self.assertRaises(ValueError): m.build(a)
    def test_rejects_missing_paths(self):
        a=Args(); a.allowed_path=[]
        with self.assertRaises(ValueError): m.build(a)
    def test_rejects_missing_acceptance(self):
        a=Args(); a.acceptance=[]
        with self.assertRaises(ValueError): m.build(a)
    def test_allows_base_mvp_dependency_sentinel(self):
        a=Args(); a.depends_on=['BASE_MVP_PASS']; a.mvp_plus=True
        task, dag, _registry, _packet = m.build(a)
        self.assertEqual('H99', task)
        self.assertEqual(['BASE_MVP_PASS'], dag['tasks'][-1]['dependsOn'])
if __name__=='__main__': unittest.main()
