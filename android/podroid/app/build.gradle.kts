/*
 * Podroid — Rootless Podman for Android
 *
 * A headless AArch64 QEMU micro-VM running Alpine Linux with Podman,
 * accessed via built-in serial terminal.
 */
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.ksp)
    alias(libs.plugins.hilt.android)
}

val podroidQemuVersion = providers.gradleProperty("podroidQemuVersion").get()
val podroidRuntimeLock = rootProject.file("../upstream/podroid-runtime.lock")
val podroidRuntimePreparer = rootProject.file("prepare-runtime.py")
val podroidRuntimeOutput = layout.buildDirectory.dir("generated/podroidRuntime")
val podroidRuntimeApk = layout.buildDirectory.file("outputs/apk/debug/app-debug.apk")
val nodeHostProfilePackager = rootProject.file("../../tools/profiles/package-assets.py")

android {
    namespace = "com.excp.podroid"
    compileSdk {
        version = release(36) {
            minorApiLevel = 1
        }
    }

    defaultConfig {
        applicationId = "com.excp.podroid"
        minSdk = 26
        targetSdk = 36
        versionCode = 30
        versionName = "1.2.6"
        buildConfigField("String", "QEMU_VERSION", "\"$podroidQemuVersion\"")

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        // Only build for arm64-v8a — we target AArch64 Android devices exclusively
        ndk {
            abiFilters += "arm64-v8a"
        }
    }

    signingConfigs {
        create("release") {
            val storePath = (project.findProperty("PODROID_RELEASE_STORE_FILE") as? String)
            if (storePath != null && file(storePath).exists()) {
                storeFile     = file(storePath)
                storePassword = project.findProperty("PODROID_RELEASE_STORE_PASSWORD") as? String
                keyAlias      = project.findProperty("PODROID_RELEASE_KEY_ALIAS")      as? String
                keyPassword   = project.findProperty("PODROID_RELEASE_KEY_PASSWORD")   as? String
            }
        }
    }

    buildTypes {
        debug {
            isDebuggable = true
            isJniDebuggable = true
            applicationIdSuffix = ".debug"
            versionNameSuffix = "-debug"
        }
        release {
            signingConfig = signingConfigs.getByName("release")
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    // Suppress Kotlin future-compat warning about annotation targets (KT-73255)
    // and silence hiltViewModel deprecation until Hilt updates its own docs.
    tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
        compilerOptions {
            freeCompilerArgs.addAll(
                "-Xannotation-default-target=param-property",
                "-nowarn"
            )
        }
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    sourceSets.getByName("main") {
        // Static paths plus the explicit preBuild dependency avoid AGP's ambiguous Provider source semantics.
        jniLibs.directories.add(podroidRuntimeOutput.get().dir("jniLibs").asFile.absolutePath)
        assets.directories.add(podroidRuntimeOutput.get().dir("assets").asFile.absolutePath)
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
        // QEMU is an ELF executable packaged as libqemu-system-aarch64.so.
        // It must be extracted to disk so ProcessBuilder can execute it.
        jniLibs {
            useLegacyPackaging = true
        }
    }
}

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

dependencies {
    // NODEHOST-COMPOSITION-HOOK
    implementation(project(":node-shell"))
    // Core
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)

    // Lifecycle & ViewModel
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.lifecycle.runtime.compose)

    // Compose BOM — pins all Compose library versions
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.material3.windowsizeclass)
    implementation(libs.androidx.compose.material.icons.extended)

    // Navigation
    implementation(libs.androidx.navigation.compose)

    // Hilt
    implementation(libs.hilt.android)
    ksp(libs.hilt.compiler)
    implementation(libs.hilt.navigation.compose)

    // Coroutines
    implementation(libs.kotlinx.coroutines.android)

    // DataStore (app settings)
    implementation(libs.androidx.datastore.preferences)

    // Vendored Termux terminal emulator & view (MatanZ/termux-app:sixel4 — Sixel + iTerm2 image support)
    implementation(project(":terminal-emulator"))
    implementation(project(":terminal-view"))

    // HiddenApiBypass — exempts our process from Android 14+ reflection filtering
    // so we can call the @SystemApi VirtualMachineManager constructors via
    // reflection on devices where the dev-grant path holds (Pixel 8+ etc.).
    implementation("org.lsposed.hiddenapibypass:hiddenapibypass:6.1")

    // Testing
    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    debugImplementation(libs.androidx.compose.ui.tooling)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
}
