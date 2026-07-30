#!/usr/bin/env python3
"""Validate the complete MVP profile registry, Android assets, and production ownership boundaries."""

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_PROFILE_IDS = {
    "alpine-direct-qualification",
    "ubuntu-2404-arm64-uefi",
    "k3s-worker-lab",
}
FORBIDDEN_FIELDS = {
    "args", "command", "kernelargs", "kernelarguments", "kernelextra", "qemuargs",
    "qemuarguments", "rawqmp", "shell", "shellcommand",
}
COMMON_SPEC_FIELDS = {
    "architecture", "machine", "boot", "systemDisk", "dataDisk",
    "initialization", "network", "health", "requirements",
}
SHELL_MAIN = ROOT / "android/modules/node-shell/src/main/kotlin/org/nodehost/shell"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def walk_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key).lower() for key in value}
        for child in value.values():
            keys.update(walk_keys(child))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for child in value:
            keys.update(walk_keys(child))
        return keys
    return set()


def artifact_ids(profile: dict) -> set[str]:
    boot = profile["spec"]["boot"]
    ids = {profile["spec"]["systemDisk"]["artifact"]}
    ids.update(value for key, value in boot.items() if key.endswith("Artifact"))
    return ids


def package_module():
    path = ROOT / "tools" / "profiles" / "package-assets.py"
    spec = importlib.util.spec_from_file_location("nodehost_profile_packager", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def enforce_production_boundaries() -> None:
    storage = (SHELL_MAIN / "AndroidQemuProfileStorage.kt").read_text(encoding="utf-8")
    assert "VmProfile(" not in storage, "runtime storage must not reconstruct complete profiles"
    assert "when (id.value)" not in storage, "runtime storage must not branch into profile mirrors"
    assert "AndroidPackagedProfileCatalog" in storage, "runtime must use the packaged profile catalog"

    catalog = (SHELL_MAIN / "AndroidPackagedProfileCatalog.kt").read_text(encoding="utf-8")
    assert 'index.json' in catalog, "Android profile loading must consume the packaged registry index"
    assert "EXPECTED_PROFILE_IDS" not in catalog, "Android must not duplicate the packaged profile registry"

    manifest_adapter = SHELL_MAIN / "ArtifactManifest.kt"
    assert manifest_adapter.is_file(), "shared artifact manifest adapter is missing"
    direct_manifest_literals = []
    for path in sorted(SHELL_MAIN.glob("*.kt")):
        if path == manifest_adapter:
            continue
        text = path.read_text(encoding="utf-8")
        if '.manifest.json"' in text or "MANIFEST_KEYS" in text or "MANIFEST_VERSION" in text:
            direct_manifest_literals.append(path.name)
    assert not direct_manifest_literals, (
        "active artifact manifests must be interpreted only by ArtifactManifestStore: "
        + ", ".join(direct_manifest_literals)
    )
    for name in ("AndroidArtifactUploads.kt", "ProductionHostApi.kt", "AndroidQemuProfileStorage.kt"):
        text = (SHELL_MAIN / name).read_text(encoding="utf-8")
        assert "ArtifactManifestStore" in text, f"{name} bypasses the shared artifact manifest adapter"

    app_build = (ROOT / "android/podroid/app/build.gradle.kts").read_text(encoding="utf-8")
    integration = (ROOT / "android/podroid.integration.gradle.kts").read_text(encoding="utf-8")
    assert 'apply(from = rootProject.file("../podroid.integration.gradle.kts"))' in app_build
    assert "verifyNodeHostProfilePackaging" in integration
    assert "package-assets.py" in integration


def main() -> None:
    profiles: dict[str, dict] = {}
    for path in sorted(ROOT.glob("profiles/*/profile.json")):
        profile = load(path)
        profile_id = profile["metadata"]["id"]
        assert path.parent.name == profile_id, f"{path}: directory and metadata id differ"
        assert profile_id not in profiles, f"duplicate profile id: {profile_id}"
        assert set(profile["spec"]) == COMMON_SPEC_FIELDS, f"{profile_id}: profile does not resolve to unified model"
        unsafe = walk_keys(profile) & FORBIDDEN_FIELDS
        assert not unsafe, f"{profile_id}: forbidden fields: {sorted(unsafe)}"
        profiles[profile_id] = profile

    assert set(profiles) == REQUIRED_PROFILE_IDS, "MVP profile registry must contain exactly the three qualified profiles"

    alpine = profiles["alpine-direct-qualification"]
    ubuntu = profiles["ubuntu-2404-arm64-uefi"]
    k3s = profiles["k3s-worker-lab"]
    assert alpine["spec"]["boot"]["type"] == "direct-kernel"
    assert alpine["spec"]["initialization"]["type"] == "legacy-podroid"
    assert ubuntu["spec"]["boot"]["type"] == "uefi"
    assert ubuntu["spec"]["initialization"]["type"] == "nocloud-net"
    assert ubuntu["spec"]["systemDisk"]["writableLayer"] == "copied-writable"
    assert {
        "uefi", "virtio-block", "virtio-net", "serial-console", "cloud-init", "openssh"
    } <= set(ubuntu["spec"]["requirements"]["qualificationChecks"])

    assert k3s["metadata"]["derivedFrom"] == "ubuntu-2404-arm64-uefi"
    for derived_section in ("architecture", "machine", "boot", "systemDisk", "dataDisk", "network", "health"):
        assert k3s["spec"][derived_section] == ubuntu["spec"][derived_section], (
            f"k3s-worker-lab diverges from Ubuntu hardware in {derived_section}"
        )
    checks = set(k3s["spec"]["requirements"]["qualificationChecks"])
    required_checks = {
        "cgroup-v2", "namespaces", "overlayfs", "br-netfilter", "vxlan", "tun",
        "iptables-or-nft", "ip-forwarding", "swap-policy", "minimum-memory",
        "minimum-storage", "tailscale-reachability",
    }
    assert required_checks <= checks

    lock = load(ROOT / "profiles/locks/images.lock.json")
    locked_ids = set(lock["artifacts"])
    referenced_ids = set().union(*(artifact_ids(profile) for profile in profiles.values()))
    assert referenced_ids <= locked_ids, f"unlocked profile artifacts: {sorted(referenced_ids - locked_ids)}"

    for profile in profiles.values():
        vendor_data = ROOT / "profiles" / profile["spec"]["initialization"]["vendorData"]
        assert vendor_data.is_file(), f"missing checked-in vendor data: {vendor_data}"

    packager = package_module()
    expected = packager.expected_assets()
    expected_profile_assets = {f"nodehost/profiles/{profile_id}/profile.json" for profile_id in REQUIRED_PROFILE_IDS}
    assert expected_profile_assets <= set(expected)
    assert "nodehost/profiles/index.json" in expected
    assert "nodehost/profiles/vm-profile.schema.json" in expected
    for path, content in expected.items():
        assert content, f"empty generated profile asset: {path}"
        if path.endswith("vendor-data.yaml") and path != "nodehost/guest-init/alpine-direct/vendor-data.yaml":
            text = content.decode("utf-8")
            assert text.startswith("#cloud-config\n") and "{{" not in text, f"unrendered guest-init asset: {path}"

    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "assets"
        packager.prepare(output)
        generated = {
            path.relative_to(output).as_posix(): path.read_bytes()
            for path in output.rglob("*") if path.is_file()
        }
        assert generated == expected, "generated Android profile assets differ from expected bytes"

    enforce_production_boundaries()
    print("profile registry/package assets/production boundaries OK:", ", ".join(sorted(profiles)))


if __name__ == "__main__":
    main()
