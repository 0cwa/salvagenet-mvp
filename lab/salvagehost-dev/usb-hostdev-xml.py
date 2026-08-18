#!/usr/bin/env python3
"""Small, dependency-free libvirt USB hostdev XML inspector.

The reconciler deliberately keeps persistent identity XML and live attach XML
separate.  This helper provides strict exit codes so shell code does not have
to decide whether an unrelated USB hostdev is safe to detach.
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child(element: ET.Element, name: str) -> ET.Element | None:
    for item in element:
        if local_name(item.tag) == name:
            return item
    return None


def source_info(hostdev: ET.Element) -> dict[str, str | None]:
    source = child(hostdev, "source")
    guest_address = child(hostdev, "address")
    guest_bus = guest_address.get("bus") if guest_address is not None else None
    guest_port = guest_address.get("port") if guest_address is not None else None
    if source is None:
        return {"vendor": None, "product": None, "bus": None, "device": None, "guest_bus": guest_bus, "guest_port": guest_port}
    vendor = child(source, "vendor")
    product = child(source, "product")
    address = child(source, "address")
    return {
        "managed": hostdev.get("managed"),
        "vendor": (vendor.get("id", "").lower().removeprefix("0x") if vendor is not None else None),
        "product": (product.get("id", "").lower().removeprefix("0x") if product is not None else None),
        "bus": address.get("bus") if address is not None else None,
        "device": address.get("device") if address is not None else None,
        "guest_bus": guest_bus,
        "guest_port": guest_port,
        "startupPolicy": source.get("startupPolicy"),
        "guestReset": source.get("guestReset"),
    }


def usb_hostdevs(root: ET.Element) -> list[ET.Element]:
    return [
        element
        for element in root.iter()
        if local_name(element.tag) == "hostdev" and element.get("type") == "usb"
    ]


def matching(root: ET.Element, vendor: str, product: str) -> list[tuple[ET.Element, dict[str, str | None]]]:
    vendor = vendor.lower().removeprefix("0x")
    product = product.lower().removeprefix("0x")
    result = []
    for element in usb_hostdevs(root):
        info = source_info(element)
        if info["vendor"] == vendor and info["product"] == product:
            result.append((element, info))
    return result


def load(path: Path) -> ET.Element:
    try:
        return ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        print(f"cannot parse {path}: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def check_persistent(args: argparse.Namespace) -> int:
    root = load(Path(args.xml))
    found = matching(root, args.vendor, args.product)
    if len(found) == 0:
        print("persistent USB hostdev is absent", file=sys.stderr)
        return 1
    if len(found) != 1:
        print(f"persistent USB hostdev identity is ambiguous ({len(found)} matches)", file=sys.stderr)
        return 2
    element, info = found[0]
    if info["bus"] is not None or info["device"] is not None:
        print("persistent USB hostdev contains a transient source bus/device address", file=sys.stderr)
        return 2
    if info["managed"] != "yes":
        print("persistent USB hostdev managed state does not match configuration", file=sys.stderr)
        return 1
    if info["startupPolicy"] != args.startup_policy:
        print("persistent USB hostdev startupPolicy does not match configuration", file=sys.stderr)
        return 1
    if info["guestReset"] != args.guest_reset:
        print("persistent USB hostdev guestReset does not match configuration", file=sys.stderr)
        return 1
    print(json.dumps({"state": "current", "source": info}, sort_keys=True))
    return 0


def check_live(args: argparse.Namespace) -> int:
    root = load(Path(args.xml))
    found = matching(root, args.vendor, args.product)
    expected_bus = str(args.bus)
    expected_device = str(args.device)
    if len(found) == 1:
        _, info = found[0]
    elif len(found) > 1:
        print(f"live USB hostdev identity is ambiguous ({len(found)} matches)", file=sys.stderr)
        return 2
    else:
        candidates = []
        for element in usb_hostdevs(root):
            info = source_info(element)
            if (
                args.guest_bus is not None
                and args.guest_port is not None
                and info["guest_bus"] == str(args.guest_bus)
                and info["guest_port"] == str(args.guest_port)
            ):
                candidates.append(info)
        if len(candidates) != 1:
            print("live USB hostdev is absent or cannot be identified safely", file=sys.stderr)
            return 1 if not candidates else 2
        info = candidates[0]
    if info["bus"] == expected_bus and info["device"] == expected_device:
        print(json.dumps({"state": "current", "source": info}, sort_keys=True))
        return 0
    print(
        json.dumps(
            {"state": "stale", "source": info, "expected_bus": expected_bus, "expected_device": expected_device},
            sort_keys=True,
        ),
        file=sys.stderr,
    )
    return 3


def extract(args: argparse.Namespace) -> int:
    root = load(Path(args.xml))
    found = matching(root, args.vendor, args.product)
    if not found and args.guest_bus is not None and args.guest_port is not None:
        found = [
            (element, source_info(element))
            for element in usb_hostdevs(root)
            if source_info(element)["guest_bus"] == str(args.guest_bus)
            and source_info(element)["guest_port"] == str(args.guest_port)
        ]
    if len(found) == 0:
        print("cannot extract absent live USB hostdev", file=sys.stderr)
        return 1
    if len(found) != 1:
        print(f"cannot extract ambiguous live USB hostdev ({len(found)} matches)", file=sys.stderr)
        return 2
    ET.register_namespace("", "")
    print(ET.tostring(found[0][0], encoding="unicode"))
    return 0


def guest_address(args: argparse.Namespace) -> int:
    root = load(Path(args.xml))
    found = matching(root, args.vendor, args.product)
    if len(found) != 1:
        print("cannot resolve one configured guest USB address", file=sys.stderr)
        return 1
    _, info = found[0]
    if info["guest_bus"] is None or info["guest_port"] is None:
        print("configured hostdev has no guest USB address", file=sys.stderr)
        return 1
    print(f"{info['guest_bus']}:{info['guest_port']}")
    return 0


def check_absent(args: argparse.Namespace) -> int:
    root = load(Path(args.xml))
    found = matching(root, args.vendor, args.product)
    if found:
        print(f"persistent USB hostdev present ({len(found)} matches)", file=sys.stderr)
        return 1
    print(json.dumps({"state": "absent"}, sort_keys=True))
    return 0


def guest_address_by_source(args: argparse.Namespace) -> int:
    root = load(Path(args.xml))
    matches = []
    for element in usb_hostdevs(root):
        info = source_info(element)
        if info["bus"] == str(args.bus) and info["device"] == str(args.device):
            matches.append(info)
    if len(matches) != 1 or matches[0]["guest_bus"] is None or matches[0]["guest_port"] is None:
        print("cannot resolve one guest USB address for the current source", file=sys.stderr)
        return 1
    print(f"{matches[0]['guest_bus']}:{matches[0]['guest_port']}")
    return 0


def check_source_address(args: argparse.Namespace) -> int:
    root = load(Path(args.xml))
    matches = [
        source_info(element)
        for element in usb_hostdevs(root)
        if source_info(element)["bus"] == str(args.bus)
        and source_info(element)["device"] == str(args.device)
    ]
    if len(matches) != 1:
        print("current USB source address is absent or ambiguous", file=sys.stderr)
        return 1
    print(json.dumps({"state": "current", "source": matches[0]}, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    persistent = subparsers.add_parser("check-persistent")
    persistent.add_argument("--xml", required=True)
    persistent.add_argument("--vendor", required=True)
    persistent.add_argument("--product", required=True)
    persistent.add_argument("--startup-policy", required=True)
    persistent.add_argument("--guest-reset", required=True)
    persistent.set_defaults(function=check_persistent)

    live = subparsers.add_parser("check-live")
    live.add_argument("--xml", required=True)
    live.add_argument("--vendor", required=True)
    live.add_argument("--product", required=True)
    live.add_argument("--bus", required=True)
    live.add_argument("--device", required=True)
    live.add_argument("--guest-bus")
    live.add_argument("--guest-port")
    live.set_defaults(function=check_live)

    extract_parser = subparsers.add_parser("extract")
    extract_parser.add_argument("--xml", required=True)
    extract_parser.add_argument("--vendor", required=True)
    extract_parser.add_argument("--product", required=True)
    extract_parser.add_argument("--guest-bus")
    extract_parser.add_argument("--guest-port")
    extract_parser.set_defaults(function=extract)

    address_parser = subparsers.add_parser("guest-address")
    address_parser.add_argument("--xml", required=True)
    address_parser.add_argument("--vendor", required=True)
    address_parser.add_argument("--product", required=True)
    address_parser.set_defaults(function=guest_address)

    absent = subparsers.add_parser("check-absent")
    absent.add_argument("--xml", required=True)
    absent.add_argument("--vendor", required=True)
    absent.add_argument("--product", required=True)
    absent.set_defaults(function=check_absent)

    source_address = subparsers.add_parser("guest-address-by-source")
    source_address.add_argument("--xml", required=True)
    source_address.add_argument("--bus", required=True)
    source_address.add_argument("--device", required=True)
    source_address.set_defaults(function=guest_address_by_source)

    source_check = subparsers.add_parser("check-source-address")
    source_check.add_argument("--xml", required=True)
    source_check.add_argument("--bus", required=True)
    source_check.add_argument("--device", required=True)
    source_check.set_defaults(function=check_source_address)

    args = parser.parse_args()
    return args.function(args)


if __name__ == "__main__":
    raise SystemExit(main())
