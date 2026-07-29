package org.nodehost.qemu

class QemuCommandCompiler {
    fun compile(launch: ResolvedVmLaunch): QemuLaunchDescriptor {
        require(launch.instanceId.matches(Regex("[a-z0-9][a-z0-9-]{0,62}")))
        require(launch.memoryMiB in 256..16_384)
        require(launch.vcpus in 1..16)
        require(launch.recoverySshHostPort in 1024..65_535)
        require(launch.kernelArguments.none { '\n' in it || '\u0000' in it })

        val args = mutableListOf(
            "-M", "virt,gic-version=3",
            "-cpu", "max,pauth-impdef=on",
            "-accel", "tcg,thread=multi,tb-size=${if (launch.memoryMiB >= 2048) 512 else 256}",
            "-smp", launch.vcpus.toString(),
            "-m", launch.memoryMiB.toString(),
        )

        when (launch.bootMode) {
            QemuBootMode.DIRECT_KERNEL -> {
                args += listOf(
                    "-kernel", requireNotNull(launch.kernelPath),
                    "-initrd", requireNotNull(launch.initramfsPath),
                    "-append", launch.kernelArguments.joinToString(" "),
                )
            }
            QemuBootMode.UEFI -> {
                args += listOf(
                    "-drive",
                    "if=pflash,format=raw,readonly=on,file=${requireNotNull(launch.firmwareCodePath)}",
                    "-drive",
                    "if=pflash,format=raw,file=${requireNotNull(launch.firmwareVarsPath)}",
                )
            }
        }
        launch.metadataSeedUrl?.let { seedUrl ->
            require(seedUrl.startsWith("http://10.0.2.2:")) {
                "MVP NoCloud metadata must use the QEMU SLIRP host gateway"
            }
            args += listOf("-smbios", "type=1,serial=ds=nocloud-net;s=$seedUrl")
        }

        when (launch.diskLayout) {
            QemuDiskLayout.LEGACY_PODROID -> addLegacyPodroidDisks(args, launch)
            QemuDiskLayout.SYSTEM_THEN_DATA -> addGenericDisks(args, launch)
        }

        args += listOf(
            "-netdev",
            "user,id=net0,ipv6=off,hostfwd=tcp:127.0.0.1:${launch.recoverySshHostPort}-:22",
            "-device", "virtio-net-pci,netdev=net0,romfile=",
            "-serial", "unix:${launch.serialSocketPath},server,nowait",
            "-device", "virtio-serial-pci",
            "-chardev", "socket,id=term0,path=${launch.consoleSocketPath},server=on,wait=off",
            "-device", "virtconsole,chardev=term0,name=org.nodehost.console",
            "-display", "none",
            "-qmp", "unix:${launch.qmpSocketPath},server,nowait",
        )

        return QemuLaunchDescriptor(
            executable = launch.qemuExecutable,
            launcher = launch.launcherExecutable,
            workingDirectory = launch.workingDirectory,
            environment = mapOf(
                "LD_LIBRARY_PATH" to "${launch.nativeLibraryDir}:${launch.workingDirectory}",
            ),
            arguments = args,
        )
    }

    private fun addLegacyPodroidDisks(
        args: MutableList<String>,
        launch: ResolvedVmLaunch,
    ) {
        val statePath = requireNotNull(launch.dataDiskPath) {
            "legacy Podroid layout requires its writable ext4 state disk"
        }
        addDisk(
            args = args,
            id = "drive1",
            path = statePath,
            format = "raw",
            readOnly = false,
            ioThread = "iothread0",
            vcpus = launch.vcpus,
            discard = true,
        )
        addDisk(
            args = args,
            id = "drive2",
            path = launch.systemDiskPath,
            format = "raw", // SquashFS is exposed as a raw block device.
            readOnly = true,
            ioThread = "iothread1",
            vcpus = launch.vcpus,
            discard = false,
        )
    }

    private fun addGenericDisks(
        args: MutableList<String>,
        launch: ResolvedVmLaunch,
    ) {
        addDisk(
            args = args,
            id = "system",
            path = launch.systemDiskPath,
            format = launch.systemDiskFormat,
            readOnly = false,
            ioThread = "iothread0",
            vcpus = launch.vcpus,
            discard = true,
        )
        launch.dataDiskPath?.let { dataPath ->
            addDisk(
                args = args,
                id = "data",
                path = dataPath,
                format = "raw",
                readOnly = false,
                ioThread = "iothread1",
                vcpus = launch.vcpus,
                discard = true,
            )
        }
    }

    private fun addDisk(
        args: MutableList<String>,
        id: String,
        path: String,
        format: String,
        readOnly: Boolean,
        ioThread: String,
        vcpus: Int,
        discard: Boolean,
    ) {
        args += listOf("-object", "iothread,id=$ioThread")
        args += listOf(
            "-device",
            "virtio-blk-pci,drive=$id,num-queues=$vcpus,iothread=$ioThread",
        )
        val options = buildList {
            add("file=$path")
            add("if=none")
            add("id=$id")
            add("format=$format")
            if (readOnly) add("readonly=on")
            add("cache=writeback")
            add("aio=threads")
            if (discard) {
                add("discard=unmap")
                add("detect-zeroes=unmap")
            }
        }
        args += listOf("-drive", options.joinToString(","))
    }
}
