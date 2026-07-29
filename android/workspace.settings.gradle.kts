// Applied from android/podroid/settings.gradle.kts by tools/bootstrap/wire-podroid.py.
val nodeHostModules = mapOf(
    "node-model" to "../modules/node-model",
    "node-core" to "../modules/node-core",
    "node-store" to "../modules/node-store",
    "runtime-qemu" to "../modules/runtime-qemu",
    "mesh-tailscale" to "../modules/mesh-tailscale",
    "control-api" to "../modules/control-api",
    "node-shell" to "../modules/node-shell",
    "test-support" to "../modules/test-support",
)
nodeHostModules.forEach { (name, relativePath) ->
    val projectPath = ":$name"
    if (findProject(projectPath) == null) include(projectPath)
    project(projectPath).projectDir = file(relativePath)
}
