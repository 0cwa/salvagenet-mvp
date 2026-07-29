import java.util.zip.ZipFile
import org.gradle.api.DefaultTask
import org.gradle.api.file.DirectoryProperty
import org.gradle.api.file.RegularFileProperty
import org.gradle.api.tasks.InputFile
import org.gradle.api.tasks.OutputDirectory
import org.gradle.api.tasks.OutputFile
import org.gradle.api.tasks.TaskAction

plugins {
    alias(libs.plugins.android.library)
}

abstract class UnpackLibtailscale : DefaultTask() {
    @get:InputFile abstract val aarFile: RegularFileProperty
    @get:OutputFile abstract val classesJar: RegularFileProperty
    @get:OutputFile abstract val consumerRules: RegularFileProperty
    @get:OutputDirectory abstract val jniDirectory: DirectoryProperty

    @TaskAction
    fun unpack() {
        val classesOutput = classesJar.get().asFile
        val consumerRulesOutput = consumerRules.get().asFile
        val jniOutput = jniDirectory.get().asFile
        check(!classesOutput.exists() || classesOutput.delete()) {
            "Could not replace generated libtailscale JAR"
        }
        check(!consumerRulesOutput.exists() || consumerRulesOutput.delete()) {
            "Could not replace generated libtailscale consumer rules"
        }
        check(!jniOutput.exists() || jniOutput.deleteRecursively()) {
            "Could not replace generated libtailscale JNI directory"
        }
        classesOutput.parentFile.mkdirs()
        jniOutput.mkdirs()

        ZipFile(aarFile.get().asFile).use { archive ->
            val classesEntry = checkNotNull(archive.getEntry("classes.jar")) {
                "Generated libtailscale AAR has no classes.jar"
            }
            archive.getInputStream(classesEntry).use { input ->
                classesOutput.outputStream().use(input::copyTo)
            }
            val consumerRulesEntry = checkNotNull(archive.getEntry("proguard.txt")) {
                "Generated libtailscale AAR has no consumer rules"
            }
            archive.getInputStream(consumerRulesEntry).use { input ->
                consumerRulesOutput.outputStream().use(input::copyTo)
            }
            // Ktor's optional IDE-debug detector references desktop-only JMX
            // classes. They are absent on Android and are not used by NodeHost.
            consumerRulesOutput.appendText(
                "\n-dontwarn java.lang.management.ManagementFactory\n" +
                    "-dontwarn java.lang.management.RuntimeMXBean\n",
            )

            val nativeEntries = archive.entries().asSequence()
                .filter { !it.isDirectory && it.name.startsWith("jni/") }
                .toList()
            check(nativeEntries.isNotEmpty()) { "Generated libtailscale AAR has no JNI libraries" }
            check(nativeEntries.all { it.name.startsWith("jni/arm64-v8a/") }) {
                "Generated libtailscale AAR contains a non-arm64 ABI"
            }
            nativeEntries.forEach { entry ->
                val relativeName = entry.name.removePrefix("jni/arm64-v8a/")
                check(relativeName.isNotEmpty() && '/' !in relativeName) {
                    "Generated libtailscale AAR has an invalid JNI entry"
                }
                val output = jniOutput.resolve("arm64-v8a").resolve(relativeName)
                output.parentFile.mkdirs()
                archive.getInputStream(entry).use { input ->
                    output.outputStream().use(input::copyTo)
                }
            }
        }
    }
}

val vendorAar = rootProject.projectDir.parentFile.resolve("vendor/tailscale/build/libtailscale.aar")
val buildLibtailscale by tasks.registering(Exec::class) {
    inputs.file(rootProject.projectDir.parentFile.resolve("vendor/tailscale/tailscale.lock"))
    inputs.file(rootProject.projectDir.resolve("../../tools/vendor/build-libtailscale-android.sh"))
    outputs.file(vendorAar)
    commandLine(rootProject.projectDir.resolve("../../tools/vendor/build-libtailscale-android.sh"))
}

// Android libraries cannot safely bundle a direct local AAR dependency. Explode
// the generated gomobile AAR into dependency types AGP supports: an embedded
// local JAR plus generated JNI source inputs.
val unpackLibtailscale by tasks.registering(UnpackLibtailscale::class) {
    dependsOn(buildLibtailscale)
    aarFile.set(vendorAar)
    classesJar.set(layout.buildDirectory.file("generated/libtailscale/libtailscale.jar"))
    consumerRules.set(layout.buildDirectory.file("generated/libtailscale/consumer-rules.pro"))
    jniDirectory.set(layout.buildDirectory.dir("generated/libtailscale/jni"))
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

androidComponents {
    onVariants(selector().all()) { variant ->
        variant.sources.jniLibs?.addGeneratedSourceDirectory(
            unpackLibtailscale,
            UnpackLibtailscale::jniDirectory,
        )
        variant.consumerProguardFiles.add(unpackLibtailscale.flatMap { it.consumerRules })
    }
}

dependencies {
    implementation(project(":node-model"))
    implementation(project(":node-core"))
    implementation(libs.androidx.core.ktx)
    implementation(libs.kotlinx.coroutines.android)
    implementation(
        files(unpackLibtailscale.flatMap { it.classesJar }).builtBy(unpackLibtailscale),
    )
    testImplementation(libs.junit)
    testImplementation("org.json:json:20240303")
}
