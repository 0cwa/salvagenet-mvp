#!/usr/bin/env python3
"""Import, update, diff, and verify the pinned Podroid source subtree."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterator

ROOT = Path(__file__).resolve().parents[2]
LOCK_PATH = ROOT / "android" / "upstream" / "podroid.lock"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
EXPECTED_METHOD = "git-subtree-squash"
EXPECTED_DESTINATION = "android/podroid"
HOOK = 'apply(from = rootProject.file("../podroid.integration.gradle.kts"))'


class VendorError(RuntimeError):
    """A deterministic, user-facing vendoring failure."""


@dataclass(frozen=True)
class Lock:
    repository: str
    commit: str
    release: str
    destination: PurePosixPath
    method: str
    patch_series: PurePosixPath
    captured_at: str
    verified_at: str
    verified_commit_message: str

    @property
    def destination_path(self) -> Path:
        return ROOT / Path(*self.destination.parts)

    @property
    def patch_series_path(self) -> Path:
        return ROOT / Path(*self.patch_series.parts)


def run(
    args: list[str],
    *,
    cwd: Path = ROOT,
    capture: bool = False,
    allow_difference: bool = False,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        args,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    allowed = {0, 1} if allow_difference else {0}
    if completed.returncode not in allowed:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise VendorError(
            f"command failed ({completed.returncode}): {' '.join(args)}"
            + (f"\n{detail}" if detail else "")
        )
    return completed


def git(*args: str, cwd: Path = ROOT, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd=cwd, capture=capture)


def safe_relative(value: object, field: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise VendorError(f"{field} must be a non-empty string")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise VendorError(f"{field} must be a normalized repository-relative path")
    return path


def load_lock() -> Lock:
    try:
        raw = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise VendorError(f"cannot read {LOCK_PATH.relative_to(ROOT)}: {error}") from error
    if not isinstance(raw, dict):
        raise VendorError("Podroid lock must contain a JSON object")
    if raw.get("schemaVersion") != 2:
        raise VendorError("unsupported Podroid lock schema; expected schemaVersion 2")

    repository = raw.get("repository")
    if (
        not isinstance(repository, str)
        or not repository.startswith("https://github.com/")
        or not repository.endswith(".git")
    ):
        raise VendorError("repository must be an explicit HTTPS GitHub clone URL")

    commit = raw.get("commit")
    if not isinstance(commit, str) or COMMIT_RE.fullmatch(commit) is None:
        raise VendorError("commit must be a full lowercase 40-character SHA")

    destination = safe_relative(raw.get("destination"), "destination")
    if destination.as_posix() != EXPECTED_DESTINATION:
        raise VendorError(f"destination must remain {EXPECTED_DESTINATION}")

    method = raw.get("method")
    if method != EXPECTED_METHOD:
        raise VendorError(f"method must remain {EXPECTED_METHOD}")

    patch_series = safe_relative(raw.get("patchSeries"), "patchSeries")
    release = raw.get("release")
    if not isinstance(release, str) or not release.startswith("v"):
        raise VendorError("release must be an explicit upstream v-prefixed release")

    captured_at = raw.get("capturedAt")
    verified_at = raw.get("verifiedAt")
    if not isinstance(captured_at, str) or DATE_RE.fullmatch(captured_at) is None:
        raise VendorError("capturedAt must use YYYY-MM-DD")
    if not isinstance(verified_at, str) or DATE_RE.fullmatch(verified_at) is None:
        raise VendorError("verifiedAt must use YYYY-MM-DD")

    verified_message = raw.get("verifiedCommitMessage")
    if not isinstance(verified_message, str) or not verified_message.strip():
        raise VendorError("verifiedCommitMessage must be non-empty")

    return Lock(
        repository=repository,
        commit=commit,
        release=release,
        destination=destination,
        method=method,
        patch_series=patch_series,
        captured_at=captured_at,
        verified_at=verified_at,
        verified_commit_message=verified_message,
    )


def patch_paths(lock: Lock) -> list[Path]:
    series = lock.patch_series_path
    try:
        lines = series.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise VendorError(f"cannot read patch series {series.relative_to(ROOT)}: {error}") from error

    paths: list[Path] = []
    seen: set[str] = set()
    for line_number, raw in enumerate(lines, start=1):
        entry = raw.strip()
        if not entry or entry.startswith("#"):
            continue
        relative = safe_relative(entry, f"{series.relative_to(ROOT)}:{line_number}")
        if len(relative.parts) != 1 or relative.suffix != ".patch":
            raise VendorError("patch series entries must be .patch files in the series directory")
        if entry in seen:
            raise VendorError(f"duplicate patch series entry: {entry}")
        seen.add(entry)
        patch = series.parent / entry
        if not patch.is_file():
            raise VendorError(f"listed patch is missing: {patch.relative_to(ROOT)}")
        text = patch.read_text(encoding="utf-8")
        if not text.startswith("diff --git "):
            raise VendorError(f"patch lacks a git diff header: {patch.relative_to(ROOT)}")
        paths.append(patch)

    if not paths:
        raise VendorError("Podroid patch series must contain at least one patch")

    unlisted = sorted(
        path.name for path in series.parent.glob("*.patch") if path.name not in seen
    )
    if unlisted:
        raise VendorError("unlisted Podroid patch files: " + ", ".join(unlisted))
    return paths


def assert_git_repository() -> None:
    git("rev-parse", "--show-toplevel", capture=True)


def assert_clean() -> None:
    status = git("status", "--porcelain=v1", "--untracked-files=all", capture=True).stdout
    if status.strip():
        raise VendorError("working tree must be clean before changing the Podroid subtree")


def verify_workspace_wiring(lock: Lock) -> None:
    destination = lock.destination_path
    settings = destination / "settings.gradle.kts"
    properties = destination / "gradle.properties"
    app = destination / "app" / "build.gradle.kts"
    integration = ROOT / "android" / "podroid.integration.gradle.kts"
    runtime_preparer = ROOT / "tools" / "vendor" / "prepare-podroid-runtime.py"
    legacy_runtime_preparer = destination / "prepare-runtime.py"

    required = [settings, properties, app, integration, runtime_preparer]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise VendorError("Podroid integration files are missing: " + ", ".join(missing))
    if legacy_runtime_preparer.exists():
        raise VendorError("runtime preparer must live outside the vendored Podroid subtree")

    if '// NODEHOST-WORKSPACE-INCLUDE' not in settings.read_text(encoding="utf-8"):
        raise VendorError("Podroid settings workspace hook is missing")

    workspace = (ROOT / "android" / "workspace.gradle.properties").read_text(
        encoding="utf-8"
    ).strip()
    property_text = properties.read_text(encoding="utf-8")
    expected_block = (
        "# NODEHOST-WORKSPACE-PROPERTIES-BEGIN\n"
        + workspace
        + "\n# NODEHOST-WORKSPACE-PROPERTIES-END"
    )
    if expected_block not in property_text:
        raise VendorError("Podroid workspace properties do not match the canonical block")

    app_text = app.read_text(encoding="utf-8")
    if HOOK not in app_text:
        raise VendorError("Podroid app does not apply the external integration script")
    forbidden = ("NODEHOST-COMPOSITION-HOOK", "preparePodroidRuntime", "verifyPodroidPackaging")
    found = [value for value in forbidden if value in app_text]
    if found:
        raise VendorError(
            "SalvageNet build logic leaked back into the vendored app build: "
            + ", ".join(found)
        )

    integration_text = integration.read_text(encoding="utf-8")
    for required_text in (
        'dependencies.add("implementation", project(":node-shell"))',
        "preparePodroidRuntime",
        "verifyNodeHostProfilePackaging",
        "verifyPodroidPackaging",
        "prepare-podroid-runtime.py",
    ):
        if required_text not in integration_text:
            raise VendorError(f"external Podroid integration is missing: {required_text}")


def verify_offline() -> Lock:
    assert_git_repository()
    lock = load_lock()
    patches = patch_paths(lock)
    if not lock.destination_path.is_dir():
        raise VendorError(f"{lock.destination.as_posix()} is not imported")
    verify_workspace_wiring(lock)
    print(
        "Podroid vendoring metadata: OK "
        f"({lock.release}, {lock.commit}, {len(patches)} patch(es))"
    )
    return lock


def apply_patches(lock: Lock, *, directory: Path, use_repository_prefix: bool) -> None:
    for patch in patch_paths(lock):
        args = ["apply", "--whitespace=error-all"]
        if use_repository_prefix:
            args.append(f"--directory={lock.destination.as_posix()}")
        args.append(str(patch))
        git(*args, cwd=directory)
        print(f"Applied {patch.relative_to(ROOT)}")


@contextlib.contextmanager
def expected_tree(lock: Lock) -> Iterator[Path]:
    with tempfile.TemporaryDirectory(prefix="salvagenet-podroid-upstream-") as temporary:
        checkout = Path(temporary) / "upstream"
        checkout.mkdir()
        git("init", "--quiet", cwd=checkout)
        git(
            "fetch",
            "--quiet",
            "--depth=1",
            "--no-tags",
            lock.repository,
            lock.commit,
            cwd=checkout,
        )
        resolved = git("rev-parse", "FETCH_HEAD^{commit}", cwd=checkout, capture=True).stdout.strip()
        if resolved != lock.commit:
            raise VendorError(
                f"upstream resolved to {resolved}, expected locked commit {lock.commit}"
            )
        git("-c", "advice.detachedHead=false", "checkout", "--quiet", "--detach", "FETCH_HEAD", cwd=checkout)
        apply_patches(lock, directory=checkout, use_repository_prefix=False)
        yield checkout


def mode_and_bytes(path: Path) -> tuple[str, bytes]:
    if path.is_symlink():
        return "120000", os.readlink(path).encode("utf-8")
    mode = "100755" if os.access(path, os.X_OK) else "100644"
    return mode, path.read_bytes()


def expected_files(root: Path) -> dict[str, tuple[str, bytes]]:
    result: dict[str, tuple[str, bytes]] = {}
    for path in sorted(root.rglob("*")):
        if ".git" in path.relative_to(root).parts or path.is_dir():
            continue
        result[path.relative_to(root).as_posix()] = mode_and_bytes(path)
    return result


def tracked_files(lock: Lock) -> dict[str, tuple[str, bytes]]:
    prefix = lock.destination.as_posix() + "/"
    output = git("ls-files", "-s", "-z", "--", lock.destination.as_posix(), capture=True).stdout
    result: dict[str, tuple[str, bytes]] = {}
    for entry in output.split("\0"):
        if not entry:
            continue
        metadata, repository_path = entry.split("\t", 1)
        mode = metadata.split(" ", 1)[0]
        if not repository_path.startswith(prefix):
            raise VendorError(f"unexpected tracked Podroid path: {repository_path}")
        relative = repository_path[len(prefix) :]
        path = ROOT / repository_path
        if not path.exists() and not path.is_symlink():
            raise VendorError(f"tracked Podroid file is missing from the worktree: {repository_path}")
        _, content = mode_and_bytes(path)
        result[relative] = (mode, content)
    return result


def compare_trees(expected: dict[str, tuple[str, bytes]], actual: dict[str, tuple[str, bytes]]) -> list[str]:
    changes: list[str] = []
    expected_names = set(expected)
    actual_names = set(actual)
    for name in sorted(expected_names - actual_names):
        changes.append(f"missing from vendored tree: {name}")
    for name in sorted(actual_names - expected_names):
        changes.append(f"not represented by upstream + patch series: {name}")
    for name in sorted(expected_names & actual_names):
        expected_mode, expected_content = expected[name]
        actual_mode, actual_content = actual[name]
        if expected_mode != actual_mode:
            changes.append(f"mode differs: {name} ({expected_mode} != {actual_mode})")
        if expected_content != actual_content:
            expected_hash = hashlib.sha256(expected_content).hexdigest()[:12]
            actual_hash = hashlib.sha256(actual_content).hexdigest()[:12]
            changes.append(f"content differs: {name} ({expected_hash} != {actual_hash})")
    return changes


def verify_network(lock: Lock) -> None:
    with expected_tree(lock) as checkout:
        changes = compare_trees(expected_files(checkout), tracked_files(lock))
    if changes:
        preview = "\n".join(f"- {change}" for change in changes[:50])
        suffix = f"\n- ... {len(changes) - 50} more" if len(changes) > 50 else ""
        raise VendorError(
            "vendored Podroid does not equal the pinned upstream tree plus its patch series:\n"
            + preview
            + suffix
        )
    print("Podroid upstream commit and patch series reproduce android/podroid exactly")


def command_verify(offline: bool) -> None:
    lock = verify_offline()
    if not offline:
        verify_network(lock)


def command_import() -> None:
    assert_git_repository()
    lock = load_lock()
    patch_paths(lock)
    assert_clean()
    if lock.destination_path.exists():
        raise VendorError(f"{lock.destination.as_posix()} already exists; refusing to overwrite")

    # Prove the exact upstream commit exists and every ordered patch applies before
    # git subtree creates the vendor commit.
    with expected_tree(lock):
        pass

    git(
        "subtree",
        "add",
        f"--prefix={lock.destination.as_posix()}",
        lock.repository,
        lock.commit,
        "--squash",
    )
    apply_patches(lock, directory=ROOT, use_repository_prefix=True)
    verify_workspace_wiring(lock)
    print(
        "Imported the locked Podroid subtree and applied SalvageNet patches.\n"
        "Commit the remaining adaptation changes separately from the subtree vendor commit."
    )


def command_update() -> None:
    lock = verify_offline()
    assert_clean()
    git(
        "subtree",
        "pull",
        f"--prefix={lock.destination.as_posix()}",
        lock.repository,
        lock.commit,
        "--squash",
    )
    try:
        verify_network(lock)
    except VendorError as error:
        raise VendorError(
            f"{error}\nRefresh the ordered patch series in a separate adaptation commit."
        ) from error
    print("Updated Podroid to the locked commit and verified the downstream patch queue")


def command_apply_patches() -> None:
    assert_git_repository()
    lock = load_lock()
    try:
        verify_workspace_wiring(lock)
    except VendorError:
        assert_clean()
        apply_patches(lock, directory=ROOT, use_repository_prefix=True)
        verify_workspace_wiring(lock)
        print("Podroid patch series applied")
    else:
        print("Podroid patch series is already represented in the worktree")


def write_snapshot(files: dict[str, tuple[str, bytes]], output: Path) -> None:
    for relative, (mode, content) in files.items():
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if mode == "120000":
            destination.symlink_to(content.decode("utf-8"))
        else:
            destination.write_bytes(content)
            destination.chmod(0o755 if mode == "100755" else 0o644)


def command_diff() -> None:
    lock = verify_offline()
    with expected_tree(lock) as checkout, tempfile.TemporaryDirectory(
        prefix="salvagenet-podroid-diff-"
    ) as temporary:
        root = Path(temporary)
        expected = root / "expected"
        actual = root / "actual"
        expected.mkdir()
        actual.mkdir()
        write_snapshot(expected_files(checkout), expected)
        write_snapshot(tracked_files(lock), actual)
        completed = run(
            [
                "git",
                "diff",
                "--no-index",
                "--binary",
                "--no-ext-diff",
                "--",
                str(expected),
                str(actual),
            ],
            cwd=ROOT,
            capture=True,
            allow_difference=True,
        )
        if completed.returncode == 0:
            print("No diff: vendored Podroid equals pinned upstream plus patches")
        else:
            sys.stdout.write(completed.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("import", help="add the locked upstream subtree and apply patches")
    subparsers.add_parser("update", help="merge the locked upstream commit and verify patches")
    verify_parser = subparsers.add_parser("verify", help="verify lock, wiring, commit, and patch queue")
    verify_parser.add_argument(
        "--offline",
        action="store_true",
        help="check only repository-local metadata and wiring",
    )
    subparsers.add_parser("diff", help="diff the vendored tree against upstream plus patches")
    subparsers.add_parser(
        "apply-patches",
        help="compatibility helper for a freshly imported, unpatched subtree",
    )
    args = parser.parse_args()

    if args.command == "import":
        command_import()
    elif args.command == "update":
        command_update()
    elif args.command == "verify":
        command_verify(args.offline)
    elif args.command == "diff":
        command_diff()
    else:
        command_apply_patches()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, VendorError) as error:
        print(f"Podroid vendoring failed: {error}", file=sys.stderr)
        raise SystemExit(1)
