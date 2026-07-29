from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time
from typing import Any

from .config import HilConfig
from .evidence import EvidenceRecorder


class SetupBlocked(RuntimeError):
    pass


class CommandFailed(RuntimeError):
    def __init__(self, argv: list[str], returncode: int, stderr: str):
        super().__init__(f"command failed ({returncode}): {shlex.join(argv)}: {stderr.strip()}")
        self.argv = argv
        self.returncode = returncode


class CommandRunner:
    def __init__(self, root: Path, evidence: EvidenceRecorder | None = None):
        self.root = root
        self.evidence = evidence

    def run(
        self,
        argv: list[str],
        *,
        timeout: float = 120,
        check: bool = True,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        started = time.monotonic()
        try:
            result = subprocess.run(
                argv,
                cwd=self.root,
                input=input_text,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            raise SetupBlocked(f"command not found: {argv[0]}") from exc
        except subprocess.TimeoutExpired as exc:
            if self.evidence:
                self.evidence.record_command(argv, 124, timeout, exc.stdout or "", exc.stderr or "")
            raise TimeoutError(f"command timed out after {timeout}s: {shlex.join(argv)}") from exc
        duration = time.monotonic() - started
        if self.evidence:
            self.evidence.record_command(argv, result.returncode, duration, result.stdout, result.stderr)
        if check and result.returncode != 0:
            raise CommandFailed(argv, result.returncode, result.stderr)
        return result


class AdbDevice:
    def __init__(self, config: HilConfig, runner: CommandRunner):
        self.config = config
        self.runner = runner

    def _adb(self, *args: str, timeout: float = 120, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self.runner.run(["adb", "-s", self.config.device_serial, *args], timeout=timeout, check=check)

    def _shell(self, command: str, *, timeout: float = 120, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self._adb("shell", command, timeout=timeout, check=check)

    def doctor(self) -> dict[str, Any]:
        if shutil.which("adb") is None:
            raise SetupBlocked("adb is not installed")
        devices = self.runner.run(["adb", "devices", "-l"], timeout=20).stdout
        matching = [line for line in devices.splitlines() if line.startswith(self.config.device_serial + "\t")]
        if not matching:
            raise SetupBlocked(f"configured device is not connected: {self.config.device_serial}")
        if "\tdevice" not in matching[0]:
            raise SetupBlocked(f"configured device is not authorized: {matching[0]}")
        return self.collect_facts()

    def install_apk(self, apk: Path) -> None:
        if not apk.is_file():
            raise SetupBlocked(f"APK not found: {apk}")
        self._adb("install", "-r", str(apk), timeout=300)

    def start_supervisor(self) -> None:
        self._shell(f"am start-foreground-service -n {shlex.quote(self.config.supervisor_component)}")

    def launch_app(self) -> None:
        self._shell(
            f"monkey -p {shlex.quote(self.config.package_name)} -c android.intent.category.LAUNCHER 1 >/dev/null"
        )

    def stop_service(self) -> None:
        self._shell(
            f"am stopservice -n {shlex.quote(self.config.supervisor_component)}",
            check=False,
        )

    def kill_qemu(self) -> None:
        script = f"pids=$(pidof {shlex.quote(self.config.qemu_pattern)}); test -n \"$pids\"; kill -9 $pids"
        command = f"run-as {shlex.quote(self.config.package_name)} sh -c {shlex.quote(script)}"
        self._shell(command)

    def count_qemu_processes(self) -> int:
        result = self._shell("ps -A -o PID,NAME,ARGS", check=False)
        if result.returncode != 0:
            result = self._shell("ps -A")
        return sum(1 for line in result.stdout.splitlines() if self.config.qemu_pattern in line)

    def collect_facts(self) -> dict[str, Any]:
        properties = [
            "ro.product.manufacturer",
            "ro.product.model",
            "ro.build.version.release",
            "ro.build.version.sdk",
            "ro.product.cpu.abi",
            "ro.build.version.security_patch",
            "ro.boot.verifiedbootstate",
            "ro.boot.flash.locked",
        ]
        facts: dict[str, Any] = {
            "serialHash": hashlib.sha256(self.config.device_serial.encode()).hexdigest()
        }
        for name in properties:
            facts[name] = self._shell(f"getprop {shlex.quote(name)}", timeout=20).stdout.strip()
        facts["pageSize"] = self._shell("getconf PAGESIZE", timeout=20, check=False).stdout.strip()
        facts["meminfo"] = self._shell("cat /proc/meminfo | head -5", timeout=20).stdout.strip().splitlines()
        facts["dataFilesystem"] = self._shell("df -h /data | tail -1", timeout=20).stdout.strip()
        facts["battery"] = self._shell("dumpsys battery | head -25", timeout=20).stdout.strip().splitlines()
        return facts

    def reboot(self, timeout_seconds: float) -> None:
        self._adb("reboot", timeout=20)
        self.runner.run(["adb", "-s", self.config.device_serial, "wait-for-device"], timeout=timeout_seconds)
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            state = self.runner.run(
                ["adb", "-s", self.config.device_serial, "get-state"],
                timeout=10,
                check=False,
            )
            if state.returncode == 0 and state.stdout.strip() == "device":
                return
            time.sleep(2)
        raise TimeoutError("device did not return after reboot")

    def logcat(self) -> str:
        return self._adb("logcat", "-d", "-v", "threadtime", timeout=60, check=False).stdout


class ControllerCli:
    def __init__(self, config: HilConfig, runner: CommandRunner):
        self.config = config
        self.runner = runner

    def _run(self, *args: str, timeout: float = 120, check: bool = True) -> subprocess.CompletedProcess[str]:
        if not self.config.controller_path.is_file():
            raise SetupBlocked(f"controller executable not found: {self.config.controller_path}")
        if not self.config.controller_config.is_file():
            raise SetupBlocked(f"controller config not found: {self.config.controller_config}")
        return self.runner.run(
            [str(self.config.controller_path), "--config", str(self.config.controller_config), *args],
            timeout=timeout,
            check=check,
        )

    @staticmethod
    def _json(result: subprocess.CompletedProcess[str]) -> Any:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"controller did not return JSON: {result.stdout[-1000:]}") from exc

    def _json_command(self, *args: str, timeout: float = 120) -> Any:
        return self._json(self._run(*args, timeout=timeout))

    def status(self) -> dict[str, Any]:
        value = self._json_command("status", timeout=30)
        if not isinstance(value, dict):
            raise RuntimeError("status response is not an object")
        return value

    def profiles(self) -> list[dict[str, Any]]:
        value = self._json_command("profiles", timeout=30)
        if not isinstance(value, list):
            raise RuntimeError("profiles response is not an array")
        return value

    def images(self) -> list[dict[str, Any]]:
        value = self._json_command("images", timeout=30)
        if not isinstance(value, list):
            raise RuntimeError("images response is not an array")
        return value

    def vms(self) -> list[dict[str, Any]]:
        value = self._json_command("vms", timeout=30)
        if not isinstance(value, list):
            raise RuntimeError("vms response is not an array")
        return value

    def _wait(self, operation: Any, timeout_seconds: float) -> dict[str, Any]:
        if not isinstance(operation, dict) or not isinstance(operation.get("id"), str):
            raise RuntimeError(f"operation response has no id: {operation!r}")
        value = self._json_command(
            "wait",
            operation["id"],
            "--timeout",
            str(timeout_seconds),
            timeout=timeout_seconds + 30,
        )
        if not isinstance(value, dict):
            raise RuntimeError("wait response is not an object")
        if value.get("state") != "SUCCEEDED":
            raise AssertionError(
                f"operation {operation['id']} ended in {value.get('state')}: {value.get('errorCode')}"
            )
        return value

    def apply_vm(self, vm_id: str, request: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as handle:
            json.dump(request, handle)
            temp = Path(handle.name)
        try:
            operation = self._json_command("apply-vm", vm_id, str(temp), timeout=30)
            return self._wait(operation, timeout_seconds)
        finally:
            temp.unlink(missing_ok=True)

    def import_image(self, request_path: Path, timeout_seconds: float) -> dict[str, Any]:
        operation = self._json_command("import-image", str(request_path), timeout=30)
        return self._wait(operation, timeout_seconds)

    def guest_ssh(self, target: str, command: str, timeout_seconds: float) -> None:
        known_hosts = self.config.root / ".local/hil-known-hosts"
        argv = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=15",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            f"UserKnownHostsFile={known_hosts}",
            target,
            command,
        ]
        self.runner.run(argv, timeout=timeout_seconds)

    def recovery_ssh(self, vm_id: str, user: str, command: str, timeout_seconds: float) -> None:
        known_hosts = self.config.root / ".local/hil-known-hosts"
        proxy = shlex.join(
            [
                str(self.config.controller_path),
                "--config",
                str(self.config.controller_config),
                "proxy-ssh",
                vm_id,
            ]
        )
        argv = [
            "ssh",
            "-o",
            f"ProxyCommand={proxy}",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=15",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            f"UserKnownHostsFile={known_hosts}",
            f"{user}@{vm_id}-recovery",
            command,
        ]
        self.runner.run(argv, timeout=timeout_seconds)


class HeadscaleLab:
    def __init__(self, config: HilConfig, runner: CommandRunner):
        self.config = config
        self.runner = runner

    @staticmethod
    def _contains_name(value: Any, expected: str) -> bool:
        if isinstance(value, dict):
            return any(HeadscaleLab._contains_name(item, expected) for item in value.values())
        if isinstance(value, list):
            return any(HeadscaleLab._contains_name(item, expected) for item in value)
        return isinstance(value, str) and expected.casefold() in value.casefold()

    def nodes(self) -> Any:
        result = self.runner.run(self.config.headscale_nodes_command, timeout=30)
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return result.stdout

    def wait_for_node(self, name: str, timeout_seconds: float) -> dict[str, Any] | str:
        deadline = time.monotonic() + timeout_seconds
        last: Any = None
        while time.monotonic() < deadline:
            last = self.nodes()
            if self._contains_name(last, name):
                return last
            time.sleep(2)
        raise TimeoutError(
            f"Headscale node did not appear within {timeout_seconds}s: {name}; last={last!r}"
        )
