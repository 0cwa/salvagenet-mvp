#!/usr/bin/env python3
"""Prepare the canonical H02A host-QEMU laboratory inputs.

The helper validates the checked-in Ubuntu profile and immutable image lock,
renders canonical vendor-data, creates a minimal test-only NoCloud layer, and
records the exact QEMU plan before any VM process starts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PROFILE_PATH = ROOT / "profiles/ubuntu-2404-arm64-uefi/profile.json"
LOCK_PATH = ROOT / "profiles/locks/images.lock.json"
RENDERER = ROOT / "tools/profiles/render-guest-init.py"
IMAGE_ID = "ubuntu-2404-arm64-cloud"
PROFILE_ID = "ubuntu-2404-arm64-uefi"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PUBLIC_KEY = re.compile(r"^ssh-ed25519 [A-Za-z0-9+/]+={0,3}(?: [ -~]{1,128})?$")
MAX_TEXT_BYTES = 256 * 1024


class LabError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LabError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LabError(f"JSON root must be an object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def require_command(name: str) -> str:
    value = shutil.which(name)
    if value is None:
        raise LabError(f"missing required command: {name}")
    return value


def canonical_profile(path: Path = PROFILE_PATH) -> dict[str, Any]:
    profile = read_json(path)
    spec = profile.get("spec")
    expected = {
        "apiVersion": "nodehost.example/v1alpha1",
        "kind": "VirtualMachineProfile",
        "profileId": PROFILE_ID,
        "architecture": "aarch64",
        "machineFamily": "virt",
        "acceleration": "tcg",
        "deviceTransport": "pci",
        "cpuModel": "max",
        "bootType": "uefi",
        "systemFormat": "qcow2",
        "writableLayer": "copied-writable",
        "dataFormat": "raw",
        "initializationType": "nocloud-net",
        "networkType": "slirp",
        "recoveryBind": "loopback",
        "recoveryGuestPort": 22,
    }
    try:
        observed = {
            "apiVersion": profile["apiVersion"],
            "kind": profile["kind"],
            "profileId": profile["metadata"]["id"],
            "architecture": spec["architecture"],
            "machineFamily": spec["machine"]["family"],
            "acceleration": spec["machine"]["acceleration"],
            "deviceTransport": spec["machine"]["deviceTransport"],
            "cpuModel": spec["machine"]["cpuModel"],
            "bootType": spec["boot"]["type"],
            "systemFormat": spec["systemDisk"]["format"],
            "writableLayer": spec["systemDisk"]["writableLayer"],
            "dataFormat": spec["dataDisk"]["format"],
            "initializationType": spec["initialization"]["type"],
            "networkType": spec["network"]["primary"]["type"],
            "recoveryBind": spec["network"]["recoverySsh"]["bind"],
            "recoveryGuestPort": spec["network"]["recoverySsh"]["guestPort"],
        }
    except (KeyError, TypeError) as exc:
        raise LabError(f"canonical profile is incomplete: {exc}") from exc
    if observed != expected:
        raise LabError(f"canonical profile contract changed: expected={expected!r} observed={observed!r}")
    checks = set(spec["requirements"]["qualificationChecks"])
    required_checks = {"uefi", "virtio-block", "virtio-net", "serial-console", "cloud-init", "openssh"}
    if not required_checks.issubset(checks):
        raise LabError(f"canonical profile lacks qualification checks: {sorted(required_checks - checks)}")
    return profile


def immutable_image_lock(path: Path = LOCK_PATH) -> dict[str, Any]:
    lock = read_json(path)
    try:
        artifact = lock["artifacts"][IMAGE_ID]
        source = artifact["source"]
        url = source["url"]
        digest = artifact["sha256"]
        size = artifact["sizeBytes"]
    except (KeyError, TypeError) as exc:
        raise LabError(f"Ubuntu image lock is incomplete: {exc}") from exc
    if source.get("kind") != "remote-release":
        raise LabError("Ubuntu image lock must use remote-release")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise LabError("Ubuntu image URL must be HTTPS")
    if "/current/" in url or url.endswith("/current"):
        raise LabError("Ubuntu image URL must be immutable, not current")
    if not SHA256.fullmatch(digest or ""):
        raise LabError("Ubuntu image lock needs an exact SHA-256")
    if not isinstance(size, int) or not 1 <= size <= 64 * 1024**3:
        raise LabError("Ubuntu image lock needs a bounded exact size")
    return {"url": url, "sha256": digest, "sizeBytes": size}


def validate_state_directory(state: Path) -> Path:
    local_root = ROOT / ".local"
    local_root.mkdir(mode=0o700, exist_ok=True)
    if local_root.is_symlink():
        raise LabError("repository .local directory must not be a symlink")
    candidate = state.expanduser()
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    if candidate.is_symlink():
        raise LabError("H02A state directory must not be a symlink")
    resolved_root = local_root.resolve(strict=True)
    resolved = candidate.resolve(strict=False)
    try:
        relative = resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise LabError(f"H02A state directory must remain under {resolved_root}: {resolved}") from exc
    if not relative.parts:
        raise LabError("H02A state directory cannot be the repository .local root")
    current = resolved_root
    for segment in relative.parts:
        current = current / segment
        if current.exists() and current.is_symlink():
            raise LabError(f"H02A state path contains a symlink: {current}")
    return resolved


def verify_image(path: Path, locked: dict[str, Any]) -> None:
    if path.is_symlink() or not path.is_file():
        raise LabError(f"pinned Ubuntu image is missing or unsafe: {path}")
    actual_size = path.stat().st_size
    if actual_size != locked["sizeBytes"]:
        raise LabError(f"Ubuntu image size mismatch: expected={locked['sizeBytes']} actual={actual_size}")
    actual_digest = sha256_file(path)
    if actual_digest != locked["sha256"]:
        raise LabError(f"Ubuntu image digest mismatch: expected={locked['sha256']} actual={actual_digest}")


def download_image(path: Path, locked: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise LabError(f"pinned Ubuntu image path must not be a symlink: {path}")
    if path.exists():
        verify_image(path, locked)
        return
    temporary = path.with_suffix(path.suffix + ".part")
    if temporary.is_symlink():
        raise LabError(f"partial Ubuntu image path must not be a symlink: {temporary}")
    command = [
        require_command("curl"),
        "--fail",
        "--location",
        "--proto",
        "=https",
        "--tlsv1.2",
        "--connect-timeout",
        "30",
        "--max-time",
        "3600",
        "--retry",
        "2",
        "--continue-at",
        "-",
        "--output",
        str(temporary),
        locked["url"],
    ]
    subprocess.run(command, check=True)
    verify_image(temporary, locked)
    temporary.replace(path)


def validate_public_key(text: str) -> str:
    value = text.strip()
    if len(value) > 1024 or not PUBLIC_KEY.fullmatch(value):
        raise LabError("generated SSH public key is not one bounded ssh-ed25519 line")
    return value


def test_user_data(public_key: str) -> str:
    """Return a shell script so user-data cannot override vendor cloud-config lists."""
    key = validate_public_key(public_key)
    return f"""#!/bin/sh
