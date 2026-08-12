#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 <git-range> | $0 <base> <head>" >&2
  exit 2
}

fail() {
  echo "report.sh: $*" >&2
  exit 2
}

case $# in
  1)
    range=$1
    [[ -n $range ]] || fail "the Git range must not be empty"
    [[ $range != -* ]] || fail "the Git range must be explicit and must not begin with '-'"
    ;;
  2)
    [[ -n $1 && -n $2 ]] || fail "the base and head must not be empty"
    [[ $1 != -* && $2 != -* ]] || fail "the base and head must not begin with '-'"
    range="$1..$2"
    ;;
  *)
    usage
    ;;
esac

repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || \
  fail "could not locate the Git repository"

exec python3 - "$repo_root" "$range" <<'PY'
import json
import subprocess
import sys


REQUIRED_TRAILERS = (
    "Agent-Model",
    "Agent-Reasoning",
    "Agent-Run-ID",
    "Agent-Task-ID",
    "Agent-Mode",
)
MAX_COMMITS = 256
MAX_FILES_PER_COMMIT = 2000
MAX_TEXT_BYTES = 4096
MAX_REPORT_BYTES = 8 * 1024 * 1024


class ReportError(Exception):
    pass


def git(repo, *args, input_bytes=None):
    completed = subprocess.run(
        ["git", "-C", repo, *args],
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        detail = completed.stderr.decode("utf-8", "replace").strip().replace("\n", " ")
        raise ReportError(detail or "Git command failed")
    return completed.stdout


def parse_trailers(repo, sha):
    message = git(repo, "show", "--no-patch", "--format=%B", sha, "--")
    parsed = git(repo, "interpret-trailers", "--parse", input_bytes=message)
    values = {name: [] for name in REQUIRED_TRAILERS}
    canonical = {name.casefold(): name for name in REQUIRED_TRAILERS}

    for line in parsed.decode("utf-8", "surrogateescape").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        name = canonical.get(key.strip().casefold())
        if name is not None:
            value = value.strip()
            if len(value.encode("utf-8", "surrogateescape")) > MAX_TEXT_BYTES:
                raise ReportError(
                    f"commit {sha}: trailer {name} exceeds the {MAX_TEXT_BYTES}-byte limit"
                )
            values[name].append(value)

    for name in REQUIRED_TRAILERS:
        if not values[name] or any(not value for value in values[name]):
            raise ReportError(f"commit {sha}: missing required trailer {name}")
    return values


def changed_files(repo, sha):
    paths = git(
        repo,
        "diff-tree",
        "--root",
        "--no-commit-id",
        "--name-only",
        "--no-renames",
        "--no-ext-diff",
        "--no-textconv",
        "-r",
        "-z",
        sha,
        "--",
    )
    raw_files = [path for path in paths.split(b"\0") if path]
    files = [path.decode("utf-8", "surrogateescape") for path in sorted(raw_files)]
    if len(files) > MAX_FILES_PER_COMMIT:
        raise ReportError(
            f"commit {sha}: changed-file limit exceeded ({len(files)} > {MAX_FILES_PER_COMMIT})"
        )
    for path in raw_files:
        if len(path) > MAX_TEXT_BYTES:
            raise ReportError(
                f"commit {sha}: changed path exceeds the {MAX_TEXT_BYTES}-byte limit"
            )
    return files


def main(repo, range_spec):
    try:
        commit_bytes = git(
            repo,
            "rev-list",
            "--reverse",
            "--topo-order",
            "--full-history",
            range_spec,
            "--",
        )
        commits = []
        for sha_bytes in commit_bytes.splitlines():
            if len(commits) >= MAX_COMMITS:
                raise ReportError(f"commit limit exceeded ({MAX_COMMITS})")
            sha = sha_bytes.decode("ascii")
            subject = git(repo, "show", "--no-patch", "--format=%s", sha, "--").decode(
                "utf-8", "surrogateescape"
            ).rstrip("\n")
            if len(subject.encode("utf-8", "surrogateescape")) > MAX_TEXT_BYTES:
                raise ReportError(
                    f"commit {sha}: subject exceeds the {MAX_TEXT_BYTES}-byte limit"
                )
            trailers = parse_trailers(repo, sha)
            commits.append(
                {
                    "sha": sha,
                    "subject": subject,
                    "Agent-Model": trailers["Agent-Model"],
                    "Agent-Reasoning": trailers["Agent-Reasoning"],
                    "Agent-Run-ID": trailers["Agent-Run-ID"],
                    "Agent-Task-ID": trailers["Agent-Task-ID"],
                    "Agent-Mode": trailers["Agent-Mode"],
                    "changedFiles": changed_files(repo, sha),
                }
            )
    except (ReportError, UnicodeDecodeError) as error:
        print(f"report.sh: {error}", file=sys.stderr)
        return 2

    report = {
        "schemaVersion": 1,
        "range": range_spec,
        "commits": commits,
    }
    encoded = json.dumps(report, ensure_ascii=True, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > MAX_REPORT_BYTES:
        print(
            f"report.sh: report exceeds the {MAX_REPORT_BYTES}-byte limit",
            file=sys.stderr,
        )
        return 2
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
PY
