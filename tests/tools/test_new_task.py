import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[2] / "tools/agents/new-task.py"
spec = importlib.util.spec_from_file_location("new_task", MODULE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Args:
    id = "F99"
    slug = "sample-task"
    name = "Sample task"
    outcome = "Outcome"
    group = 9
    depends_on = []
    allowed_path = ["sample/**"]
    context = []
    acceptance = ["It works."]
    mvp_plus = False
    activate = False


class NewTaskTest(unittest.TestCase):
    def test_rejects_bad_id(self):
        args = Args()
        args.id = "bad"
        with self.assertRaises(ValueError):
            m.build(args)

    def test_rejects_missing_paths(self):
        args = Args()
        args.allowed_path = []
        with self.assertRaises(ValueError):
            m.build(args)

    def test_rejects_missing_acceptance(self):
        args = Args()
        args.acceptance = []
        with self.assertRaises(ValueError):
            m.build(args)

    def test_new_task_is_queued_by_default(self):
        args = Args()
        _task, dag, registry, packet = m.build(args)
        self.assertNotIn("F99", {item["id"] for item in dag["tasks"]})
        created = next(item for item in registry["tasks"] if item["id"] == "F99")
        self.assertEqual("QUEUED_REVIEW", created["status"])
        self.assertIn("Phase-start review", packet)

    def test_explicit_activation_adds_task_to_dag(self):
        args = Args()
        args.activate = True
        task, dag, registry, _packet = m.build(args)
        self.assertEqual("F99", task)
        self.assertEqual("F99", dag["tasks"][-1]["id"])
        self.assertEqual("PLANNED", registry["cycleStatus"]["F99"])

    def test_allows_base_mvp_dependency_sentinel_when_activated(self):
        args = Args()
        args.depends_on = ["BASE_MVP_PASS"]
        args.mvp_plus = True
        args.activate = True
        task, dag, _registry, _packet = m.build(args)
        self.assertEqual("F99", task)
        self.assertEqual(["BASE_MVP_PASS"], dag["tasks"][-1]["dependsOn"])


if __name__ == "__main__":
    unittest.main()
