#!/usr/bin/env python3
"""Build and verify the exact profile/guest-init assets consumed by Android."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE_ROOT = ROOT / "profiles"
SCHEMA = PROFILE_ROOT / "schema" / "vm-profile.schema.json"
PROFILE_IDS = (
    "alpine-direct-qualification",
    "ubuntu-2404-arm64-uefi",
    "k3s-worker-lab",
)
MAX_PROFILE_BYTES = 64 * 1024
MAX_VENDOR_BYTES = 128 * 1024


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def renderer_module():
    path = ROOT / "tools" / "profiles" / "render-guest-init.py"
    spec = importlib.util.spec_from_file_location("nodehost_guest_init_renderer", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("guest-init renderer could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bounded(path: Path, maximum: int) -> bytes:
    if not path.is_file():
        raise RuntimeError(f"required profile asset is missing: {path}")
    if path.stat().st_size > maximum:
        raise RuntimeError(f"profile asset exceeds {maximum} bytes: {path}")
    return path.read_bytes()


def expected_assets() -> dict[str, bytes]:
    renderer = renderer_module()
    assets: dict[str, bytes] = {}
    index_entries: list[dict[str, object]] = []
    seen_vendor: dict[str, bytes] = {}
    for profile_id in PROFILE_IDS:
        profile_path = PROFILE_ROOT / profile_id / "profile.json"
        profile_bytes = bounded(profile_path, MAX_PROFILE_BYTES)
        profile = json.loads(profile_bytes)
        if profile.get("apiVersion") != "nodehost.example/v1alpha1" or profile.get("kind") != "VirtualMachineProfile":
            raise RuntimeError(f"unsupported profile contract: {profile_path}")
        if profile.get("metadata", {}).get("id") != profile_id:
            raise RuntimeError(f"profile directory/id mismatch: {profile_path}")
        relative_vendor = profile["spec"]["initialization"]["vendorData"]
        vendor_source = (PROFILE_ROOT / relative_vendor).resolve()
        if PROFILE_ROOT.resolve() not in vendor_source.parents:
            raise RuntimeError(f"vendor data escaped profiles root: {relative_vendor}")
        if profile["spec"]["initialization"]["type"] == "nocloud-net":
            vendor_text = renderer.render(vendor_source, {}, allow_unresolved=False)
            vendor_bytes = vendor_text.encode("utf-8")
            if not vendor_text.startswith("#cloud-config\n") or "{{" in vendor_text:
                raise RuntimeError(f"vendor data did not render to final cloud-config: {relative_vendor}")
        else:
            vendor_bytes = bounded(vendor_source, MAX_VENDOR_BYTES)
        if len(vendor_bytes) > MAX_VENDOR_BYTES:
            raise RuntimeError(f"rendered vendor data exceeds {MAX_VENDOR_BYTES} bytes: {relative_vendor}")
        previous = seen_vendor.setdefault(relative_vendor, vendor_bytes)
        if previous != vendor_bytes:
            raise RuntimeError(f"vendor data path rendered inconsistently: {relative_vendor}")
        profile_asset = f"nodehost/profiles/{profile_id}/profile.json"
        vendor_asset = f"nodehost/{relative_vendor}"
        assets[profile_asset] = profile_bytes
        assets[vendor_asset] = vendor_bytes
        index_entries.append(
            {
                "id": profile_id,
                "profilePath": profile_asset.removeprefix("nodehost/"),
                "profileSha256": sha256_bytes(profile_bytes),
                "vendorDataPath": relative_vendor,
                "vendorDataSha256": sha256_bytes(vendor_bytes),
            }
        )
    schema_bytes = bounded(SCHEMA, MAX_PROFILE_BYTES)
    assets["nodehost/profiles/vm-profile.schema.json"] = schema_bytes
    index = {
        "schemaVersion": 1,
        "profileSchemaSha256": sha256_bytes(schema_bytes),
        "profiles": index_entries,
    }
    assets["nodehost/profiles/index.json"] = (
        json.dumps(index, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return assets


def prepare(output_dir: Path) -> None:
    assets = expected_assets()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    try:
        for relative, content in assets.items():
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
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


def verify_apk(apk: Path) -> None:
    if not apk.is_file():
        raise RuntimeError(f"APK is missing: {apk}")
    expected = expected_assets()
    with zipfile.ZipFile(apk) as archive:
        by_name: dict[str, list[zipfile.ZipInfo]] = {}
        for info in archive.infolist():
            by_name.setdefault(info.filename, []).append(info)
        for relative, content in expected.items():
            apk_path = f"assets/{relative}"
            matches = by_name.get(apk_path, [])
            if len(matches) != 1 or matches[0].is_dir():
                raise RuntimeError(f"APK must contain exactly one profile asset: {apk_path}")
            actual = archive.read(matches[0])
            if actual != content:
                raise RuntimeError(
                    f"packaged profile asset differs from canonical source: {apk_path}; "
                    f"expected={sha256_bytes(content)} actual={sha256_bytes(actual)}"
                )
    print(f"Verified {len(expected)} canonical profile assets in {apk}")


def main() -> int:
    parser = argparse.ArgumentParser()
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--prepare", action="store_true")
    actions.add_argument("--verify-apk", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    try:
        if args.prepare:
            if args.output_dir is None:
                parser.error("--prepare requires --output-dir")
            prepare(args.output_dir.resolve())
        else:
            verify_apk(args.verify_apk.resolve())
    except (KeyError, TypeError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from None
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
