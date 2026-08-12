from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "tools" / "provenance" / "report.sh"
COMMIT_HELPER = ROOT / "tools" / "provenance" / "commit-agent.sh"


def run_git(repo: Path, *args: str, input_text: str | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout.strip()


def commit(repo: Path, subject: str, body: str, filename: str, content: str) -> str:
    (repo / filename).write_text(content, encoding="utf-8")
    run_git(repo, "add", filename)
    message = f"{subject}\n\n{body}\n"
    run_git(repo, "commit", "-F", "-", input_text=message)
    return run_git(repo, "rev-parse", "HEAD")


def metadata(
    *,
    model: str = "model-a",
    reasoning: str = "high",
    run_id: str = "run-1",
    task: str = "P01",
    mode: str = "goal",
) -> str:
    return "\n".join(
        [
            f"Agent-Model: {model}",
            f"Agent-Reasoning: {reasoning}",
            f"Agent-Run-ID: {run_id}",
            f"Agent-Task-ID: {task}",
            f"Agent-Mode: {mode}",
        ]
    )


class ProvenanceReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        run_git(self.repo, "init", "-q")
        run_git(self.repo, "config", "user.name", "Provenance Test")
        run_git(self.repo, "config", "user.email", "provenance@example.invalid")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def report(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(REPORT), *args],
            cwd=self.repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def commit_helper(self, *, reasoning: str | None) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                "AGENT_MODEL": "model-a",
                "AGENT_RUN_ID": "run-helper",
                "AGENT_TASK_ID": "P01",
                "AGENT_MODE": "goal",
            }
        )
        if reasoning is not None:
            environment["AGENT_REASONING"] = reasoning
        else:
            environment.pop("AGENT_REASONING", None)
        return subprocess.run(
            [str(COMMIT_HELPER), "helper commit"],
            cwd=self.repo,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_exact_range_and_deterministic_order(self) -> None:
        first = commit(self.repo, "first", metadata(run_id="run-1"), "one.txt", "one")
        second = commit(self.repo, "second", metadata(run_id="run-2"), "two.txt", "two")

        result = self.report(first, second)
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["range"], f"{first}..{second}")
        self.assertEqual([item["subject"] for item in document["commits"]], ["second"])
        self.assertEqual(document["commits"][0]["Agent-Run-ID"], ["run-2"])
        self.assertEqual(document["commits"][0]["changedFiles"], ["two.txt"])

        repeated = self.report(f"{first}..{second}")
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(repeated.stdout, result.stdout)

    def test_only_the_supplied_range_is_read(self) -> None:
        outside = commit(self.repo, "outside range", "", "outside.txt", "outside")
        target = commit(self.repo, "target", metadata(), "target.txt", "target")

        result = self.report(outside, target)
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual([item["subject"] for item in document["commits"]], ["target"])

    def test_changed_files_are_sorted_deterministically(self) -> None:
        base = commit(self.repo, "base", metadata(), "base.txt", "base")
        (self.repo / "z.txt").write_text("z", encoding="utf-8")
        (self.repo / "a.txt").write_text("a", encoding="utf-8")
        run_git(self.repo, "add", "z.txt", "a.txt")
        run_git(
            self.repo,
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-F",
            "-",
            input_text=f"paths\n\n{metadata()}\n",
        )
        target = run_git(self.repo, "rev-parse", "HEAD")

        result = self.report(base, target)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout)["commits"][0]["changedFiles"], ["a.txt", "z.txt"]
        )

    def test_missing_metadata_fails_loudly(self) -> None:
        first = commit(self.repo, "first", metadata(), "one.txt", "one")
        second = commit(
            self.repo,
            "missing reasoning",
            "\n".join(
                [
                    "Agent-Model: model-a",
                    "Agent-Run-ID: run-2",
                    "Agent-Task-ID: P01",
                    "Agent-Mode: goal",
                ]
            ),
            "two.txt",
            "two",
        )

        result = self.report(first, second)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Agent-Reasoning", result.stderr)

    def test_repeated_trailer_values_are_explicit(self) -> None:
        base = commit(self.repo, "base", metadata(), "base.txt", "base")
        target = commit(
            self.repo,
            "repeated model",
            "\n".join(
                [
                    "Agent-Model: model-a",
                    "Agent-Model: model-b",
                    "Agent-Reasoning: unknown",
                    "Agent-Reasoning: declared",
                    "Agent-Run-ID: run-1",
                    "Agent-Task-ID: P01",
                    "Agent-Mode: goal",
                ]
            ),
            "one.txt",
            "one",
        )

        result = self.report(base, target)
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["commits"][0]["Agent-Model"], ["model-a", "model-b"])
        self.assertEqual(
            document["commits"][0]["Agent-Reasoning"], ["unknown", "declared"]
        )

    def test_blank_metadata_fails_loudly(self) -> None:
        base = commit(self.repo, "base", metadata(), "base.txt", "base")
        target = commit(
            self.repo,
            "blank model",
            "\n".join(
                [
                    "Agent-Model:",
                    "Agent-Reasoning: declared",
                    "Agent-Run-ID: run-2",
                    "Agent-Task-ID: P01",
                    "Agent-Mode: goal",
                ]
            ),
            "one.txt",
            "one",
        )

        result = self.report(base, target)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Agent-Model", result.stderr)

    def test_not_applicable_is_valid(self) -> None:
        base = commit(self.repo, "base", metadata(), "base.txt", "base")
        target = commit(
            self.repo,
            "human review",
            metadata(model="human", reasoning="not-applicable", mode="human-review"),
            "one.txt",
            "one",
        )

        result = self.report(base, target)
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["commits"][0]["Agent-Reasoning"], ["not-applicable"])

    def test_requires_an_explicit_range(self) -> None:
        result = subprocess.run(
            [str(REPORT)],
            cwd=self.repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage:", result.stderr)

    def test_rejects_empty_or_option_like_base_and_head(self) -> None:
        empty_base = self.report("", "HEAD")
        self.assertEqual(empty_base.returncode, 2)
        self.assertIn("must not be empty", empty_base.stderr)

        option_head = self.report("HEAD", "--all")
        self.assertEqual(option_head.returncode, 2)
        self.assertIn("must not begin with '-'", option_head.stderr)

    def test_commit_helper_requires_and_writes_reasoning(self) -> None:
        (self.repo / "helper.txt").write_text("helper", encoding="utf-8")
        run_git(self.repo, "add", "helper.txt")
        missing = self.commit_helper(reasoning=None)
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("AGENT_REASONING", missing.stderr)
        self.assertEqual(run_git(self.repo, "rev-list", "--all", "--count"), "0")

        present = self.commit_helper(reasoning="high")
        self.assertEqual(present.returncode, 0, present.stderr)
        message = run_git(self.repo, "log", "-1", "--format=%B")
        self.assertIn("Agent-Reasoning: high", message)


if __name__ == "__main__":
    unittest.main()
