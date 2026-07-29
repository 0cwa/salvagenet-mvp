plugins {
    alias(libs.plugins.android.library)
}

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
    testImplementation(libs.junit)
}
