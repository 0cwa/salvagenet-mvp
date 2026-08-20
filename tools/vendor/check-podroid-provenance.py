#!/usr/bin/env python3
"""Verify that Podroid lock provenance fields describe the pinned upstream commit."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK_PATH = ROOT / "android" / "upstream" / "podroid.lock"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
RELEASE_RE = re.compile(r"^v[0-9A-Za-z][0-9A-Za-z._-]{0,63}$")


class ProvenanceError(RuntimeError):
    """A deterministic upstream provenance failure."""


def run(*args: str, cwd: Path) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise ProvenanceError(
            f"git {' '.join(args)} failed ({completed.returncode})"
            + (f"\n{detail}" if detail else "")
        )
    return completed.stdout.strip()


def main() -> int:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    repository = lock.get("repository")
    commit = lock.get("commit")
    release = lock.get("release")
    expected_subject = lock.get("verifiedCommitMessage")
    if (
        not isinstance(repository, str)
        or not repository.startswith("https://github.com/")
        or not repository.endswith(".git")
    ):
        raise ProvenanceError("repository must be an explicit HTTPS GitHub clone URL")
    if not isinstance(commit, str) or COMMIT_RE.fullmatch(commit) is None:
        raise ProvenanceError("commit must be a full lowercase SHA")
    if not isinstance(release, str) or RELEASE_RE.fullmatch(release) is None:
        raise ProvenanceError("release must be a normalized v-prefixed tag")
    if not isinstance(expected_subject, str) or not expected_subject.strip():
        raise ProvenanceError("verifiedCommitMessage must be non-empty")

    with tempfile.TemporaryDirectory(prefix="salvagenet-podroid-provenance-") as temporary:
        checkout = Path(temporary)
        run("init", "--quiet", cwd=checkout)
        run("fetch", "--quiet", "--depth=1", "--no-tags", repository, commit, cwd=checkout)
        resolved_commit = run("rev-parse", "FETCH_HEAD^{commit}", cwd=checkout)
        actual_subject = run("show", "-s", "--format=%s", "FETCH_HEAD", cwd=checkout)
        run(
            "fetch",
            "--quiet",
            "--depth=1",
            "--no-tags",
            repository,
            f"refs/tags/{release}:refs/tags/{release}",
            cwd=checkout,
        )
        release_commit = run("rev-parse", f"refs/tags/{release}^{{commit}}", cwd=checkout)

    if resolved_commit != commit:
        raise ProvenanceError(f"upstream resolved to {resolved_commit}, expected {commit}")
    if release_commit != commit:
        raise ProvenanceError(f"release {release} points to {release_commit}, expected {commit}")
    if actual_subject != expected_subject:
        raise ProvenanceError(
            "verified commit subject differs: "
            f"expected {expected_subject!r}, got {actual_subject!r}"
        )
    print(f"Podroid provenance: OK ({release} -> {commit}, {actual_subject})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, json.JSONDecodeError, ProvenanceError) as error:
        print(f"Podroid provenance failed: {error}", file=sys.stderr)
        raise SystemExit(1)
