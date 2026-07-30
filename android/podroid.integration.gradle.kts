/*
 * SalvageNet-owned composition and packaging for the vendored Podroid app.
 *
 * Keep this file outside android/podroid so upstream refreshes have one narrow,
 * reviewable hook instead of a growing set of edits inside the subtree.
 */

val podroidRuntimeLock = rootProject.file("../upstream/podroid-runtime.lock")
val podroidRuntimePreparer = rootProject.file("../../tools/vendor/prepare-podroid-runtime.py")
val podroidRuntimeOutput = layout.buildDirectory.dir("generated/podroidRuntime")
val podroidRuntimeApk = layout.buildDirectory.file("outputs/apk/debug/app-debug.apk")
val nodeHostProfilePackager = rootProject.file("../../tools/profiles/package-assets.py")

extensions.configure<com.android.build.api.dsl.ApplicationExtension> {
    sourceSets.getByName("main") {
        // Static paths plus the explicit preBuild dependency avoid AGP's ambiguous Provider source semantics.
        jniLibs.directories.add(podroidRuntimeOutput.get().dir("jniLibs").asFile.absolutePath)
        assets.directories.add(podroidRuntimeOutput.get().dir("assets").asFile.absolutePath)
    }
}

dependencies.add("implementation", project(":node-shell"))

val preparePodroidRuntime by tasks.registering(Exec::class) {
    group = "build setup"
    description = "Obtains and verifies the pinned Podroid runtime before Android packaging."
    inputs.files(podroidRuntimeLock, podroidRuntimePreparer)
    inputs.dir(file("src/main/assets/qemu"))
    outputs.dir(podroidRuntimeOutput)
    commandLine(
        "python3",
        podroidRuntimePreparer.absolutePath,
        "--prepare",
        "--output-dir",
        podroidRuntimeOutput.get().asFile.absolutePath,
    )
    if (gradle.startParameter.isOffline) {
        args("--offline")
    }
}

tasks.named("preBuild") {
    dependsOn(preparePodroidRuntime)
}

// The sibling adapter exposes a generated file-backed AAR; resolve it only after its producer completes.
tasks.matching { it.name == "desugarDebugFileDependencies" || it.name == "checkDebugDuplicateClasses" }
    .configureEach {
        dependsOn(":mesh-tailscale:buildLibtailscale")
    }

val verifyNodeHostProfilePackaging by tasks.registering(Exec::class) {
    group = "verification"
    description = "Fails unless the debug APK contains the exact canonical profile and guest-init assets."
    dependsOn("packageDebug", ":node-shell:prepareNodeHostProfileAssets")
    inputs.files(nodeHostProfilePackager, podroidRuntimeApk)
    inputs.dir(rootProject.file("../../profiles"))
    commandLine(
        "python3",
        nodeHostProfilePackager.absolutePath,
        "--verify-apk",
        podroidRuntimeApk.get().asFile.absolutePath,
    )
}

val verifyPodroidPackaging by tasks.registering(Exec::class) {
    group = "verification"
    description = "Fails unless the debug APK contains the complete pinned ARM64 Podroid runtime."
    dependsOn("packageDebug", verifyNodeHostProfilePackaging)
    inputs.files(podroidRuntimeLock, podroidRuntimePreparer, podroidRuntimeApk)
    commandLine(
        "python3",
        podroidRuntimePreparer.absolutePath,
        "--verify-apk",
        podroidRuntimeApk.get().asFile.absolutePath,
    )
}

tasks.matching { it.name == "assembleDebug" }.configureEach {
    finalizedBy(verifyPodroidPackaging)
}

// The repository CI invokes :app:lintDebug, so missing runtime/profile payloads fail that existing gate too.
tasks.matching { it.name == "lintDebug" }.configureEach {
    dependsOn(verifyPodroidPackaging)
}
