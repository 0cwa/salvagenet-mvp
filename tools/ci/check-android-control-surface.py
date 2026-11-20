#!/usr/bin/env python3
"""Keep upstream automation entry points out of the SalvageNet application."""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ANDROID = "{http://schemas.android.com/apk/res/android}"
PODROID_PACKAGE = "com.excp.podroid"
FORBIDDEN_COMPONENTS = {
    "com.excp.podroid.service.VmControlReceiver",
    "com.excp.podroid.engine.control.ControlProvider",
    "com.excp.podroid.umltest.UmlTestProvider",
    "com.excp.podroid.umltest.UmlTestService",
}
FORBIDDEN_ACTIONS = {
    "com.excp.podroid.action.START_VM",
    "com.excp.podroid.action.STOP_VM",
}
ACTIVITY_DISPATCH = re.compile(r"\b(?:ACTION_START_VM|START_VM|handleStartVmIntent)\b")


class ControlSurfaceError(ValueError):
    pass


def component_name(name: str, package: str) -> str:
    if name.startswith("."):
        return package + name
    if "." not in name:
        return package + "." + name
    return name


def check_manifest(text: str, label: str = "manifest") -> None:
    try:
        manifest = ET.fromstring(text)
    except ET.ParseError as error:
        raise ControlSurfaceError(f"{label}: invalid manifest XML: {error}") from error
    if manifest.tag != "manifest":
        raise ControlSurfaceError(f"{label}: expected a manifest element")
    # Source manifests use the Gradle namespace; decoded APK manifests may use
    # a suffixed application ID but contain fully qualified component names.
    package = manifest.get("package") or PODROID_PACKAGE
    for component in manifest.findall("./application/*"):
        name = component_name(component.get(ANDROID + "name", ""), package)
        if name in FORBIDDEN_COMPONENTS:
            raise ControlSurfaceError(f"{label}: upstream control component is registered: {name}")
        for action in component.findall("./intent-filter/action"):
            name = action.get(ANDROID + "name")
            if name in FORBIDDEN_ACTIONS:
                raise ControlSurfaceError(f"{label}: upstream control action is registered: {name}")


def check_main_activity(text: str, label: str = "MainActivity.kt") -> None:
    # Removing an intent filter does not prevent delivery of explicit intents
    # to the exported launcher Activity. Its dispatch must be removed as well.
    match = ACTIVITY_DISPATCH.search(text)
    if match:
        raise ControlSurfaceError(f"{label}: upstream VM intent dispatch remains: {match.group()}")


def check_sources(root: Path = ROOT) -> int:
    sources = root / "android/podroid/app/src"
    if not sources.exists():
        return 0
    if not (sources / "main/AndroidManifest.xml").is_file():
        raise ControlSurfaceError("Podroid source is missing its main AndroidManifest.xml")
    manifests = sorted(sources.glob("*/AndroidManifest.xml"))
    for path in manifests:
        check_manifest(path.read_text(encoding="utf-8"), str(path.relative_to(root)))
    activity = sources / "main/java/com/excp/podroid/MainActivity.kt"
    check_main_activity(activity.read_text(encoding="utf-8"), str(activity.relative_to(root)))
    return len(manifests)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, help="decoded APK manifest from apkanalyzer manifest print")
    args = parser.parse_args()
    try:
        if args.manifest:
            check_manifest(args.manifest.read_text(encoding="utf-8"), str(args.manifest))
            print("Android control surface: PASS (packaged manifest)")
        else:
            count = check_sources()
            if count:
                print(f"Android control surface: PASS ({count} source manifest(s) and MainActivity)")
            else:
                print("Android control surface: SKIP (Podroid source has not been imported)")
        return 0
    except (OSError, ControlSurfaceError) as error:
        print(f"Android control surface failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
