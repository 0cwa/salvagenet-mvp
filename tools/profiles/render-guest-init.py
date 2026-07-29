#!/usr/bin/env python3
"""Render checked-in guest-init templates without executing profile content."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
INCLUDE_LINE = re.compile(r"^(?P<indent>\s*)\{\{INCLUDE:(?P<path>[^}]+)\}\}\s*$")
VALUE = re.compile(r"\{\{(?P<name>[A-Z][A-Z0-9_]*)\}\}")


def repository_file(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    if path != ROOT and ROOT not in path.parents:
        raise ValueError(f"include escapes repository: {relative}")
    if not path.is_file():
        raise ValueError(f"include does not exist: {relative}")
    return path


def expand_includes(text: str) -> str:
    output: list[str] = []
    for raw_line in text.splitlines():
        match = INCLUDE_LINE.match(raw_line)
        if not match:
            output.append(raw_line)
            continue
        path = repository_file(match.group("path").strip())
        indent = match.group("indent")
        included = path.read_text(encoding="utf-8").rstrip("\n").splitlines()
        output.extend(indent + line if line else indent for line in included)
    return "\n".join(output) + ("\n" if text.endswith("\n") else "")


def render_values(text: str, values: dict[str, Any], allow_unresolved: bool) -> str:
    normalized = {key: str(value) for key, value in values.items()}

    def replace(match: re.Match[str]) -> str:
        name = match.group("name")
        if name in normalized:
            return normalized[name]
        if allow_unresolved:
            return match.group(0)
        raise ValueError(f"missing template value: {name}")

    return VALUE.sub(replace, text)


def render(template: Path, values: dict[str, Any], allow_unresolved: bool) -> str:
    resolved = template.resolve()
    if resolved != ROOT and ROOT not in resolved.parents:
        raise ValueError(f"template escapes repository: {template}")
    return render_values(
        expand_includes(resolved.read_text(encoding="utf-8")),
        values,
        allow_unresolved,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("template", type=Path)
    parser.add_argument("--values-json", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow-unresolved", action="store_true")
    args = parser.parse_args()

    values: dict[str, Any] = {}
    if args.values_json:
        loaded = json.loads(args.values_json.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise SystemExit("--values-json must contain a JSON object")
        values = loaded

    try:
        result = render(args.template, values, args.allow_unresolved)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_name(args.output.name + ".tmp")
        temporary.write_text(result, encoding="utf-8")
        temporary.replace(args.output)
    else:
        print(result, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
