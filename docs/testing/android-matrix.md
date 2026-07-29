# Android test matrix

## Minimum overnight matrix

| Class | Required evidence |
|---|---|
| Primary ARM64 phone | Full APK-native QEMU + host/guest mesh end-to-end |
| Android emulator/API 36 | Activity/service/import/database tests with fake QEMU and mesh |
| 16 KiB-capable or configured device | Native ELF alignment/install/start validation |

## Broader qualification after MVP

- Android 8/9 legacy floor;
- Android 10/11 executable/foreground changes;
- Android 12/13 phantom-process and notification behavior;
- Android 14/15/16 foreground-service and page-size behavior;
- Pixel/AOSP, Samsung, Xiaomi/Redmi, OnePlus/Motorola;
- low-memory device and sustained plugged-in thermal test.

## Collected facts

`tests/device/collect-device-facts.sh` records API level, ABI, memory, storage, page size, battery, thermal service availability, package state, and ADB authorization. It writes to ignored `.local/device-facts/`.
