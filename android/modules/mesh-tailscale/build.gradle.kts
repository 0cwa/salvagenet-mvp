plugins {
    alias(libs.plugins.android.library)
}

val vendorAar = rootProject.projectDir.parentFile.resolve("vendor/tailscale/build/libtailscale.aar")
val buildLibtailscale by tasks.registering(Exec::class) {
    inputs.file(rootProject.projectDir.parentFile.resolve("vendor/tailscale/tailscale.lock"))
    inputs.file(rootProject.projectDir.resolve("../../tools/vendor/build-libtailscale-android.sh"))
    outputs.file(vendorAar)
    commandLine(rootProject.projectDir.resolve("../../tools/vendor/build-libtailscale-android.sh"))
}

tasks.named("preBuild").configure { dependsOn(buildLibtailscale) }

android {
    namespace = "org.nodehost.mesh"
    compileSdk = providers.gradleProperty("nodehost.compileSdk").orNull?.toInt() ?: 36
    defaultConfig { minSdk = providers.gradleProperty("nodehost.minSdk").orNull?.toInt() ?: 26 }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    testOptions { unitTests.isIncludeAndroidResources = true }
}

dependencies {
    implementation(project(":node-model"))
    implementation(project(":node-core"))
    implementation(libs.androidx.core.ktx)
    implementation(libs.kotlinx.coroutines.android)
    implementation(files(vendorAar))
    testImplementation(libs.junit)
    testImplementation("org.json:json:20240303")
}
