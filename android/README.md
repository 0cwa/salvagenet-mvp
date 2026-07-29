# Android workspace

`android/podroid/` is intentionally absent from the scaffold. Import and wire it with:

```sh
make import-podroid
make wire-podroid
```

Sibling modules remain under `android/modules/` and are included into the imported Gradle settings by `android/workspace.settings.gradle.kts`.