set -eu
install -d -m 0700 -o nodeadmin -g nodeadmin /home/nodeadmin/.ssh
cat > /home/nodeadmin/.ssh/authorized_keys <<'NODEHOST_H02A_KEY'
{key}
NODEHOST_H02A_KEY
chown nodeadmin:nodeadmin /home/nodeadmin/.ssh/authorized_keys
chmod 0600 /home/nodeadmin/.ssh/authorized_keys
cat > /etc/ssh/sshd_config.d/99-nodehost-h02a.conf <<'NODEHOST_H02A_SSHD'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
NODEHOST_H02A_SSHD
chmod 0644 /etc/ssh/sshd_config.d/99-nodehost-h02a.conf
systemctl restart ssh
install -d -m 0755 /var/lib/nodehost
printf 'h02a-ready\\n' > /var/lib/nodehost/h02a-ready
"""


def meta_data(instance_id: str = "nodehost-h02a-ubuntu", hostname: str = "nodehost-h02a") -> str:
    token = re.compile(r"^[a-z0-9][a-z0-9.-]{0,62}$")
    if not token.fullmatch(instance_id) or not token.fullmatch(hostname):
        raise LabError("NoCloud instance ID or hostname is invalid")
    return f"instance-id: {instance_id}\nlocal-hostname: {hostname}\n"


def ensure_text(path: Path, content: str, mode: int = 0o600) -> None:
    encoded = content.encode("utf-8")
    if not encoded or len(encoded) > MAX_TEXT_BYTES or b"\x00" in encoded:
        raise LabError(f"generated text is empty, oversized, or contains NUL: {path.name}")
    temporary = path.with_name(path.name + ".tmp")
    if temporary.is_symlink() or path.is_symlink():
        raise LabError(f"generated text path must not be a symlink: {path}")
    temporary.write_bytes(encoded)
    os.chmod(temporary, mode)
    temporary.replace(path)


def render_vendor_data(state: Path, profile: dict[str, Any]) -> Path:
    relative = profile["spec"]["initialization"]["vendorData"]
    source = ROOT / "profiles" / relative
    destination = state / "vendor-data"
    subprocess.run(
        [sys.executable, str(RENDERER), str(source), "--allow-unresolved", "--output", str(destination)],
        check=True,
    )
    text = destination.read_text(encoding="utf-8")
    if "{{INCLUDE:" in text:
        raise LabError("canonical vendor-data retained an unresolved include")
    if "/var/lib/nodehost/bootstrap.env" not in text:
        raise LabError("canonical vendor-data lost its inert bootstrap condition")
    return destination


def find_firmware_pair() -> tuple[Path, Path]:
    pairs = [
        (
            Path("/usr/share/AAVMF/AAVMF_CODE.fd"),
            Path("/usr/share/AAVMF/AAVMF_VARS.fd"),
        ),
        (
            Path("/usr/share/AAVMF/AAVMF_CODE.ms.fd"),
            Path("/usr/share/AAVMF/AAVMF_VARS.ms.fd"),
        ),
    ]
    for code, variables in pairs:
        if all(path.is_file() and not path.is_symlink() for path in (code, variables)):
            return code, variables
    raise LabError("a matched AAVMF code/vars firmware pair was not found")


def package_fact(path: Path) -> str | None:
    dpkg_query = shutil.which("dpkg-query")
    if dpkg_query is None:
        return None
    owner = subprocess.run(
        [dpkg_query, "-S", str(path)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if owner.returncode != 0 or ":" not in owner.stdout:
        return None
    package = owner.stdout.split(":", 1)[0].strip()
    version = subprocess.run(
        [dpkg_query, "-W", "-f=${Package}=${Version}", package],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return version.stdout.strip() if version.returncode == 0 else package


def firmware_fact(path: Path) -> dict[str, Any]:
    return {
        "sourcePath": str(path),
        "sha256": sha256_file(path),
        "sizeBytes": path.stat().st_size,
        "package": package_fact(path),
    }


def copy_verified(source: Path, destination: Path, expected_digest: str | None = None) -> str:
    if source.is_symlink() or not source.is_file():
        raise LabError(f"copy source is missing or unsafe: {source}")
    if destination.is_symlink():
        raise LabError(f"copy destination must not be a symlink: {destination}")
    shutil.copyfile(source, destination)
    actual = sha256_file(destination)
    expected = expected_digest or sha256_file(source)
    if actual != expected or destination.stat().st_size != source.stat().st_size:
        destination.unlink(missing_ok=True)
        raise LabError(f"copied file identity differs from source: {source.name}")
    return actual


def qemu_command(profile: dict[str, Any], state: Path, ssh_port: int) -> list[str]:
    if not 1024 <= ssh_port <= 65535:
        raise LabError("loopback SSH port must be in 1024..65535")
    spec = profile["spec"]
    memory = max(2048, int(spec["requirements"]["minimumMemoryMiB"]))
    return [
        require_command("qemu-system-aarch64"),
        "-name", "nodehost-h02a",
        "-machine", spec["machine"]["family"],
        "-cpu", spec["machine"]["cpuModel"],
        "-accel", f"{spec['machine']['acceleration']},thread=multi",
        "-smp", "2",
        "-m", str(memory),
        "-nographic",
        "-nodefaults",
        "-no-user-config",
        "-drive", f"if=pflash,format=raw,readonly=on,file={state / 'AAVMF_CODE.fd'}",
        "-drive", f"if=pflash,format=raw,file={state / 'AAVMF_VARS.fd'}",
        "-drive", f"if=none,id=system,format=qcow2,file={state / 'system.qcow2'}",
        "-device", "virtio-blk-pci,drive=system",
        "-drive", f"if=none,id=data,format=raw,file={state / 'data.raw'}",
        "-device", "virtio-blk-pci,drive=data",
        "-drive", f"if=none,id=seed,format=raw,readonly=on,file={state / 'seed.img'}",
        "-device", "virtio-blk-pci,drive=seed",
        "-netdev", f"user,id=net0,hostfwd=tcp:127.0.0.1:{ssh_port}-:22",
        "-device", "virtio-net-pci,netdev=net0",
        "-qmp", f"unix:{state / 'qmp.sock'},server=on,wait=off",
        "-monitor", "none",
        "-serial", f"file:{state / 'serial.log'}",
    ]


def normalized_command(command: list[str], state: Path) -> list[str]:
    state_text = str(state)
    return [value.replace(state_text, "$STATE") for value in command]


def source_fact() -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()
    )
    return {"commit": commit, "dirtyTracked": dirty}


def tool_fact(command: str, *args: str) -> dict[str, Any]:
    path = require_command(command)
    completed = subprocess.run(
        [path, *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return {
        "path": path,
        "version": completed.stdout.splitlines()[0][:256] if completed.stdout else None,
        "exitCode": completed.returncode,
    }


def reset_generated_state(state: Path) -> None:
    retained = {
        "ubuntu-24.04-server-cloudimg-arm64.img",
        "ubuntu-24.04-server-cloudimg-arm64.img.part",
        "evidence",
    }
    for path in state.iterdir():
        if path.name in retained:
            continue
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)


def prepare(state: Path, ssh_port: int) -> dict[str, Any]:
    for name in ("qemu-system-aarch64", "qemu-img", "cloud-localds", "ssh-keygen", "curl", "cp"):
        require_command(name)
    state = validate_state_directory(state)
    state.mkdir(parents=True, exist_ok=True)
    os.chmod(state, 0o700)
    reset_generated_state(state)
    profile = canonical_profile()
    lock = immutable_image_lock()
    base = state / "ubuntu-24.04-server-cloudimg-arm64.img"
    download_image(base, lock)

    private_key = state / "id_ed25519"
    public_key_path = state / "id_ed25519.pub"
    subprocess.run(
        [require_command("ssh-keygen"), "-q", "-t", "ed25519", "-N", "", "-C", "nodehost-h02a", "-f", str(private_key)],
        check=True,
    )
    os.chmod(private_key, 0o600)
    public_key = validate_public_key(public_key_path.read_text(encoding="utf-8"))

    vendor = render_vendor_data(state, profile)
    user = state / "user-data"
    metadata = state / "meta-data"
    ensure_text(user, test_user_data(public_key))
    ensure_text(metadata, meta_data())

    seed = state / "seed.img"
    subprocess.run(
        [require_command("cloud-localds"), "--vendor-data", str(vendor), str(seed), str(user), str(metadata)],
        check=True,
    )

    system = state / "system.qcow2"
    subprocess.run(
        [require_command("cp"), "--reflink=auto", "--sparse=always", str(base), str(system)],
        check=True,
    )
    if system.stat().st_size != lock["sizeBytes"] or sha256_file(system) != lock["sha256"]:
        system.unlink(missing_ok=True)
        raise LabError("copied-writable system disk identity differs from the pinned base")
    info = json.loads(
        subprocess.run(
            [require_command("qemu-img"), "info", "--output=json", str(system)],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout
    )
    if info.get("format") != "qcow2" or info.get("backing-filename"):
        raise LabError("system disk is not an independent copied-writable qcow2")

    data = state / "data.raw"
    data_size = int(profile["spec"]["dataDisk"]["defaultSizeGiB"]) * 1024**3
    subprocess.run([require_command("qemu-img"), "create", "-q", "-f", "raw", str(data), str(data_size)], check=True)
    if data.stat().st_size != data_size:
        raise LabError("raw data disk has the wrong virtual size")

    code_source, vars_source = find_firmware_pair()
    code = state / "AAVMF_CODE.fd"
    variables = state / "AAVMF_VARS.fd"
    code_digest = copy_verified(code_source, code)
    vars_digest = copy_verified(vars_source, variables)

    command = qemu_command(profile, state, ssh_port)
    plan = {
        "schemaVersion": 1,
        "evidenceClass": "host-qemu-preflight",
        "androidHardwareValidated": False,
        "physicalGateEligible": False,
        "guestMeshValidated": False,
        "source": source_fact(),
        "profile": {
            "id": PROFILE_ID,
            "path": str(PROFILE_PATH.relative_to(ROOT)),
            "sha256": sha256_file(PROFILE_PATH),
        },
        "vendorData": {
            "path": str((ROOT / "profiles" / profile["spec"]["initialization"]["vendorData"]).relative_to(ROOT)),
            "renderedSha256": sha256_file(vendor),
        },
        "testUserData": {
            "format": "text/x-shellscript",
            "sha256": sha256_file(user),
        },
        "image": lock,
        "firmware": {
            "code": {**firmware_fact(code_source), "copiedSha256": code_digest},
            "vars": {**firmware_fact(vars_source), "copiedSha256": vars_digest},
        },
        "tools": {
            "qemu": tool_fact("qemu-system-aarch64", "--version"),
            "qemuImg": tool_fact("qemu-img", "--version"),
            "cloudLocalds": tool_fact("cloud-localds", "--help"),
        },
        "lab": {
            "memoryMiB": max(2048, int(profile["spec"]["requirements"]["minimumMemoryMiB"])),
            "vcpus": 2,
            "sshHost": "127.0.0.1",
            "sshPort": ssh_port,
            "systemDiskMode": "copied-writable",
            "qemuCommand": normalized_command(command, state),
        },
    }
    ensure_text(state / "preflight.json", json.dumps(plan, indent=2, sort_keys=True) + "\n")
    ensure_text(state / "qemu-command.json", json.dumps(command, indent=2) + "\n")
    return plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--ssh-port", type=int, default=2222)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        profile = canonical_profile()
        lock = immutable_image_lock()
        if args.validate_only:
            print(json.dumps({"profileId": profile["metadata"]["id"], "image": lock}, indent=2, sort_keys=True))
        else:
            print(json.dumps(prepare(args.state, args.ssh_port), indent=2, sort_keys=True))
        return 0
    except (LabError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"H02A preparation error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
