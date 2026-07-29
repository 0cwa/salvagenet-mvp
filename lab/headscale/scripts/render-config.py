#!/usr/bin/env python3
"""Render and validate the disposable Headscale laboratory configuration."""

from __future__ import annotations

import argparse
import ipaddress
import os
from pathlib import Path
import re
from urllib.parse import urlparse


DOCUMENTATION_NETWORKS = (
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("2001:db8::/32"),
)
PLACEHOLDER = re.compile(r"\$\{[A-Z0-9_]+\}")


def parse_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise ValueError(
            f"missing {path}; copy .env.example to .env and set a phone-reachable URL"
        )
    values: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}:{line_number}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"{path}:{line_number}: empty key")
        values[key] = value
    return values


def validate_public_url(value: str, allow_non_phone_reachable: bool = False) -> None:
    if "REPLACE" in value.upper() or "EXAMPLE" in value.upper():
        raise ValueError("HEADSCALE_PUBLIC_URL still contains a placeholder")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("HEADSCALE_PUBLIC_URL must be an absolute http(s) URL")
    if parsed.path not in ("", "/") or parsed.params or parsed.query or parsed.fragment:
        raise ValueError("HEADSCALE_PUBLIC_URL must not contain a path, query, or fragment")
    if allow_non_phone_reachable:
        return

    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".invalid"):
        raise ValueError("HEADSCALE_PUBLIC_URL must be reachable from the Android phone")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return
    if address.is_loopback or address.is_unspecified:
        raise ValueError("HEADSCALE_PUBLIC_URL must not use loopback/unspecified address")
    if any(address in network for network in DOCUMENTATION_NETWORKS):
        raise ValueError("HEADSCALE_PUBLIC_URL uses a documentation-only address")


def validate_base_domain(value: str) -> None:
    if not value or value.startswith(".") or value.endswith(".") or "." not in value:
        raise ValueError("HEADSCALE_BASE_DOMAIN must be a dot-qualified DNS name")
    if not re.fullmatch(r"[A-Za-z0-9.-]+", value):
        raise ValueError("HEADSCALE_BASE_DOMAIN contains invalid characters")


def render(
    root: Path,
    env_path: Path,
    output_dir: Path,
    *,
    allow_non_phone_reachable: bool = False,
) -> Path:
    values = parse_env(env_path)
    values.update({key: value for key, value in os.environ.items() if key.startswith("HEADSCALE_")})

    required = {
        "HEADSCALE_VERSION",
        "HEADSCALE_PUBLIC_URL",
        "HEADSCALE_LISTEN_IP",
        "HEADSCALE_HOST_PORT",
        "HEADSCALE_BASE_DOMAIN",
    }
    missing = sorted(key for key in required if not values.get(key))
    if missing:
        raise ValueError("missing " + ", ".join(missing))

    validate_public_url(
        values["HEADSCALE_PUBLIC_URL"],
        allow_non_phone_reachable=allow_non_phone_reachable,
    )
    validate_base_domain(values["HEADSCALE_BASE_DOMAIN"])
    listen_address = ipaddress.ip_address(values["HEADSCALE_LISTEN_IP"])
    if listen_address.is_loopback:
        raise ValueError("HEADSCALE_LISTEN_IP must not be loopback")
    public_host = urlparse(values["HEADSCALE_PUBLIC_URL"]).hostname
    assert public_host is not None
    try:
        public_address = ipaddress.ip_address(public_host)
    except ValueError:
        public_address = None
    if (
        public_address is not None
        and not listen_address.is_unspecified
        and listen_address != public_address
    ):
        raise ValueError("HEADSCALE_LISTEN_IP must match the public URL address")
    try:
        host_port = int(values["HEADSCALE_HOST_PORT"])
    except ValueError:
        raise ValueError("HEADSCALE_HOST_PORT must be an integer") from None
    if not 1 <= host_port <= 65535:
        raise ValueError("HEADSCALE_HOST_PORT must be between 1 and 65535")
    public_url = urlparse(values["HEADSCALE_PUBLIC_URL"])
    public_port = public_url.port or (443 if public_url.scheme == "https" else 80)
    if public_port != host_port:
        raise ValueError("HEADSCALE_PUBLIC_URL port must match HEADSCALE_HOST_PORT")

    template = (root / "config/config.yaml.template").read_text(encoding="utf-8")
    for key, value in values.items():
        template = template.replace("${" + key + "}", value)
    unresolved = sorted(set(PLACEHOLDER.findall(template)))
    if unresolved:
        raise ValueError("unresolved template variable(s): " + ", ".join(unresolved))

    output_dir.mkdir(parents=True, exist_ok=True)
    config_path = output_dir / "config.yaml"
    policy_path = output_dir / "policy.hujson"
    config_tmp = config_path.with_suffix(".yaml.tmp")
    policy_tmp = policy_path.with_suffix(".hujson.tmp")
    config_tmp.write_text(template, encoding="utf-8")
    policy_tmp.write_text(
        (root / "config/policy.hujson").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    config_tmp.replace(config_path)
    policy_tmp.replace(policy_path)
    return config_path


def main() -> int:
    script = Path(__file__).resolve()
    root = script.parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=root / ".env")
    parser.add_argument("--output-dir", type=Path, default=root / "config/generated")
    parser.add_argument(
        "--allow-non-phone-reachable",
        action="store_true",
        help="test-only: allow loopback/documentation control URLs",
    )
    args = parser.parse_args()
    try:
        path = render(
            root,
            args.env_file,
            args.output_dir,
            allow_non_phone_reachable=args.allow_non_phone_reachable,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
