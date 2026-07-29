# Android emulator laboratory instructions

- The emulator validates Activity/service/database/API behavior with fake QEMU
  and mesh adapters; it cannot qualify APK-native QEMU performance or VpnService
  behavior on real OEM hardware.
- Keep AVD files outside the repository and logs under ignored `.local/`.
- Do not add a system image download to the default scaffold validation path.
