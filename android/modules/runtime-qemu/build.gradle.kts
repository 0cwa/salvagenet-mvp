plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "org.nodehost.qemu"
    compileSdk = providers.gradleProperty("nodehost.compileSdk").orNull?.toInt() ?: 36
    defaultConfig { minSdk = providers.gradleProperty("nodehost.minSdk").orNull?.toInt() ?: 26 }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    testOptions { unitTests.isIncludeAndroidResources = true }
    sourceSets.getByName("test").resources.srcDir("../../../tests/qemu")
}

dependencies {
    implementation(libs.kotlinx.coroutines.android)
    implementation(project(":node-model"))
    implementation(project(":node-core"))
    testImplementation(libs.junit)
}
