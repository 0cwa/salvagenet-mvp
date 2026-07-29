package org.nodehost.qemu

import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class QemuProfileResolverTest {
    private val resolver = QemuProfileResolver()

    @Test
    fun rejectsRuntimeBelowProfileMinimumBeforeResolvingEffects() {
        val profile = QemuTestFixtures.ubuntuProfile()
        val runtime = QemuTestFixtures.runtime(profile, memoryMiB = 512)
        assertThrows(IllegalArgumentException::class.java) {
            resolver.resolve(profile, runtime, QemuTestFixtures.allocation("abcdefghijklmnop"))
        }
    }

    @Test
    fun noCloudRequiresConstrainedBootstrapToken() {
        val profile = QemuTestFixtures.ubuntuProfile()
        assertThrows(IllegalArgumentException::class.java) {
            resolver.resolve(profile, QemuTestFixtures.runtime(profile), QemuTestFixtures.allocation())
        }
        assertThrows(IllegalArgumentException::class.java) {
            QemuTestFixtures.allocation("../../escape-token")
        }
    }

    @Test
    fun allMutableAndArtifactPathsAreInstanceScoped() {
        val profile = QemuTestFixtures.alpineProfile()
        val launch = resolver.resolve(profile, QemuTestFixtures.runtime(profile), QemuTestFixtures.allocation()).resolved
        val paths = listOfNotNull(
            launch.kernelPath, launch.initramfsPath, launch.systemDiskPath, launch.dataDiskPath,
            launch.qmpSocketPath, launch.serialSocketPath, launch.consoleSocketPath,
            launch.controlSocketPath, launch.hostSocketPath,
        )
        assertTrue(paths.all { it.path.startsWith("/files/vms/default/") })
    }
}
