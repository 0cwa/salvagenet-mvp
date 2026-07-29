#!/usr/bin/env python3
"""Idempotently wire sibling NodeHost modules into the imported Podroid project."""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PODROID = ROOT / "android" / "podroid"
SETTINGS = PODROID / "settings.gradle.kts"
PROPS = PODROID / "gradle.properties"
APP = PODROID / "app" / "build.gradle.kts"
SETTINGS_MARK = "// NODEHOST-WORKSPACE-INCLUDE"
PROPS_BEGIN = "# NODEHOST-WORKSPACE-PROPERTIES-BEGIN"
PROPS_END = "# NODEHOST-WORKSPACE-PROPERTIES-END"
DEP = 'implementation(project(":node-shell"))'


def check() -> list[str]:
    missing: list[str] = []
    if not SETTINGS.exists():
        return ["Podroid is not imported"]
    if SETTINGS_MARK not in SETTINGS.read_text():
        missing.append("settings include marker")
    props = PROPS.read_text() if PROPS.exists() else ""
    if PROPS_BEGIN not in props or PROPS_END not in props:
        missing.append("Gradle properties block")
    if APP.exists() and DEP not in APP.read_text():
        missing.append("app node-shell dependency")
    return missing


def wire() -> None:
    if not SETTINGS.exists():
        raise SystemExit("import Podroid first")

    text = SETTINGS.read_text()
    if SETTINGS_MARK not in text:
        SETTINGS.write_text(
            text.rstrip()
            + "\n\n"
            + SETTINGS_MARK
            + '\napply(from = "../workspace.settings.gradle.kts")\n'
        )

    workspace = (ROOT / "android" / "workspace.gradle.properties").read_text().strip()
    props = PROPS.read_text() if PROPS.exists() else ""
    if PROPS_BEGIN not in props:
        PROPS.write_text(
            props.rstrip()
            + "\n\n"
            + PROPS_BEGIN
            + "\n"
            + workspace
            + "\n"
            + PROPS_END
            + "\n"
        )

    app = APP.read_text()
    if DEP not in app:
        needle = "dependencies {"
        if needle not in app:
            raise SystemExit("Podroid app dependencies block not found")
        insertion = needle + "\n    // NODEHOST-COMPOSITION-HOOK\n    " + DEP
        APP.write_text(app.replace(needle, insertion, 1))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        failures = check()
        if failures:
            raise SystemExit("not wired: " + ", ".join(failures))
        print("Podroid wiring: OK")
        return 0

    wire()
    failures = check()
    if failures:
        raise SystemExit("wiring incomplete: " + ", ".join(failures))
    print("Podroid wiring complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
