from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    pass


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{field} must be a non-empty string")
    return value


def _string_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ConfigError(f"{field} must be a list of non-empty strings")
    return list(value)


@dataclass(frozen=True)
class HilConfig:
    root: Path
    source: Path
    raw: dict[str, Any]

    @classmethod
    def load(cls, root: Path, path: str | None = None) -> "HilConfig":
        selected = Path(path or os.environ.get("SALVAGENET_HIL_CONFIG", ".local/hil.json"))
        if not selected.is_absolute():
            selected = root / selected
        if not selected.is_file():
            raise ConfigError(
                f"HIL config not found: {selected}. Copy tests/hil/config.example.json to .local/hil.json."
            )
        try:
            value = json.loads(selected.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(f"cannot read HIL config {selected}: {exc}") from exc
        if not isinstance(value, dict):
            raise ConfigError("HIL config must contain a JSON object")
        return cls(root=root, source=selected, raw=value)

    def path(self, dotted: str, *, required: bool = True) -> Path | None:
        value = self.value(dotted, required=required)
        if value is None:
            return None
        text = _require_string(value, dotted)
        path = Path(text)
        return path if path.is_absolute() else self.root / path

    def value(self, dotted: str, *, required: bool = True, default: Any = None) -> Any:
        current: Any = self.raw
        for part in dotted.split("."):
            if not isinstance(current, dict) or part not in current:
                if required:
                    raise ConfigError(f"missing required config field: {dotted}")
                return default
            current = current[part]
        return current

    @property
    def device_serial(self) -> str:
        return _require_string(self.value("device.serial"), "device.serial")

    @property
    def package_name(self) -> str:
        return _require_string(self.value("device.packageName"), "device.packageName")

    @property
    def supervisor_component(self) -> str:
        return _require_string(self.value("device.supervisorComponent"), "device.supervisorComponent")

    @property
    def qemu_pattern(self) -> str:
        return _require_string(
            self.value("device.qemuProcessPattern", required=False, default="libqemu-system-aarch64.so"),
            "device.qemuProcessPattern",
        )

    @property
    def apk_path(self) -> Path:
        path = self.path("paths.apk")
        assert path is not None
        return path

    @property
    def controller_path(self) -> Path:
        path = self.path("paths.controller")
        assert path is not None
        return path

    @property
    def controller_config(self) -> Path:
        path = self.path("paths.controllerConfig")
        assert path is not None
        return path

    @property
    def evidence_directory(self) -> Path:
        path = self.path("paths.evidenceDirectory", required=False)
        return path or (self.root / ".local/hil-runs")

    @property
    def build_command(self) -> list[str]:
        return _string_list(
            self.value(
                "paths.buildCommand",
                required=False,
                default=["android/podroid/gradlew", "-p", "android/podroid", ":app:assembleDebug"],
            ),
            "paths.buildCommand",
        )

    @property
    def headscale_nodes_command(self) -> list[str]:
        return _string_list(
            self.value(
                "headscale.nodesCommand",
                required=False,
                default=[
                    "lab/headscale/scripts/container.sh",
                    "exec",
                    "headscale",
                    "nodes",
                    "list",
                    "--output",
                    "json",
                ],
            ),
            "headscale.nodesCommand",
        )

    def scenario(self, name: str) -> dict[str, Any]:
        value = self.value(name, required=False, default={})
        if not isinstance(value, dict):
            raise ConfigError(f"{name} must be an object")
        return value
