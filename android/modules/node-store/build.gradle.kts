plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.ksp)
}

android {
    namespace = "org.nodehost.store"
    compileSdk = providers.gradleProperty("nodehost.compileSdk").orNull?.toInt() ?: 36
    defaultConfig { minSdk = providers.gradleProperty("nodehost.minSdk").orNull?.toInt() ?: 26 }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    testOptions { unitTests.isIncludeAndroidResources = true }
}

ksp {
    arg("room.schemaLocation", file("schemas").absolutePath)
}

dependencies {
    implementation(project(":node-model"))
    implementation(project(":node-core"))
    val roomVersion = providers.gradleProperty("nodehost.roomVersion").get()
    implementation("androidx.room:room-runtime:$roomVersion")
    implementation("androidx.room:room-ktx:$roomVersion")
    ksp("androidx.room:room-compiler:$roomVersion")
    testImplementation(libs.junit)
}
