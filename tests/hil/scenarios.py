from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import time
from typing import Any, Callable

from .config import ConfigError, HilConfig
from .evidence import EvidenceRecorder
from .ports import ControllerPort, DevicePort, MeshLabPort


ARTIFACT_ID = re.compile(r"^[a-z0-9][a-z0-9.-]{0,127}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot read JSON object {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfigError(f"{path} must contain a JSON object")
    return value


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_artifact_set(config: HilConfig) -> list[dict[str, Any]]:
    path = config.path("mvp.artifactSet", required=False)
    if path is None:
        return []
    root = load_object(path)
    if root.get("schemaVersion") != 1 or set(root) != {"schemaVersion", "artifacts"}:
        raise ConfigError("artifact set must contain exactly schemaVersion=1 and artifacts")
    values = root.get("artifacts")
    if not isinstance(values, list) or len(values) > 16:
        raise ConfigError("artifact set must contain at most 16 artifacts")
    result: list[dict[str, Any]] = []
    ids: set[str] = set()
    for index, value in enumerate(values):
        if not isinstance(value, dict) or set(value) != {"id", "path", "sha256", "sizeBytes"}:
            raise ConfigError(f"artifact set entry {index} has invalid fields")
        artifact_id = value.get("id")
        digest = value.get("sha256")
        size = value.get("sizeBytes")
        raw_path = value.get("path")
        if not isinstance(artifact_id, str) or not ARTIFACT_ID.fullmatch(artifact_id):
            raise ConfigError(f"artifact set entry {index} has an invalid id")
        if artifact_id in ids:
            raise ConfigError(f"artifact set contains duplicate id: {artifact_id}")
        ids.add(artifact_id)
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            raise ConfigError(f"artifact set entry {index} has an invalid sha256")
        if not isinstance(size, int) or size < 1 or size > 64 * 1024 * 1024 * 1024:
            raise ConfigError(f"artifact set entry {index} has an invalid sizeBytes")
        if not isinstance(raw_path, str) or not raw_path:
            raise ConfigError(f"artifact set entry {index} has an invalid path")
        artifact_path = Path(raw_path)
        if not artifact_path.is_absolute():
            artifact_path = config.root / artifact_path
        if not artifact_path.is_file():
            raise ConfigError(f"artifact payload is missing: {artifact_path}")
        if artifact_path.stat().st_size != size:
            raise ConfigError(f"artifact payload size mismatch: {artifact_id}")
        if file_sha256(artifact_path) != digest:
            raise ConfigError(f"artifact payload digest mismatch: {artifact_id}")
        result.append({"id": artifact_id, "path": artifact_path, "sha256": digest, "sizeBytes": size})
    return result


def next_generation(vms: list[dict[str, Any]], template: dict[str, Any]) -> int:
    generations = [item.get("generation") for item in vms if isinstance(item.get("generation"), int)]
    template_generation = template.get("generation")
    if not isinstance(template_generation, int) or template_generation < 1:
        raise ConfigError("apply request generation must be a positive integer")
    return max([template_generation, *[generation + 1 for generation in generations]])


def wait_until(
    predicate: Callable[[], bool],
    *,
    timeout_seconds: float,
    description: str,
    interval_seconds: float = 2,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(interval_seconds)
    raise TimeoutError(f"timed out waiting for {description}")


def _scenario_timeout(config: HilConfig, name: str, default: float) -> float:
    value = config.scenario(name).get("timeoutSeconds", default)
    if not isinstance(value, (int, float)) or value <= 0:
        raise ConfigError(f"{name}.timeoutSeconds must be positive")
    return float(value)


def wait_for_controller_status(controller: ControllerPort, timeout_seconds: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            return controller.status()
        except Exception as exc:
            last_error = exc
            time.sleep(2)
    raise TimeoutError(f"Host API did not become ready: {last_error}")


def controller_is_unavailable(controller: ControllerPort) -> bool:
    try:
        controller.status()
    except Exception:
        return True
    return False


def doctor(config: HilConfig, device: DevicePort, recorder: EvidenceRecorder) -> None:
    required = [config.apk_path, config.controller_path, config.controller_config]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise ConfigError(f"required HIL files are missing: {missing}")
    if shutil.which("ssh") is None:
        raise ConfigError("OpenSSH client is not installed")
    facts = device.doctor()
    recorder.write_json("device-facts.json", facts)
    recorder.assert_that("hil.required-files", True, "APK, controller, and controller config are present")
    recorder.assert_that("hil.ssh-installed", True, "OpenSSH client available")
    recorder.assert_that("hil.device-authorized", True, "configured ADB device is connected and authorized")


def smoke(config: HilConfig, device: DevicePort, controller: ControllerPort, recorder: EvidenceRecorder) -> None:
    timeout = _scenario_timeout(config, "smoke", 900)
    request_path = config.path("smoke.applyRequest")
    assert request_path is not None
    template = load_object(request_path)

    device.install_apk(config.apk_path)
    device.start_supervisor()
    status = wait_for_controller_status(controller, min(timeout, 120))
    recorder.write_json("host-status-before.json", status)

    capabilities = controller.capabilities()
    profiles = controller.profiles()
    recorder.write_json("capabilities.json", capabilities)
    recorder.write_json("profiles.json", profiles)
    profile_ids = {item.get("id") for item in profiles}
    recorder.assert_that(
        "smoke.profile-present",
        template.get("profileId") in profile_ids,
        f"profile={template.get('profileId')} available={sorted(str(item) for item in profile_ids)}",
    )

    current_vms = controller.vms()
    recorder.write_json("vms-before.json", current_vms)
    request = dict(template)
    request["generation"] = next_generation(current_vms, template)
    request["desiredState"] = "running"
    recorder.write_json("desired-vm.json", request)
    controller.apply_vm("default", request, timeout)

    wait_until(lambda: device.count_qemu_processes() == 1, timeout_seconds=timeout, description="one QEMU process")
    recorder.assert_that("smoke.one-qemu", device.count_qemu_processes() == 1, "one QEMU process after start")

    stopped = dict(request)
    stopped["generation"] = request["generation"] + 1
    stopped["desiredState"] = "stopped"
    controller.apply_vm("default", stopped, timeout)
    wait_until(lambda: device.count_qemu_processes() == 0, timeout_seconds=120, description="QEMU exit")
    recorder.assert_that("smoke.graceful-stop", True, "QEMU process exited after stopped generation")

    restarted = dict(request)
    restarted["generation"] = request["generation"] + 2
    controller.apply_vm("default", restarted, timeout)
    wait_until(lambda: device.count_qemu_processes() == 1, timeout_seconds=timeout, description="QEMU restart")
    recorder.assert_that("smoke.restart-one-qemu", True, "one QEMU process after restart")
    recorder.write_json("vms-after.json", controller.vms())
    recorder.write_json("host-status-after.json", controller.status())


def mvp(config: HilConfig, controller: ControllerPort, mesh: MeshLabPort, recorder: EvidenceRecorder) -> None:
    timeout = _scenario_timeout(config, "mvp", 1200)
    settings = config.scenario("mvp")
    host_node = settings.get("hostNodeName")
    guest_node = settings.get("guestNodeName")
    if not isinstance(host_node, str) or not isinstance(guest_node, str):
        raise ConfigError("mvp.hostNodeName and mvp.guestNodeName are required")

    recorder.write_json("headscale-host-nodes.json", mesh.wait_for_node(host_node, timeout))
    recorder.assert_that("mvp.host-mesh", True, f"exact host node observed: {host_node}")
    recorder.write_json("host-status.json", wait_for_controller_status(controller, min(timeout, 120)))
    recorder.assert_that("mvp.host-api", True, "authenticated Host API returned status")
    recorder.write_json("capabilities.json", controller.capabilities())
    recorder.write_json("profiles.json", controller.profiles())

    available_by_id = {
        item.get("id"): item for item in controller.images() if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    artifact_set = load_artifact_set(config)
    if artifact_set:
        recorder.write_json(
            "artifact-set.json",
            [{key: item[key] for key in ("id", "sha256", "sizeBytes")} for item in artifact_set],
        )
    for item in artifact_set:
        existing = available_by_id.get(item["id"])
        if existing and existing.get("sha256") == item["sha256"] and existing.get("sizeBytes") == item["sizeBytes"]:
            continue
        uploaded = controller.upload_image(item["id"], item["path"], item["sha256"], timeout)
        if uploaded.get("id") != item["id"] or uploaded.get("sha256") != item["sha256"]:
            raise AssertionError(f"uploaded artifact identity mismatch: {item['id']}")

    image_imports = settings.get("imageImports", [])
    if not isinstance(image_imports, list) or not all(isinstance(item, str) for item in image_imports):
        raise ConfigError("mvp.imageImports must be a list of JSON file paths")
    for item in image_imports:
        path = Path(item)
        if not path.is_absolute():
            path = config.root / path
        controller.import_image(path, timeout)

    images = controller.images()
    recorder.write_json("images.json", images)
    required_images = settings.get("requiredImageIds", [])
    if not isinstance(required_images, list) or not all(isinstance(item, str) for item in required_images):
        raise ConfigError("mvp.requiredImageIds must be a list of strings")
    available = {item.get("id") for item in images}
    missing = [item for item in required_images if item not in available]
    recorder.assert_that("mvp.images-present", not missing, f"missing={missing}")

    request_path = config.path("mvp.applyRequest")
    assert request_path is not None
    template = load_object(request_path)
    current_vms = controller.vms()
    recorder.write_json("vms-before.json", current_vms)
    request = dict(template)
    request["generation"] = next_generation(current_vms, template)
    request["desiredState"] = "running"
    recorder.write_json("desired-vm.json", request)
    controller.apply_vm("default", request, timeout)
    recorder.write_json("vms-after.json", controller.vms())
    recorder.assert_that("mvp.vm-apply", True, f"VM generation {request['generation']} succeeded")

    recorder.write_json("headscale-guest-nodes.json", mesh.wait_for_node(guest_node, timeout))
    recorder.assert_that("mvp.guest-mesh", True, f"exact guest node observed: {guest_node}")
    recorder.assert_that("mvp.distinct-mesh-identities", host_node != guest_node, "host and guest names differ")

    guest_target = settings.get("guestSshTarget")
    if not isinstance(guest_target, str):
        raise ConfigError("mvp.guestSshTarget is required")
    check_command = str(settings.get("guestCheckCommand", "true"))
    controller.guest_ssh(guest_target, check_command, timeout)
    recorder.assert_that("mvp.guest-ssh", True, f"ordinary SSH succeeded: {guest_target}")

    recovery_user = str(settings.get("recoveryUser", "nodeadmin"))
    disable = settings.get("guestMeshDisableCommand")
    restore = settings.get("guestMeshRestoreCommand")
    if not isinstance(disable, str) or not disable or not isinstance(restore, str) or not restore:
        raise ConfigError("guest mesh disable and restore commands are required")
    mesh_disabled = False
    primary_failed = False
    try:
        controller.guest_ssh(guest_target, disable, timeout)
        mesh_disabled = True
        time.sleep(float(settings.get("guestMeshDownSettleSeconds", 5)))
        ordinary_failed = False
        try:
            controller.guest_ssh(guest_target, check_command, min(timeout, 30))
        except Exception:
            ordinary_failed = True
        recorder.assert_that("mvp.guest-mesh-disabled", ordinary_failed, "ordinary SSH failed with guest mesh down")
        controller.recovery_ssh("default", recovery_user, check_command, timeout)
        recorder.assert_that("mvp.recovery-ssh", True, "host-mediated recovery SSH succeeded")
    except BaseException:
        primary_failed = True
        raise
    finally:
        if mesh_disabled:
            try:
                controller.recovery_ssh("default", recovery_user, restore, timeout)
                recorder.assertions.append(
                    {"id": "mvp.cleanup-guest-mesh", "passed": True, "detail": "guest mesh restored"}
                )
            except Exception as cleanup_error:
                recorder.assertions.append(
                    {"id": "mvp.cleanup-guest-mesh", "passed": False, "detail": str(cleanup_error)}
                )
                if not primary_failed:
                    raise RuntimeError("guest mesh cleanup failed") from cleanup_error


def resilience(config: HilConfig, device: DevicePort, controller: ControllerPort, recorder: EvidenceRecorder) -> None:
    timeout = _scenario_timeout(config, "resilience", 600)
    settings = config.scenario("resilience")

    wait_until(lambda: device.count_qemu_processes() == 1, timeout_seconds=timeout, description="QEMU baseline")
    recorder.assert_that("resilience.baseline-one-qemu", True, "one QEMU process before disturbances")

    device.stop_service()
    device.start_supervisor()
    wait_until(lambda: device.count_qemu_processes() == 1, timeout_seconds=timeout, description="QEMU after service restart")
    wait_for_controller_status(controller, min(timeout, 120))
    recorder.assert_that("resilience.service-restart", True, "service restart reconciled one QEMU process")

    device.kill_qemu()
    wait_until(lambda: device.count_qemu_processes() == 1, timeout_seconds=timeout, description="QEMU recreation")
    recorder.assert_that("resilience.qemu-restart", True, "QEMU child was recreated exactly once")

    offline_seconds = float(settings.get("controllerOfflineSeconds", 15))
    isolated = controller.set_controller_reachable(False)
    if isolated:
        try:
            wait_until(
                lambda: controller_is_unavailable(controller),
                timeout_seconds=min(60, timeout),
                description="controller path to become unavailable",
            )
            time.sleep(offline_seconds)
            recorder.assert_that(
                "resilience.controller-unavailable",
                device.count_qemu_processes() == 1,
                f"one QEMU process remained during {offline_seconds}s of configured controller unavailability",
            )
        finally:
            controller.set_controller_reachable(True)
            recorder.assertions.append(
                {"id": "resilience.cleanup-controller", "passed": True, "detail": "controller path restored"}
            )
        wait_for_controller_status(controller, min(timeout, 120))
        recorder.assert_that("resilience.controller-restored", True, "controller path recovered")
    else:
        time.sleep(offline_seconds)
        recorder.assert_that(
            "resilience.controller-silent",
            device.count_qemu_processes() == 1,
            f"one QEMU process remained while no controller requests were made for {offline_seconds}s",
        )
        recorder.assertions.append(
            {
                "id": "resilience.controller-unavailable",
                "passed": False,
                "skipped": True,
                "detail": "controller isolation commands are not configured",
            }
        )

    if settings.get("allowReboot", False) is True:
        device.reboot(float(settings.get("rebootTimeoutSeconds", 240)))
        wait_until(lambda: device.count_qemu_processes() == 1, timeout_seconds=timeout, description="QEMU after reboot")
        wait_for_controller_status(controller, min(timeout, 120))
        recorder.assert_that("resilience.reboot", True, "Host API and one QEMU process returned after reboot")
    else:
        recorder.assertions.append(
            {"id": "resilience.reboot", "passed": False, "skipped": True, "detail": "allowReboot is false"}
        )
