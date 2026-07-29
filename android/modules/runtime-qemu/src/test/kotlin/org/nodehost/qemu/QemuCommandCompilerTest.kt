package org.nodehost.qemu

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class QemuCommandCompilerTest {
    @Test
    fun legacyProfilePreservesPodroidDiskOrderAndLoopbackRecovery() {
        val result = QemuCommandCompiler().compile(directLaunch())
        val drives = result.arguments.filter { it.startsWith("file=") }

        assertTrue(drives[0].contains("file=/files/vms/default/state.raw"))
        assertTrue(drives[0].contains("id=drive1"))
        assertTrue(drives[1].contains("file=/files/images/alpine.squashfs"))
        assertTrue(drives[1].contains("id=drive2"))
        assertTrue(drives[1].contains("readonly=on"))
        assertTrue(result.arguments.any { it.contains("hostfwd=tcp:127.0.0.1:19922-:22") })
        assertEquals("/native/liblauncher.so", result.argv().first())
    }

    @Test
    fun uefiProfileUsesGenericSystemFirstLayoutAndNoAlpinePath() {
        val result = QemuCommandCompiler().compile(uefiLaunch())
        val joined = result.arguments.joinToString("\n")

        assertTrue(joined.contains("if=pflash,format=raw,readonly=on,file=/firmware/AAVMF_CODE.fd"))
        assertTrue(joined.contains("file=/files/vms/default/system.qcow2,if=none,id=system,format=qcow2"))
        assertTrue(joined.contains("ds=nocloud-net;s=http://10.0.2.2:18080/bootstrap/nonce/"))
        assertFalse(joined.contains("alpine-rootfs"))
    }

    private fun directLaunch() = ResolvedVmLaunch(
        instanceId = "default",
        qemuExecutable = "/native/libqemu-system-aarch64.so",
        launcherExecutable = "/native/liblauncher.so",
        nativeLibraryDir = "/native",
        workingDirectory = "/files/vms/default",
        bootMode = QemuBootMode.DIRECT_KERNEL,
        diskLayout = QemuDiskLayout.LEGACY_PODROID,
        memoryMiB = 1024,
        vcpus = 2,
        kernelPath = "/files/kernel",
        initramfsPath = "/files/initrd",
        kernelArguments = listOf("console=ttyAMA0"),
        systemDiskPath = "/files/images/alpine.squashfs",
        systemDiskFormat = "raw",
        dataDiskPath = "/files/vms/default/state.raw",
        qmpSocketPath = "/files/vms/default/qmp.sock",
        serialSocketPath = "/files/vms/default/serial.sock",
        consoleSocketPath = "/files/vms/default/console.sock",
        recoverySshHostPort = 19922,
    )

    private fun uefiLaunch() = ResolvedVmLaunch(
        instanceId = "default",
        qemuExecutable = "/native/libqemu-system-aarch64.so",
        launcherExecutable = "/native/liblauncher.so",
        nativeLibraryDir = "/native",
        workingDirectory = "/files/vms/default",
        bootMode = QemuBootMode.UEFI,
        diskLayout = QemuDiskLayout.SYSTEM_THEN_DATA,
        memoryMiB = 1024,
        vcpus = 2,
        firmwareCodePath = "/firmware/AAVMF_CODE.fd",
        firmwareVarsPath = "/files/vms/default/AAVMF_VARS.fd",
        metadataSeedUrl = "http://10.0.2.2:18080/bootstrap/nonce/",
        systemDiskPath = "/files/vms/default/system.qcow2",
        systemDiskFormat = "qcow2",
        dataDiskPath = "/files/vms/default/data.raw",
        qmpSocketPath = "/files/vms/default/qmp.sock",
        serialSocketPath = "/files/vms/default/serial.sock",
        consoleSocketPath = "/files/vms/default/console.sock",
        recoverySshHostPort = 19922,
    )
}
