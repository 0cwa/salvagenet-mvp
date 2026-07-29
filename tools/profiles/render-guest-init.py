#!/usr/bin/env python3
"""Render checked-in guest-init templates without executing profile content."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
GUEST_INIT_ROOT = ROOT / "profiles/guest-init"
MAX_ASSET_BYTES = 128 * 1024
INCLUDE_LINE = re.compile(r"^(?P<indent>\s*)\{\{INCLUDE:(?P<path>[^}]+)\}\}\s*$")
VALUE = re.compile(r"\{\{(?P<name>[A-Z][A-Z0-9_]*)\}\}")
SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_-]{16,512}$")
SAFE_HOSTNAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,62}$")
SAFE_INSTANCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def repository_file(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    if path != GUEST_INIT_ROOT and GUEST_INIT_ROOT not in path.parents:
        raise ValueError(f"include is outside profiles/guest-init: {relative}")
    if not path.is_file():
        raise ValueError(f"include does not exist: {relative}")
    if path.stat().st_size > MAX_ASSET_BYTES:
        raise ValueError(f"include exceeds {MAX_ASSET_BYTES} bytes: {relative}")
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


def validate_deployment_value(name: str, value: str) -> None:
    if name == "METADATA_BASE":
        parsed = urlparse(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or not parsed.path.endswith("/")
            or any(character.isspace() for character in value)
            or len(value) > 2048
        ):
            raise ValueError("METADATA_BASE must be a bounded http(s) URL ending in /")
    elif name == "BOOTSTRAP_TOKEN" and not SAFE_TOKEN.fullmatch(value):
        raise ValueError("BOOTSTRAP_TOKEN must be a 16-512 character URL-safe token")
    elif name == "HOSTNAME" and not SAFE_HOSTNAME.fullmatch(value):
        raise ValueError("HOSTNAME is invalid")
    elif name == "INSTANCE_ID" and not SAFE_INSTANCE_ID.fullmatch(value):
        raise ValueError("INSTANCE_ID is invalid")
    elif "\n" in value or "\r" in value or "\x00" in value:
        raise ValueError(f"{name} contains a forbidden control character")


def render_values(text: str, values: dict[str, Any], allow_unresolved: bool) -> str:
    normalized = {key: str(value) for key, value in values.items()}
    for name, value in normalized.items():
        validate_deployment_value(name, value)

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
    if resolved != GUEST_INIT_ROOT and GUEST_INIT_ROOT not in resolved.parents:
        raise ValueError(f"template is outside profiles/guest-init: {template}")
    if not resolved.is_file():
        raise ValueError(f"template does not exist: {template}")
    if resolved.stat().st_size > MAX_ASSET_BYTES:
        raise ValueError(f"template exceeds {MAX_ASSET_BYTES} bytes: {template}")
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
