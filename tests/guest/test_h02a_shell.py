#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "lab/qemu/scripts"


class H02AShellTests(unittest.TestCase):
    def setUp(self) -> None:
        local = ROOT / ".local"
        local.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=local, prefix="qemu-lab-shell-test-")
        self.state = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        self.environment = os.environ.copy()
        self.environment["NODEHOST_QEMU_LAB_DIR"] = str(self.state)
        self.environment["NODEHOST_QEMU_LAB_SSH_PORT"] = "2222"

    def run_script(self, name: str, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SCRIPTS / name), *arguments],
            cwd=ROOT,
            env=self.environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )

    def test_shell_entry_points_parse(self) -> None:
        for path in (
            SCRIPTS / "common.sh",
            SCRIPTS / "prepare.sh",
            SCRIPTS / "start.sh",
            SCRIPTS / "smoke.sh",
            SCRIPTS / "stop.sh",
            SCRIPTS / "e2e.sh",
            ROOT / "tools/profiles/pin-ubuntu-image.sh",
        ):
            subprocess.run(["bash", "-n", str(path)], check=True)

    def test_start_refuses_unrelated_live_pid(self) -> None:
        for name in (
            "preflight.json",
            "qemu-command.json",
            "system.qcow2",
            "data.raw",
            "seed.img",
            "AAVMF_CODE.fd",
            "AAVMF_VARS.fd",
        ):
            (self.state / name).touch()
        (self.state / "qemu.pid").write_text(f"{os.getpid()}\n", encoding="utf-8")
        result = self.run_script("start.sh")
        self.assertEqual(2, result.returncode, result.stderr)
        self.assertIn("process identity differs", result.stderr)
        os.kill(os.getpid(), 0)

    def test_stop_refuses_unrelated_live_pid(self) -> None:
        (self.state / "qemu.pid").write_text(f"{os.getpid()}\n", encoding="utf-8")
        result = self.run_script("stop.sh")
        self.assertEqual(2, result.returncode, result.stderr)
        self.assertIn("process identity differs", result.stderr)
        os.kill(os.getpid(), 0)

    def test_orchestration_has_three_stages_and_no_insecure_host_key_bypass(self) -> None:
        e2e = (SCRIPTS / "e2e.sh").read_text(encoding="utf-8")
        smoke = (SCRIPTS / "smoke.sh").read_text(encoding="utf-8")
        stop = (SCRIPTS / "stop.sh").read_text(encoding="utf-8")
        common = (SCRIPTS / "common.sh").read_text(encoding="utf-8")
        self.assertIn('"$(dirname "$0")/smoke.sh" initial', e2e)
        self.assertIn('"$(dirname "$0")/smoke.sh" guest-reboot', e2e)
        self.assertIn('"$(dirname "$0")/smoke.sh" qemu-restart', e2e)
        self.assertIn("passwordOnlyClientRejected", smoke)
        self.assertIn("keyboardInteractiveOnlyClientRejected", smoke)
        self.assertIn("qualificationSudoNoninteractive", smoke)
        self.assertIn("sudo -n true", smoke)
        self.assertIn("sudo -n systemctl reboot", e2e)
        self.assertIn("sudo -n systemctl poweroff", e2e)
        self.assertIn("sudo -n systemctl poweroff", stop)
        self.assertNotIn("'sudo systemctl", smoke + e2e + stop)
        self.assertIn("StrictHostKeyChecking=accept-new", common)
        self.assertNotIn("StrictHostKeyChecking=no", common + smoke + e2e)
        self.assertIn("readonly ssh_wait_seconds=900", common)
        self.assertIn("readonly cloud_init_wait_seconds=1800", common)
        self.assertIn('wait_for_ssh "$ssh_wait_seconds"', smoke)
        self.assertIn('wait_for_ssh "$ssh_wait_seconds"', e2e)
        self.assertIn('ssh_nodeadmin "$cloud_init_wait_seconds" \'cloud-init status --wait --long\'', smoke)
        self.assertLess(smoke.index("cloud-init status --wait --long"), smoke.index("sudo -n true"))
        self.assertNotIn("sudo -n cloud-init status", smoke)
        self.assertNotIn("wait_for_ssh 360", smoke + e2e)
        self.assertFalse((SCRIPTS / "report.py").exists())


if __name__ == "__main__":
    unittest.main()
