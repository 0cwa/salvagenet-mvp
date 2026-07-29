plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "org.nodehost.api"
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
    val ktorVersion = providers.gradleProperty("nodehost.ktorVersion").get()
    implementation("io.ktor:ktor-server-core:$ktorVersion")
    implementation("io.ktor:ktor-server-cio:$ktorVersion")
    implementation("io.ktor:ktor-server-content-negotiation:$ktorVersion")
    implementation("io.ktor:ktor-server-status-pages:$ktorVersion")
    implementation("com.google.code.gson:gson:2.11.0")
    testImplementation(libs.junit)
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.9.0")
}
