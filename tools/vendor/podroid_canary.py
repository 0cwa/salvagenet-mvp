#!/usr/bin/env python3
"""Prepare an ephemeral Podroid upstream candidate for SalvageNet compatibility CI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
SOURCE_LOCK = ROOT / "android" / "upstream" / "podroid.lock"
RUNTIME_LOCK = ROOT / "android" / "upstream" / "podroid-runtime.lock"
PATCH_SERIES = ROOT / "android" / "upstream" / "patches" / "series"
DEFAULT_DESTINATION = ROOT / "android" / ".podroid-canary"
DEFAULT_REPORT_ROOT = ROOT / ".artifacts" / "podroid-canary"
CHUNK_SIZE = 1024 * 1024
SHA256_RE = re.compile(r"^sha256:([0-9a-f]{64})$")


class CanaryError(RuntimeError):
    pass


def run(args: list[str], *, cwd: Path, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        args,
        cwd=cwd,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise CanaryError(
            f"{' '.join(args)} failed ({completed.returncode})"
            + (f"\n{detail}" if detail else "")
        )
    return completed


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def repository_slug(repository: str) -> str:
    parsed = urlparse(repository)
    if parsed.scheme != "https" or parsed.netloc != "github.com":
        raise CanaryError("Podroid canary requires an https://github.com repository")
    parts = parsed.path.strip("/").split("/")
    if len(parts) != 2:
        raise CanaryError(f"cannot derive GitHub repository from {repository!r}")
    owner, name = parts
    if name.endswith(".git"):
        name = name[:-4]
    if not owner or not name:
        raise CanaryError(f"invalid GitHub repository path: {repository!r}")
    return f"{owner}/{name}"


def github_json(url: str) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "salvagenet-podroid-canary/1",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def resolve_ref(repository: str, refspec: str) -> tuple[str, str]:
    with tempfile.TemporaryDirectory(prefix="salvagenet-podroid-ref-") as temporary:
        checkout = Path(temporary)
        run(["git", "init", "--quiet"], cwd=checkout)
        run(
            ["git", "fetch", "--quiet", "--depth=1", "--no-tags", repository, refspec],
            cwd=checkout,
        )
        commit = run(["git", "rev-parse", "FETCH_HEAD^{commit}"], cwd=checkout).stdout.strip()
        subject = run(["git", "show", "-s", "--format=%s", "FETCH_HEAD"], cwd=checkout).stdout.strip()
    return commit, subject


def resolve_target(track: str, source_lock: dict) -> dict:
    repository = source_lock["repository"]
    slug = repository_slug(repository)
    if track == "release":
        release = github_json(f"https://api.github.com/repos/{slug}/releases/latest")
        tag = release.get("tag_name")
        if not isinstance(tag, str) or not tag:
            raise CanaryError("latest Podroid release has no tag_name")
        assets = [
            asset
            for asset in release.get("assets", [])
            if isinstance(asset.get("name"), str) and asset["name"].lower().endswith(".apk")
        ]
        if len(assets) != 1:
            raise CanaryError(f"expected exactly one APK asset in {tag}, found {len(assets)}")
        commit, subject = resolve_ref(repository, f"refs/tags/{tag}")
        asset = assets[0]
        return {
            "track": track,
            "commit": commit,
            "subject": subject,
            "release": tag,
            "releaseUrl": release.get("html_url"),
            "publishedAt": release.get("published_at"),
            "asset": {
                "name": asset["name"],
                "url": asset["browser_download_url"],
                "size": asset.get("size"),
                "digest": asset.get("digest"),
            },
        }
    if track == "main":
        commit, subject = resolve_ref(repository, "refs/heads/main")
        return {
            "track": track,
            "commit": commit,
            "subject": subject,
            "release": None,
            "releaseUrl": None,
            "publishedAt": None,
            "asset": None,
        }
    raise CanaryError(f"unsupported track: {track}")


def patch_names() -> list[str]:
    names: list[str] = []
    for raw in PATCH_SERIES.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            names.append(line)
    if not names:
        raise CanaryError("Podroid patch series is empty")
    return names


def checkout_target(repository: str, commit: str, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "init", "--quiet", str(destination)], cwd=ROOT)
    run(
        ["git", "fetch", "--quiet", "--depth=1", "--no-tags", repository, commit],
        cwd=destination,
    )
    run(["git", "checkout", "--quiet", "--detach", "FETCH_HEAD"], cwd=destination)


def apply_patch_series(destination: Path) -> tuple[list[dict], bool]:
    results: list[dict] = []
    failed = False
    for name in patch_names():
        patch = (PATCH_SERIES.parent / name).read_text(encoding="utf-8")
        if failed:
            results.append({"name": name, "status": "not-run"})
            continue
        checked = run(
            ["git", "apply", "--check", "--whitespace=nowarn", "-"],
            cwd=destination,
            input_text=patch,
            check=False,
        )
        if checked.returncode != 0:
            results.append(
                {
                    "name": name,
                    "status": "conflict",
                    "detail": (checked.stderr or checked.stdout).strip()[-8000:],
                }
            )
            failed = True
            continue
        applied = run(
            ["git", "apply", "--whitespace=nowarn", "-"],
            cwd=destination,
            input_text=patch,
            check=False,
        )
        if applied.returncode != 0:
            results.append(
                {
                    "name": name,
                    "status": "apply-failed",
                    "detail": (applied.stderr or applied.stdout).strip()[-8000:],
                }
            )
            failed = True
        else:
            results.append({"name": name, "status": "applied"})
    return results, not failed


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def obtain_release_apk(target: dict) -> Path:
    asset = target.get("asset")
    if not isinstance(asset, dict):
        raise CanaryError("release track is missing an APK asset")
    cache_root = Path(
        os.environ.get(
            "PODROID_CANARY_CACHE",
            str(Path.home() / ".cache" / "salvagenet-podroid-canary"),
        )
    )
    release_dir = cache_root / str(target["release"])
    release_dir.mkdir(parents=True, exist_ok=True)
    apk = release_dir / asset["name"]
    expected_digest = None
    digest_field = asset.get("digest")
    if isinstance(digest_field, str):
        match = SHA256_RE.fullmatch(digest_field)
        if match:
            expected_digest = match.group(1)
    expected_size = asset.get("size")
    if apk.is_file():
        size_ok = expected_size is None or apk.stat().st_size == expected_size
        digest_ok = expected_digest is None or sha256_file(apk) == expected_digest
        if size_ok and digest_ok:
            return apk
        apk.unlink()
    partial = apk.with_suffix(apk.suffix + ".partial")
    partial.unlink(missing_ok=True)
    request = urllib.request.Request(asset["url"], headers={"User-Agent": "salvagenet-podroid-canary/1"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response, partial.open("xb") as out:
            for chunk in iter(lambda: response.read(CHUNK_SIZE), b""):
                out.write(chunk)
        if expected_size is not None and partial.stat().st_size != expected_size:
            raise CanaryError(
                f"release APK size mismatch: expected {expected_size}, got {partial.stat().st_size}"
            )
        actual_digest = sha256_file(partial)
        if expected_digest is not None and actual_digest != expected_digest:
            raise CanaryError(
                f"release APK digest mismatch: expected {expected_digest}, got {actual_digest}"
            )
        os.replace(partial, apk)
    finally:
        partial.unlink(missing_ok=True)
    return apk


def build_runtime_lock(base_lock: dict, apk: Path, target: dict) -> dict:
    asset = target["asset"]
    apk_digest = sha256_file(apk)
    artifacts: list[dict] = []
    with zipfile.ZipFile(apk) as archive:
        by_name: dict[str, list[zipfile.ZipInfo]] = {}
        for info in archive.infolist():
            by_name.setdefault(info.filename, []).append(info)
        for artifact in base_lock["artifacts"]:
            name = artifact["apkPath"]
            matches = by_name.get(name, [])
            if len(matches) != 1 or matches[0].is_dir():
                raise CanaryError(
                    f"candidate release APK must contain exactly one regular entry: {name}"
                )
            digest = hashlib.sha256()
            with archive.open(matches[0]) as stream:
                for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
                    digest.update(chunk)
            artifacts.append(
                {
                    "apkPath": name,
                    "size": matches[0].file_size,
                    "sha256": digest.hexdigest(),
                    "generated": bool(artifact["generated"]),
                }
            )
    return {
        "schemaVersion": 1,
        "source": {
            "version": target["release"],
            "url": asset["url"],
            "fileName": asset["name"],
            "size": apk.stat().st_size,
            "sha256": apk_digest,
            "publishedBy": "Podroid upstream canary from GitHub release asset",
        },
        "artifacts": artifacts,
    }


def write_report(report: dict, report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    target = report.get("target") or {}
    lines = [
        "# Podroid upstream canary",
        "",
        f"- Track: `{report['track']}`",
        f"- Baseline: `{report['baseline']['release']}` / `{report['baseline']['commit']}`",
        f"- Target: `{target.get('release') or 'main'}` / `{target.get('commit', 'unresolved')}`",
    ]
    if target.get("subject"):
        lines.append(f"- Target subject: {target['subject']}")
    lines += ["", "## Patch queue", "", "| Patch | Result |", "|---|---|"]
    for patch in report.get("patches", []):
        lines.append(f"| `{patch['name']}` | {patch['status']} |")
    conflicts = [patch for patch in report.get("patches", []) if patch.get("detail")]
    if conflicts:
        lines += ["", "## Conflict details", ""]
        for patch in conflicts:
            lines += [f"### {patch['name']}", "", "```text", patch["detail"], "```", ""]
    runtime = report.get("runtime")
    if runtime:
        lines += ["## Runtime candidate", "", f"- Status: `{runtime['status']}`"]
        if runtime.get("apkSha256"):
            lines.append(f"- APK SHA-256: `{runtime['apkSha256']}`")
    if report.get("error"):
        lines += ["", "## Error", "", "```text", report["error"], "```"]
    (report_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def prepare(track: str, destination: Path, report_dir: Path) -> int:
    source_lock = load_json(SOURCE_LOCK)
    report = {
        "schemaVersion": 1,
        "track": track,
        "baseline": {"commit": source_lock["commit"], "release": source_lock["release"]},
        "target": {},
        "patches": [],
        "source": {"status": "pending", "destination": str(destination)},
        "runtime": {"status": "not-applicable" if track == "main" else "pending"},
    }
    try:
        target = resolve_target(track, source_lock)
        report["target"] = target
        checkout_target(source_lock["repository"], target["commit"], destination)
        patches, applied = apply_patch_series(destination)
        report["patches"] = patches
        if not applied:
            report["source"]["status"] = "patch-conflict"
            write_report(report, report_dir)
            return 2
        report["source"]["status"] = "ready"
        if track == "release":
            apk = obtain_release_apk(target)
            candidate_lock = build_runtime_lock(load_json(RUNTIME_LOCK), apk, target)
            RUNTIME_LOCK.write_text(json.dumps(candidate_lock, indent=2) + "\n", encoding="utf-8")
            report["runtime"] = {
                "status": "candidate-lock-written",
                "sourceVersion": target["release"],
                "apkSha256": candidate_lock["source"]["sha256"],
                "artifactCount": len(candidate_lock["artifacts"]),
            }
        shutil.rmtree(destination / ".git", ignore_errors=True)
        write_report(report, report_dir)
        return 0
    except (CanaryError, OSError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        report["source"]["status"] = "error"
        report["error"] = str(error)
        write_report(report, report_dir)
        print(f"Podroid canary preparation failed: {error}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare"])
    parser.add_argument("--track", choices=["release", "main"], required=True)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--report-dir", type=Path)
    args = parser.parse_args()
    report_dir = args.report_dir or (DEFAULT_REPORT_ROOT / args.track)
    return prepare(args.track, args.destination.resolve(), report_dir.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
