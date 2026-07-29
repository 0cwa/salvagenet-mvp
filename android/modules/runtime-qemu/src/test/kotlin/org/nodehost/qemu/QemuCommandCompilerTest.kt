package org.nodehost.qemu

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class QemuCommandCompilerTest {
    private val resolver = QemuProfileResolver()
    private val compiler = QemuCommandCompiler()

    @Test
    fun alpineOutputMatchesPodroidDerivedGoldenArgvExactly() {
        val profile = QemuTestFixtures.alpineProfile()
        val actual = compiler.compile(resolver.resolve(profile, QemuTestFixtures.runtime(profile, memoryMiB = 512), QemuTestFixtures.allocation()).resolved)
            .argv().map { it.replace("/native", "\${NATIVE_LIB}").replace("/files", "\${FILES}").replace("10.0.2.2", "\${ANDROID_IP}") }
        assertEquals(golden("podroid-baseline.argv"), actual)
    }

    @Test
    fun alpineProfilePreservesPodroidLaunchKnowledgeAndScopesEveryPath() {
        val profile = QemuTestFixtures.alpineProfile()
        val launch = resolver.resolve(profile, QemuTestFixtures.runtime(profile), QemuTestFixtures.allocation()).resolved
        val result = compiler.compile(launch)
        val joined = result.argv().joinToString("\n")

        assertEquals("/native/libpodroid-launcher.so", result.argv().first())
        assertEquals("/native:/files/vms/default", result.environment.getValue("LD_LIBRARY_PATH"))
        assertTrue(joined.contains("virt,gic-version=3"))
        assertTrue(joined.contains("max,sve=off,pauth-impdef=on"))
        assertTrue(joined.contains("file=/files/vms/default/storage.img,if=none,id=drive1"))
        assertTrue(joined.contains("file=/files/vms/default/artifacts/alpine-rootfs.squashfs,if=none,id=drive2"))
        assertTrue(joined.contains("hostfwd=tcp:127.0.0.1:19922-:22"))
        assertTrue(result.sockets.all { it.path.startsWith("/files/vms/default/") })
        assertFalse(result.arguments.any { it.contains("hostfwd=tcp::") })
    }

    @Test
    fun ubuntuUefiHasNoAlpineFilenameAndUsesNoCloudAndWritableSystemFirst() {
        val profile = QemuTestFixtures.ubuntuProfile()
        val allocation = QemuTestFixtures.allocation("abcdefghijklmnop")
        val result = compiler.compile(resolver.resolve(profile, QemuTestFixtures.runtime(profile), allocation).resolved)
        val joined = result.arguments.joinToString("\n")

        assertTrue(joined.contains("if=pflash,format=raw,readonly=on,file=/files/vms/default/artifacts/AAVMF_CODE.fd"))
        assertTrue(joined.contains("file=/files/vms/default/system.qcow2,if=none,id=system,format=qcow2"))
        assertTrue(joined.contains("ds=nocloud-net;s=http://10.0.2.2:8080/v1/bootstrap/abcdefghijklmnop/"))
        assertFalse(joined.contains("alpine", ignoreCase = true))
        assertFalse(joined.contains("vmlinuz", ignoreCase = true))
        val normalized = result.argv().map {
            it.replace("/native", "\${NATIVE_LIB}")
                .replace("/files", "\${FILES}")
                .replace("abcdefghijklmnop", "\${TOKEN}")
        }
        assertEquals(golden("ubuntu-uefi.argv"), normalized)
    }

    @Test
    fun argvElementsPreserveSpacesWithoutStringSplitting() {
        val profile = QemuTestFixtures.alpineProfile()
        val result = compiler.compile(resolver.resolve(profile, QemuTestFixtures.runtime(profile), QemuTestFixtures.allocation()).resolved)
        val appendIndex = result.arguments.indexOf("-append")

        assertEquals("console=ttyAMA0 mitigations=off loglevel=1 quiet mitigations=off androidip=10.0.2.2 ssh=1 podroid.x11.dpi=96", result.arguments[appendIndex + 1])
    }

    private fun golden(name: String): List<String> =
        requireNotNull(javaClass.classLoader!!.getResourceAsStream(name)).bufferedReader()
            .readLines().filter { it.isNotBlank() && !it.startsWith('#') }
}
