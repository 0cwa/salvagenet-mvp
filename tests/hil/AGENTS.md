# Hardware-in-the-loop test instructions

- Use only the Android serial configured in `.local/hil.json`; never select the first device returned by `adb devices`.
- Every scenario runs under the serial-specific `.local/hil-locks/` lease; do not bypass or create a second physical runner.
- `doctor` and `facts` are read-only. Mutating scenarios require non-expired local authorization for the scenario and each destructive adapter action.
- Diagnostic mode is the default and is permanently non-promotable. Candidate mode requires a clean source tree and exact APK digest.
- Scenario code depends on the small ports in `ports.py`. Put ADB, Headscale, controller, SSH, artifact upload, and subprocess details in adapters.
- Reuse the real Host API, `phonectl-mvp`, Headscale lab, QMP-backed runtime observations, and ordinary SSH. Do not add test-owned product state.
- Do not add a debug APK endpoint when the same observation is available through the Host API, ADB, existing diagnostics, Headscale, or SSH.
- Fake, emulator, host-QEMU, and physical-device results are distinct. Only a clean reviewed physical candidate run may close a physical acceptance gate.
- A physical pass records source mode/cleanliness, commit, APK SHA-256, hashed device serial, device facts, profiles, image digests, desired state, commands, assertions, and bounded redacted output.
- Exit 77 means a verified device/setup/authorization prerequisite is unavailable. It is not a substitute for attempting `hil-doctor`.
- Never print or persist live enrollment keys, Headscale API keys, controller capabilities, private keys, guest secrets, or raw device serials.
- Cleanup that restores guest mesh or controller reachability must run through `finally` and be recorded.
- Keep this runner standard-library-only until a repeated requirement proves a dependency necessary.
- USB/AOA networking remains out of scope until all base MVP gates pass.
