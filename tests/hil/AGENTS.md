# Hardware-in-the-loop test instructions

- Use only the Android serial configured in `.local/hil.json`; never select the first device returned by `adb devices`.
- Scenario code depends on the small ports in `ports.py`. Put ADB, Headscale, controller, SSH, and subprocess details in adapters.
- Reuse the real Host API, `phonectl-mvp`, Headscale lab, QMP-backed runtime observations, and ordinary SSH. Do not add test-owned product state.
- Do not add a debug APK endpoint when the same observation is available through the Host API, ADB, existing diagnostics, Headscale, or SSH.
- Fake, emulator, host-QEMU, and physical-device results are distinct. Only a physical HIL run may close a physical acceptance gate.
- A physical pass records the source commit, APK SHA-256, hashed device serial, device facts, commands, assertions, and bounded redacted output.
- Exit 77 means a verified device/setup prerequisite is unavailable. It is not a substitute for attempting `hil-doctor`.
- Never print or persist live enrollment keys, Headscale API keys, controller capabilities, private keys, or guest secrets.
- Keep this runner standard-library-only until a repeated requirement proves a dependency necessary.
- USB/AOA networking remains out of scope until all base MVP gates pass.
