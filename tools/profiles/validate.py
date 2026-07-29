#!/usr/bin/env python3
"""Validate canonical profiles and their trusted guest-init assets."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


root = Path(__file__).resolve().parents[2]
profiles: list[str] = []
for path in sorted(root.glob("profiles/*/profile.json")):
    data = json.loads(path.read_text(encoding="utf-8"))
    profiles.append(data["metadata"]["id"])
    assert data["apiVersion"] == "nodehost.example/v1alpha1"
    assert data["kind"] == "VirtualMachineProfile"
    text = path.read_text(encoding="utf-8").lower()
    for forbidden in ("qemuargs", "kernelargs", "shellcommand", "rawqmp"):
        assert forbidden not in text, f"{path}: forbidden field {forbidden}"

required = {
    "alpine-direct-qualification",
    "ubuntu-2404-arm64-uefi",
    "k3s-worker-lab",
}
assert required <= set(profiles), f"missing profiles: {required - set(profiles)}"

renderer_path = root / "tools/profiles/render-guest-init.py"
spec = importlib.util.spec_from_file_location("guest_init_renderer", renderer_path)
assert spec and spec.loader
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)

for relative in (
    "profiles/guest-init/ubuntu/vendor-data.yaml",
    "profiles/guest-init/k3s-worker-lab/vendor-data.yaml",
):
    rendered = renderer.render(root / relative, {}, allow_unresolved=False)
    assert rendered.startswith("#cloud-config\n"), f"{relative}: not cloud-config"
    assert "{{" not in rendered, f"{relative}: unresolved template marker"
    assert "PasswordAuthentication no" in rendered, f"{relative}: password SSH not disabled"

sample_values = {
    "METADATA_BASE": "http://10.0.2.2:8123/v1/bootstrap/sample/",
    "BOOTSTRAP_TOKEN": "safe-validation-token_123",
    "INSTANCE_ID": "nodehost-validation-1",
    "HOSTNAME": "worker-validation-1",
}
for relative in (
    "profiles/guest-init/ubuntu/user-data.template.yaml",
    "profiles/guest-init/common/meta-data.template.yaml",
):
    rendered = renderer.render(root / relative, sample_values, allow_unresolved=False)
    assert "{{" not in rendered, f"{relative}: unresolved deployment value"

qualifier = (root / "profiles/guest-init/k3s-worker-lab/qualify-k3s.sh").read_text(
    encoding="utf-8"
)
assert "joinedCluster: false" in qualifier
assert "get.k3s.io" not in qualifier
assert "k3s server" not in qualifier and "k3s agent" not in qualifier

print(f'profiles OK: {", ".join(profiles)}; guest-init assets OK')
