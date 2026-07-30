from __future__ import annotations

import json
from pathlib import Path
import shutil
import time
from typing import Any, Callable

from .config import ConfigError, HilConfig
from .evidence import EvidenceRecorder
from .ports import ControllerPort, DevicePort, MeshLabPort


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot read JSON object {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfigError(f"{path} must contain a JSON object")
    return value


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


def smoke(
    config: HilConfig,
    device: DevicePort,
    controller: ControllerPort,
    recorder: EvidenceRecorder,
) -> None:
    timeout = _scenario_timeout(config, "smoke", 900)
    request_path = config.path("smoke.applyRequest")
    assert request_path is not None
    template = load_object(request_path)

    device.install_apk(config.apk_path)
    device.start_supervisor()
    status = wait_for_controller_status(controller, min(timeout, 120))
    recorder.write_json("host-status-before.json", status)

    profiles = controller.profiles()
    profile_ids = {item.get("id") for item in profiles}
    recorder.assert_that(
        "smoke.profile-present",
        template.get("profileId") in profile_ids,
        f"profile={template.get('profileId')} available={sorted(str(item) for item in profile_ids)}",
    )

    request = dict(template)
    request["generation"] = next_generation(controller.vms(), template)
    request["desiredState"] = "running"
    controller.apply_vm("default", request, timeout)

    wait_until(
        lambda: device.count_qemu_processes() == 1,
        timeout_seconds=timeout,
        description="exactly one QEMU process",
    )
    recorder.assert_that(
        "smoke.one-qemu",
        device.count_qemu_processes() == 1,
        "one QEMU process after start",
    )

    stopped = dict(request)
    stopped["generation"] = request["generation"] + 1
    stopped["desiredState"] = "stopped"
    controller.apply_vm("default", stopped, timeout)
    wait_until(
        lambda: device.count_qemu_processes() == 0,
        timeout_seconds=120,
        description="QEMU process exit after graceful stop",
    )
    recorder.assert_that("smoke.graceful-stop", True, "QEMU process exited after stopped generation")

    restarted = dict(request)
    restarted["generation"] = request["generation"] + 2
    controller.apply_vm("default", restarted, timeout)
    wait_until(
        lambda: device.count_qemu_processes() == 1,
        timeout_seconds=timeout,
        description="one QEMU process after restart",
    )
    recorder.assert_that("smoke.restart-one-qemu", True, "one QEMU process after restart")
    recorder.write_json("host-status-after.json", controller.status())


def mvp(
    config: HilConfig,
    controller: ControllerPort,
    mesh: MeshLabPort,
    recorder: EvidenceRecorder,
) -> None:
    timeout = _scenario_timeout(config, "mvp", 1200)
    settings = config.scenario("mvp")
    host_node = settings.get("hostNodeName")
    guest_node = settings.get("guestNodeName")
    if not isinstance(host_node, str) or not isinstance(guest_node, str):
        raise ConfigError("mvp.hostNodeName and mvp.guestNodeName are required")

    recorder.write_json("headscale-host-nodes.json", mesh.wait_for_node(host_node, timeout))
    recorder.write_json("host-status.json", wait_for_controller_status(controller, min(timeout, 120)))

    image_imports = settings.get("imageImports", [])
    if not isinstance(image_imports, list) or not all(isinstance(item, str) for item in image_imports):
        raise ConfigError("mvp.imageImports must be a list of JSON file paths")
    for item in image_imports:
        path = Path(item)
        if not path.is_absolute():
            path = config.root / path
        controller.import_image(path, timeout)

    required_images = settings.get("requiredImageIds", [])
    if not isinstance(required_images, list) or not all(isinstance(item, str) for item in required_images):
        raise ConfigError("mvp.requiredImageIds must be a list of strings")
    available = {item.get("id") for item in controller.images()}
    missing = [item for item in required_images if item not in available]
    recorder.assert_that(
        "mvp.images-present",
        not missing,
        f"missing={missing} available={sorted(str(item) for item in available)}",
    )

    request_path = config.path("mvp.applyRequest")
    assert request_path is not None
    template = load_object(request_path)
    request = dict(template)
    request["generation"] = next_generation(controller.vms(), template)
    request["desiredState"] = "running"
    controller.apply_vm("default", request, timeout)

    recorder.write_json("headscale-guest-nodes.json", mesh.wait_for_node(guest_node, timeout))
    recorder.assert_that(
        "mvp.distinct-mesh-identities",
        host_node != guest_node,
        f"host={host_node} guest={guest_node}",
    )

    guest_target = settings.get("guestSshTarget")
    if not isinstance(guest_target, str):
        raise ConfigError("mvp.guestSshTarget is required")
    check_command = str(settings.get("guestCheckCommand", "true"))
    controller.guest_ssh(guest_target, check_command, timeout)
    recorder.assert_that("mvp.guest-ssh", True, f"ordinary SSH succeeded: {guest_target}")

    recovery_user = str(settings.get("recoveryUser", "nodeadmin"))
    disable = settings.get("guestMeshDisableCommand")
    restore = settings.get("guestMeshRestoreCommand")
    if not isinstance(disable, str) or not disable:
        raise ConfigError("mvp.guestMeshDisableCommand is required for recovery-path evidence")
    if not isinstance(restore, str) or not restore:
        raise ConfigError("mvp.guestMeshRestoreCommand is required for recovery-path cleanup")
    controller.guest_ssh(guest_target, disable, timeout)
    time.sleep(float(settings.get("guestMeshDownSettleSeconds", 5)))
    ordinary_failed = False
    try:
        controller.guest_ssh(guest_target, check_command, min(timeout, 30))
    except Exception:
        ordinary_failed = True
    recorder.assert_that(
        "mvp.guest-mesh-disabled",
        ordinary_failed,
        "ordinary guest-mesh SSH failed after disabling guest Tailscale",
    )

    controller.recovery_ssh("default", recovery_user, check_command, timeout)
    recorder.assert_that("mvp.recovery-ssh", True, "host-mediated recovery SSH succeeded")
    controller.recovery_ssh("default", recovery_user, restore, timeout)


def resilience(
    config: HilConfig,
    device: DevicePort,
    controller: ControllerPort,
    recorder: EvidenceRecorder,
) -> None:
    timeout = _scenario_timeout(config, "resilience", 600)
    settings = config.scenario("resilience")

    wait_until(
        lambda: device.count_qemu_processes() == 1,
        timeout_seconds=timeout,
        description="running QEMU baseline",
    )
    recorder.assert_that("resilience.baseline-one-qemu", True, "one QEMU process before disturbances")

    device.stop_service()
    device.start_supervisor()
    wait_until(
        lambda: device.count_qemu_processes() == 1,
        timeout_seconds=timeout,
        description="QEMU after service restart",
    )
    wait_for_controller_status(controller, min(timeout, 120))
    recorder.assert_that(
        "resilience.service-restart",
        True,
        "service restart preserved/reconciled one QEMU process",
    )

    device.kill_qemu()
    wait_until(
        lambda: device.count_qemu_processes() == 1,
        timeout_seconds=timeout,
        description="QEMU reconciliation after child kill",
    )
    recorder.assert_that("resilience.qemu-restart", True, "QEMU child was recreated exactly once")

    offline_seconds = float(settings.get("controllerOfflineSeconds", 15))
    time.sleep(offline_seconds)
    recorder.assert_that(
        "resilience.controller-offline",
        device.count_qemu_processes() == 1,
        f"one QEMU process remained while controller made no requests for {offline_seconds}s",
    )

    allow_reboot = settings.get("allowReboot", False)
    if allow_reboot is True:
        device.reboot(float(settings.get("rebootTimeoutSeconds", 240)))
        wait_until(
            lambda: device.count_qemu_processes() == 1,
            timeout_seconds=timeout,
            description="QEMU after reboot",
        )
        wait_for_controller_status(controller, min(timeout, 120))
        recorder.assert_that(
            "resilience.reboot",
            True,
            "host API and one QEMU process returned after reboot",
        )
    else:
        recorder.assertions.append(
            {
                "id": "resilience.reboot",
                "passed": False,
                "skipped": True,
                "detail": "resilience.allowReboot is false",
            }
        )
