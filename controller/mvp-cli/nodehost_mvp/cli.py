from __future__ import annotations

import argparse
import json
import secrets
import sys
from pathlib import Path
from typing import Any

from .client import ApiError, NodeHostClient
from .config import ControllerConfig
from .proxy import proxy_ssh


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="phonectl-mvp")
    parser.add_argument("--config", help="JSON config; omit to use NODEHOST_* environment variables")
    subcommands = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "capabilities", "profiles", "images", "vms", "operations", "diagnostics"):
        subcommands.add_parser(name)

    get_vm = subcommands.add_parser("get-vm")
    get_vm.add_argument("vm_id")

    import_image = subcommands.add_parser("import-image")
    import_image.add_argument("request_json")
    import_image.add_argument("--idempotency-key")

    apply_vm = subcommands.add_parser("apply-vm")
    apply_vm.add_argument("vm_id")
    apply_vm.add_argument("request_json")
    apply_vm.add_argument("--idempotency-key")

    remove_vm = subcommands.add_parser("remove-vm")
    remove_vm.add_argument("vm_id")
    remove_vm.add_argument("--idempotency-key")

    operation = subcommands.add_parser("operation")
    operation.add_argument("operation_id")

    cancel = subcommands.add_parser("cancel-operation")
    cancel.add_argument("operation_id")
    cancel.add_argument("--idempotency-key")

    revoke = subcommands.add_parser("revoke-controller")
    revoke.add_argument("controller_id")
    revoke.add_argument("--idempotency-key")

    wait = subcommands.add_parser("wait")
    wait.add_argument("operation_id")
    wait.add_argument("--timeout", type=float, default=600)

    proxy = subcommands.add_parser("proxy-ssh")
    proxy.add_argument("vm_id")
    return parser


def _key(value: str | None) -> str:
    return value or secrets.token_urlsafe(24)


def _load_json_object(path: str) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    if len(raw) > 1024 * 1024:
        raise ValueError("request JSON exceeds 1 MiB")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("request JSON must contain an object")
    return value


def run(args: argparse.Namespace) -> Any:
    config = ControllerConfig.load(args.config)
    if args.command == "proxy-ssh":
        return proxy_ssh(config, args.vm_id)

    client = NodeHostClient(config)
    if args.command == "status": return client.status()
    if args.command == "capabilities": return client.capabilities()
    if args.command == "profiles": return client.profiles()
    if args.command == "images": return client.images()
    if args.command == "vms": return client.vms()
    if args.command == "get-vm": return client.vm(args.vm_id)
    if args.command == "import-image": return client.import_image(_load_json_object(args.request_json), _key(args.idempotency_key))
    if args.command == "apply-vm": return client.apply_vm(args.vm_id, _load_json_object(args.request_json), _key(args.idempotency_key))
    if args.command == "remove-vm": return client.remove_vm(args.vm_id, _key(args.idempotency_key))
    if args.command == "operations": return client.operations()
    if args.command == "operation": return client.operation(args.operation_id)
    if args.command == "cancel-operation": return client.cancel_operation(args.operation_id, _key(args.idempotency_key))
    if args.command == "diagnostics": return client.diagnostics()
    if args.command == "revoke-controller": return client.revoke_controller(args.controller_id, _key(args.idempotency_key))
    if args.command == "wait": return client.wait(args.operation_id, args.timeout)
    raise AssertionError(args.command)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run(args)
        if args.command == "proxy-ssh":
            return int(result)
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    except (ApiError, OSError, ValueError, RuntimeError, TimeoutError, json.JSONDecodeError) as exc:
        # Boundary exceptions are designed not to carry headers/configuration.
        print(f"phonectl-mvp: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
