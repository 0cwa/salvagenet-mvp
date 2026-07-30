#!/usr/bin/env python3
"""Prepare and verify Podroid's pinned APK-native runtime artifacts."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import struct
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
LOCK_PATH = HERE.parent / "upstream" / "podroid-runtime.lock"
SOURCE_ASSETS = HERE / "app" / "src" / "main" / "assets"
CHUNK_SIZE = 1024 * 1024


class RuntimeErrorWithContext(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_lock() -> dict:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    if lock.get("schemaVersion") != 1:
        raise RuntimeErrorWithContext("unsupported runtime lock schema")
    return lock


def verify_file(path: Path, artifact: dict) -> None:
    if not path.is_file():
        raise RuntimeErrorWithContext(f"required runtime artifact is missing: {path}")
    actual_size = path.stat().st_size
    if actual_size != artifact["size"]:
        raise RuntimeErrorWithContext(
            f"size mismatch for {path}: expected {artifact['size']}, got {actual_size}"
        )
    actual_hash = sha256_file(path)
    if actual_hash != artifact["sha256"]:
        raise RuntimeErrorWithContext(
            f"SHA-256 mismatch for {path}: expected {artifact['sha256']}, got {actual_hash}"
        )


def verify_elf(path: Path) -> None:
    data = path.read_bytes()
    if len(data) < 64 or data[:6] != b"\x7fELF\x02\x01":
        raise RuntimeErrorWithContext(f"not a 64-bit little-endian ELF: {path}")
    machine = struct.unpack_from("<H", data, 18)[0]
    if machine != 183:  # EM_AARCH64
        raise RuntimeErrorWithContext(f"not an AArch64 ELF (e_machine={machine}): {path}")
    program_offset = struct.unpack_from("<Q", data, 32)[0]
    entry_size = struct.unpack_from("<H", data, 54)[0]
    entry_count = struct.unpack_from("<H", data, 56)[0]
    if entry_size < 56 or entry_count == 0 or program_offset + entry_size * entry_count > len(data):
        raise RuntimeErrorWithContext(f"invalid ELF program header table: {path}")
    loads = 0
    for index in range(entry_count):
        offset = program_offset + index * entry_size
        if struct.unpack_from("<I", data, offset)[0] != 1:  # PT_LOAD
            continue
        loads += 1
        file_offset = struct.unpack_from("<Q", data, offset + 8)[0]
        virtual_address = struct.unpack_from("<Q", data, offset + 16)[0]
        alignment = struct.unpack_from("<Q", data, offset + 48)[0]
        if alignment < 16384 or file_offset % 16384 != virtual_address % 16384:
            raise RuntimeErrorWithContext(
                f"ELF PT_LOAD is not 16 KiB compatible (align={alignment}): {path}"
            )
    if loads == 0:
        raise RuntimeErrorWithContext(f"ELF has no PT_LOAD segments: {path}")


def generated_path(output_dir: Path, apk_path: str) -> Path:
    pure = PurePosixPath(apk_path)
    if pure.is_absolute() or ".." in pure.parts:
        raise RuntimeErrorWithContext(f"unsafe locked APK path: {apk_path}")
    if pure.parts[:2] == ("lib", "arm64-v8a"):
        return output_dir / "jniLibs" / "arm64-v8a" / pure.name
    if pure.parts[:1] == ("assets",):
        return output_dir / "assets" / Path(*pure.parts[1:])
    raise RuntimeErrorWithContext(f"unsupported generated APK path: {apk_path}")


def verify_runtime(output_dir: Path, lock: dict) -> None:
    for artifact in lock["artifacts"]:
        apk_path = artifact["apkPath"]
        if artifact["generated"]:
            path = generated_path(output_dir, apk_path)
        else:
            path = SOURCE_ASSETS / Path(*PurePosixPath(apk_path).parts[1:])
        verify_file(path, artifact)
        if apk_path.startswith("lib/arm64-v8a/"):
            verify_elf(path)
    marker = output_dir / ".prepared.json"
    if not marker.is_file():
        raise RuntimeErrorWithContext(f"runtime preparation marker is missing: {marker}")


def cache_directory() -> Path:
    configured = os.environ.get("PODROID_RUNTIME_CACHE")
    if configured:
        return Path(configured).expanduser()
    cache_home = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return cache_home / "podroid" / "runtime"


def valid_source_apk(path: Path, source: dict) -> bool:
    return (
        path.is_file()
        and path.stat().st_size == source["size"]
        and sha256_file(path) == source["sha256"]
    )


def obtain_source_apk(lock: dict, offline: bool) -> Path:
    source = lock["source"]
    cache_dir = cache_directory() / source["version"]
    cache_dir.mkdir(parents=True, exist_ok=True)
    apk = cache_dir / source["fileName"]
    lock_file = cache_dir / ".download.lock"
    with lock_file.open("a+b") as lock_stream:
        fcntl.flock(lock_stream, fcntl.LOCK_EX)
        if valid_source_apk(apk, source):
            print(f"Podroid runtime source cache hit: {apk}")
            return apk
        if apk.exists():
            if offline:
                raise RuntimeErrorWithContext(f"cached runtime APK failed its pinned digest: {apk}")
            apk.unlink()
        if offline:
            raise RuntimeErrorWithContext(
                f"offline mode requires pinned runtime APK in cache: {apk}"
            )
        partial = apk.with_suffix(apk.suffix + ".partial")
        partial.unlink(missing_ok=True)
        request = urllib.request.Request(
            source["url"], headers={"User-Agent": "nodehost-podroid-runtime-preparer/1"}
        )
        print(f"Downloading pinned Podroid runtime source: {source['url']}")
        try:
            with urllib.request.urlopen(request, timeout=30) as response, partial.open("xb") as out:
                total = 0
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > source["size"]:
                        raise RuntimeErrorWithContext("runtime APK exceeds pinned size")
                    out.write(chunk)
                out.flush()
                os.fsync(out.fileno())
            if not valid_source_apk(partial, source):
                raise RuntimeErrorWithContext("downloaded runtime APK failed pinned size/SHA-256")
            os.replace(partial, apk)
        finally:
            partial.unlink(missing_ok=True)
        return apk


def validate_zip_entries(archive: zipfile.ZipFile, lock: dict) -> dict[str, zipfile.ZipInfo]:
    by_name: dict[str, list[zipfile.ZipInfo]] = {}
    for info in archive.infolist():
        by_name.setdefault(info.filename, []).append(info)
    selected: dict[str, zipfile.ZipInfo] = {}
    for artifact in lock["artifacts"]:
        name = artifact["apkPath"]
        pure = PurePosixPath(name)
        if pure.is_absolute() or ".." in pure.parts:
            raise RuntimeErrorWithContext(f"unsafe locked archive path: {name}")
        matches = by_name.get(name, [])
        if len(matches) != 1 or matches[0].is_dir():
            raise RuntimeErrorWithContext(f"archive must contain exactly one regular entry: {name}")
        if matches[0].file_size != artifact["size"]:
            raise RuntimeErrorWithContext(f"archive entry size mismatch: {name}")
        selected[name] = matches[0]
    return selected


def extract_generated(apk: Path, output_dir: Path, lock: dict) -> None:
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    try:
        with zipfile.ZipFile(apk) as archive:
            entries = validate_zip_entries(archive, lock)
            for artifact in lock["artifacts"]:
                if not artifact["generated"]:
                    continue
                destination = generated_path(staging, artifact["apkPath"])
                destination.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                written = 0
                with archive.open(entries[artifact["apkPath"]]) as source, destination.open("xb") as out:
                    while True:
                        chunk = source.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        written += len(chunk)
                        if written > artifact["size"]:
                            raise RuntimeErrorWithContext(f"expanded entry exceeds pinned size: {artifact['apkPath']}")
                        digest.update(chunk)
                        out.write(chunk)
                if written != artifact["size"] or digest.hexdigest() != artifact["sha256"]:
                    raise RuntimeErrorWithContext(f"extracted artifact failed lock: {artifact['apkPath']}")
                if artifact["apkPath"].startswith("lib/arm64-v8a/"):
                    verify_elf(destination)
        marker = staging / ".prepared.json"
        marker.write_text(
            json.dumps({"sourceSha256": lock["source"]["sha256"], "schemaVersion": 1}, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        old = output_dir.with_name(output_dir.name + ".old")
        if old.exists():
            shutil.rmtree(old)
        if output_dir.exists():
            os.replace(output_dir, old)
        try:
            os.replace(staging, output_dir)
        except BaseException:
            if old.exists() and not output_dir.exists():
                os.replace(old, output_dir)
            raise
        if old.exists():
            shutil.rmtree(old)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def prepare(output_dir: Path, offline: bool) -> None:
    lock = load_lock()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    preparation_lock = output_dir.parent / ".podroid-runtime.prepare.lock"
    with preparation_lock.open("a+b") as lock_stream:
        fcntl.flock(lock_stream, fcntl.LOCK_EX)
        try:
            verify_runtime(output_dir, lock)
            print(f"Podroid runtime already prepared and verified: {output_dir}")
            return
        except RuntimeErrorWithContext:
            pass
        apk = obtain_source_apk(lock, offline)
        extract_generated(apk, output_dir, lock)
        verify_runtime(output_dir, lock)
        print(f"Prepared and verified Podroid runtime: {output_dir}")


def verify_packaged_apk(apk: Path) -> None:
    lock = load_lock()
    if not apk.is_file():
        raise RuntimeErrorWithContext(f"APK is missing: {apk}")
    with zipfile.ZipFile(apk) as archive:
        entries = validate_zip_entries(archive, lock)
        for artifact in lock["artifacts"]:
            info = entries[artifact["apkPath"]]
            digest = hashlib.sha256()
            native = artifact["apkPath"].startswith("lib/arm64-v8a/")
            with tempfile.NamedTemporaryFile() if native else open(os.devnull, "wb") as temporary:
                with archive.open(info) as stream:
                    for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
                        digest.update(chunk)
                        if native:
                            temporary.write(chunk)
                if digest.hexdigest() != artifact["sha256"]:
                    raise RuntimeErrorWithContext(f"packaged artifact digest mismatch: {artifact['apkPath']}")
                if native:
                    temporary.flush()
                    verify_elf(Path(temporary.name))
    print(f"Verified packaged Podroid runtime in {apk} ({apk.stat().st_size} bytes, sha256={sha256_file(apk)})")


def main() -> int:
    parser = argparse.ArgumentParser()
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--prepare", action="store_true")
    actions.add_argument("--verify-apk", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if args.prepare:
        if args.output_dir is None:
            parser.error("--prepare requires --output-dir")
        prepare(args.output_dir.resolve(), args.offline)
    else:
        verify_packaged_apk(args.verify_apk.resolve())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeErrorWithContext, zipfile.BadZipFile) as error:
        print(f"Podroid runtime preparation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
