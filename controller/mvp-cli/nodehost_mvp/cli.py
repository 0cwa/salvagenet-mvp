from __future__ import annotations

import argparse
import json
import secrets
import sys
from pathlib import Path

from .client import NodeHostClient
from .config import ControllerConfig
from .proxy import proxy_ssh


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="phonectl-mvp")
    parser.add_argument("--config", required=True)
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("status")

    apply_vm = subcommands.add_parser("apply-vm")
    apply_vm.add_argument("vm_id")
    apply_vm.add_argument("request_json")
    apply_vm.add_argument("--idempotency-key")

    wait = subcommands.add_parser("wait")
    wait.add_argument("operation_id")
    wait.add_argument("--timeout", type=float, default=600)

    proxy = subcommands.add_parser("proxy-ssh")
    proxy.add_argument("vm_id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = ControllerConfig.load(args.config)
    if args.command == "proxy-ssh":
        return proxy_ssh(config, args.vm_id)

    client = NodeHostClient(config)
    if args.command == "status":
        result = client.status()
    elif args.command == "apply-vm":
        request = json.loads(Path(args.request_json).read_text())
        result = client.apply_vm(
            args.vm_id,
            request,
            args.idempotency_key or secrets.token_urlsafe(24),
        )
    elif args.command == "wait":
        result = client.wait(args.operation_id, args.timeout)
    else:
        raise AssertionError(args.command)

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
