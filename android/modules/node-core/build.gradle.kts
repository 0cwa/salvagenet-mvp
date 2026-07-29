plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "org.nodehost.core"
    compileSdk = providers.gradleProperty("nodehost.compileSdk").orNull?.toInt() ?: 36
    defaultConfig { minSdk = providers.gradleProperty("nodehost.minSdk").orNull?.toInt() ?: 26 }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    testOptions { unitTests.isIncludeAndroidResources = true }
}

dependencies {
    implementation(libs.kotlinx.coroutines.android)
    implementation(project(":node-model"))
    testImplementation(libs.junit)
}
