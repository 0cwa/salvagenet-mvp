package org.nodehost.qemu

internal class QemuCommandCompiler {
    fun compile(launch: ResolvedVmLaunch): QemuLaunchDescriptor {
        require(launch.memoryMiB in 256..16_384)
        require(launch.vcpus in 1..16)
        require(launch.recoverySshHostPort in 1024..65_535)
        require(launch.kernelArguments.none { '\n' in it || '\u0000' in it || it.isBlank() })

        val args = mutableListOf(
            "-M", "virt,gic-version=3",
            "-cpu", "max,pauth-impdef=on",
            "-accel", "tcg,thread=multi,tb-size=${if (launch.memoryMiB >= 2048) 512 else 256}",
            "-smp", launch.vcpus.toString(),
            "-m", launch.memoryMiB.toString(),
        )
        when (launch.bootMode) {
            QemuBootMode.DIRECT_KERNEL -> args += listOf(
                "-kernel", requireNotNull(launch.kernelPath).path,
                "-append", launch.kernelArguments.joinToString(" "),
                "-initrd", requireNotNull(launch.initramfsPath).path,
            )
            QemuBootMode.UEFI -> args += listOf(
                "-drive", "if=pflash,format=raw,readonly=on,file=${requireNotNull(launch.firmwareCodePath).path}",
                "-drive", "if=pflash,format=raw,file=${requireNotNull(launch.firmwareVarsPath).path}",
            )
        }
        launch.metadataSeedUrl?.let { args += listOf("-smbios", "type=1,serial=ds=nocloud-net;s=$it") }

        when (launch.diskLayout) {
            QemuDiskLayout.LEGACY_PODROID -> {
                addDisk(args, "drive1", requireNotNull(launch.dataDiskPath).path, "raw", false, "iothread0", launch.vcpus, true)
                addDisk(args, "drive2", launch.systemDiskPath.path, "raw", true, "iothread1", launch.vcpus, false)
            }
            QemuDiskLayout.SYSTEM_THEN_DATA -> {
                addDisk(args, "system", launch.systemDiskPath.path, launch.systemDiskFormat, false, "iothread0", launch.vcpus, true)
                launch.dataDiskPath?.let { addDisk(args, "data", it.path, "raw", false, "iothread1", launch.vcpus, true) }
            }
        }

        args += listOf(
            "-netdev", "user,id=net0,ipv6=off,hostfwd=tcp:127.0.0.1:${launch.recoverySshHostPort}-:22",
            "-device", "virtio-net-pci,netdev=net0,romfile=",
            "-serial", "unix:${launch.serialSocketPath.path},server,nowait",
            "-device", "virtio-serial-pci",
            "-chardev", "socket,id=term0,path=${launch.consoleSocketPath.path},server=on,wait=off",
            "-device", "virtconsole,chardev=term0,name=org.podroid.term",
            "-chardev", "socket,id=ctrl0,path=${launch.controlSocketPath.path},server=on,wait=off",
            "-device", "virtconsole,chardev=ctrl0,name=org.podroid.ctrl",
            "-chardev", "socket,id=host0,path=${launch.hostSocketPath.path},server=on,wait=off",
            "-device", "virtconsole,chardev=host0,name=org.podroid.host",
            "-display", "none",
            "-qmp", "unix:${launch.qmpSocketPath.path},server,nowait",
            "-cpu", "max,sve=off,pauth-impdef=on",
            "-accel", "tcg,thread=multi,tb-size=512",
            "-object", "rng-random,id=rng0,filename=/dev/urandom",
            "-device", "virtio-rng-pci,rng=rng0",
            "-overcommit", "mem-lock=off",
        )
        return QemuLaunchDescriptor(
            executable = launch.qemuExecutable,
            launcher = launch.launcherExecutable,
            workingDirectory = launch.workingDirectory,
            environment = mapOf("LD_LIBRARY_PATH" to "${launch.nativeLibraryDir.path}:${launch.workingDirectory.path}"),
            arguments = args,
            sockets = listOf(launch.serialSocketPath, launch.consoleSocketPath, launch.controlSocketPath, launch.hostSocketPath, launch.qmpSocketPath),
        )
    }

    private fun addDisk(args: MutableList<String>, id: String, path: String, format: String, readOnly: Boolean, ioThread: String, vcpus: Int, discard: Boolean) {
        require(format == "raw" || format == "qcow2")
        args += listOf("-object", "iothread,id=$ioThread")
        args += listOf("-device", "virtio-blk-pci,drive=$id,num-queues=$vcpus,iothread=$ioThread")
        val options = mutableListOf("file=$path", "if=none", "id=$id", "format=$format")
        if (readOnly) options += "readonly=on"
        options += listOf("cache=writeback", "aio=threads")
        if (discard) options += listOf("discard=unmap", "detect-zeroes=unmap")
        args += listOf("-drive", options.joinToString(","))
    }
}
