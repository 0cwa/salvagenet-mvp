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
}

dependencies {
    implementation(project(":node-model"))
    implementation(project(":node-core"))
    implementation(project(":node-store"))
    implementation(project(":runtime-qemu"))
    implementation(project(":mesh-tailscale"))
    implementation(project(":control-api"))
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    testImplementation(libs.junit)
}
