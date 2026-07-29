plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "org.nodehost.shell"
    compileSdk = providers.gradleProperty("nodehost.compileSdk").orNull?.toInt() ?: 36
    defaultConfig { minSdk = providers.gradleProperty("nodehost.minSdk").orNull?.toInt() ?: 26 }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    testOptions { unitTests.isIncludeAndroidResources = true }
    buildFeatures { buildConfig = true }
}

dependencies {
    implementation(project(":node-model"))
    implementation(project(":node-core"))
    implementation(project(":node-store"))
    implementation(project(":runtime-qemu"))
    implementation(project(":mesh-tailscale"))
    implementation(project(":control-api"))
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.kotlinx.coroutines.android)
    val roomVersion = providers.gradleProperty("nodehost.roomVersion").get()
    implementation("androidx.room:room-runtime:$roomVersion")
    testImplementation(project(":test-support"))
    testImplementation(libs.junit)
    testImplementation("androidx.test:core:1.6.1")
    testImplementation("org.robolectric:robolectric:4.16.1")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.9.0")
}
