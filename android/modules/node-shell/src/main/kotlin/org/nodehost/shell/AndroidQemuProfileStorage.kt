package org.nodehost.shell

import android.content.Context
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.RandomAccessFile
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.security.MessageDigest
import org.json.JSONObject
import org.nodehost.model.ArtifactRef
import org.nodehost.model.BootSpec
import org.nodehost.model.DataDiskSpec
import org.nodehost.model.DiskFormat
import org.nodehost.model.HealthKind
import org.nodehost.model.HealthSpec
import org.nodehost.model.InitializationKind
import org.nodehost.model.InitializationSpec
import org.nodehost.model.MachineSpec
import org.nodehost.model.ProfileRequirements
import org.nodehost.model.RecoverySshSpec
import org.nodehost.model.RuntimeSpec
import org.nodehost.model.SystemDiskSpec
import org.nodehost.model.VmProfile
import org.nodehost.model.VmProfileId
import org.nodehost.model.WritableLayer

internal const val ALPINE_PROFILE_ID = "alpine-direct-qualification"
private const val UBUNTU_PROFILE_ID = "ubuntu-2404-arm64-uefi"
private const val K3S_PROFILE_ID = "k3s-worker-lab"

/** Owns profile resolution and offline disk/artifact effects; process lifecycle stays in AndroidQemuRuntimeBackend. */
internal class AndroidQemuProfileStorage(
    context: Context,
    private val atomicMove: (File, File) -> Unit = { source, target ->
        Files.move(source.toPath(), target.toPath(), StandardCopyOption.ATOMIC_MOVE)
    },
) {
    private val application = context.applicationContext
    private val artifactRoot = File(application.filesDir, "nodehost-artifacts")

    internal fun profile(id: VmProfileId, verifyArtifacts: Boolean): VmProfile = when (id.value) {
        ALPINE_PROFILE_ID -> VmProfile(
            id, 1, machine = MachineSpec(cpuModel = "max"),
            boot = BootSpec.DirectKernel(artifact("podroid-kernel", verifyArtifacts), artifact("podroid-initramfs", verifyArtifacts), "podroid-compatible-v1"),
            systemDisk = SystemDiskSpec(artifact("podroid-alpine-squashfs", verifyArtifacts), DiskFormat.SQUASHFS, WritableLayer.SEPARATE_EXT4_OVERLAY),
            dataDisk = DataDiskSpec(4, true),
            initialization = InitializationSpec(InitializationKind.LEGACY_PODROID, "guest-init/alpine-direct/vendor-data.yaml"),
            recoverySsh = RecoverySshSpec(), health = HealthSpec(HealthKind.CONSOLE_MARKER, "Ready!"),
            requirements = ProfileRequirements(512, 3, setOf("virtio-block", "virtio-net", "serial-console", "overlayfs")),
        )
        UBUNTU_PROFILE_ID, K3S_PROFILE_ID -> {
            val k3s = id.value == K3S_PROFILE_ID
            VmProfile(
                id, 1, extends = if (k3s) VmProfileId(UBUNTU_PROFILE_ID) else null,
                machine = MachineSpec(cpuModel = "max"),
                boot = BootSpec.Uefi(artifact("aavmf-code", verifyArtifacts), artifact("aavmf-vars", verifyArtifacts)),
                systemDisk = SystemDiskSpec(artifact("ubuntu-2404-arm64-cloud", verifyArtifacts), DiskFormat.QCOW2, WritableLayer.QCOW2_OVERLAY),
                dataDisk = DataDiskSpec(8, true),
                initialization = InitializationSpec(InitializationKind.NOCLOUD_NET, if (k3s) "guest-init/k3s-worker-lab/vendor-data.yaml" else "guest-init/ubuntu/vendor-data.yaml", "/v1/bootstrap/{token}/"),
                recoverySsh = RecoverySshSpec(), health = HealthSpec(HealthKind.METADATA_CALLBACK),
                requirements = if (k3s) ProfileRequirements(1024, 8, K3S_CHECKS) else ProfileRequirements(768, 5, setOf("uefi", "cloud-init", "openssh")),
            )
        }
        else -> error("unsupported profile: ${id.value}")
    }

    internal fun prepareDisks(runtime: RuntimeSpec) {
        val instance = instanceDirectory().apply { check(mkdirs() || isDirectory) }
        val artifacts = File(instance, "artifacts").apply { check(mkdirs() || isDirectory) }
        when (runtime.profileId.value) {
            ALPINE_PROFILE_ID -> {
                copyVerified("podroid-kernel", File(artifacts, "vmlinuz-virt"))
                copyVerified("podroid-initramfs", File(artifacts, "initrd.img"))
                copyVerified("podroid-alpine-squashfs", File(artifacts, "alpine-rootfs.squashfs"))
                val overlay = File(instance, "storage.img")
                if (!overlay.exists()) RandomAccessFile(overlay, "rw").use { it.setLength(runtime.dataDiskGiB * GIB) }
            }
            UBUNTU_PROFILE_ID, K3S_PROFILE_ID -> {
                copyVerified("aavmf-code", File(artifacts, "AAVMF_CODE.fd"))
                // These are mutable VM state. Verify the imported source, but create each target exactly once.
                copyVerifiedOnce("aavmf-vars", File(instance, "firmware-vars.fd"))
                copyVerifiedOnce("ubuntu-2404-arm64-cloud", File(instance, "system.qcow2"))
                val data = File(instance, "data.raw")
                val durable = durableDataFile()
                if (!data.exists() && durable.exists()) {
                    atomicMove(durable, data)
                    check(data.isFile && !durable.exists()) { "data disk restoration was not atomic" }
                }
                if (!data.exists()) RandomAccessFile(data, "rw").use { it.setLength(runtime.dataDiskGiB * GIB) }
            }
            else -> error("unsupported profile: ${runtime.profileId.value}")
        }
    }

    internal fun removeSystem(runtime: RuntimeSpec) {
        val instance = instanceDirectory()
        val data = File(instance, "data.raw")
        if (runtime.preserveDataOnDelete && data.exists()) {
            val durable = durableDataFile()
            check(durable.parentFile?.mkdirs() == true || durable.parentFile?.isDirectory == true) { "durable data directory unavailable" }
            check(!durable.exists()) { "durable data disk already exists" }
            atomicMove(data, durable)
            check(durable.isFile && !data.exists()) { "data disk preservation was not atomic" }
        }
        deleteBounded(instance, MAX_DELETE_ENTRIES)
    }

    internal fun instanceDirectory() = File(application.filesDir, "vms/default")

    private fun durableDataFile() = File(application.filesDir, "nodehost-durable/vms/default/data.raw")

    private fun artifact(id: String, verify: Boolean): ArtifactRef {
        val file = artifactFile(id)
        require(file.isFile && file.length() in 1..MAX_ARTIFACT_BYTES) { "trusted artifact is missing or out of bounds: $id" }
        val digest = sha256(file)
        if (verify) require(expectedDigest(id) == digest) { "artifact digest mismatch: $id" }
        return ArtifactRef(id, digest, file.length())
    }

    private fun artifactFile(id: String): File {
        val manifest = File(artifactRoot, "$id.manifest.json")
        if (!manifest.isFile) return File(artifactRoot, id)
        require(manifest.length() in 1..4096) { "artifact manifest is out of bounds: $id" }
        val relative = JSONObject(manifest.readText()).getString("relativePath")
        val resolved = File(artifactRoot, relative).canonicalFile
        require(resolved.path.startsWith(artifactRoot.canonicalPath + File.separator)) { "artifact manifest escaped its root" }
        return resolved
    }

    private fun expectedDigest(id: String): String {
        val manifest = File(artifactRoot, "$id.manifest.json")
        if (manifest.isFile) return JSONObject(manifest.readText()).getString("sha256")
        val expected = File(artifactRoot, "$id.sha256")
        require(expected.isFile && expected.length() <= 128) { "artifact digest metadata is missing: $id" }
        return expected.readText().trim()
    }

    private fun copyVerifiedOnce(id: String, target: File) {
        artifact(id, true)
        if (target.exists()) {
            require(target.isFile && target.length() in 1..MAX_ARTIFACT_BYTES) { "mutable system state is invalid: ${target.name}" }
            return
        }
        copyVerified(id, target)
    }

    private fun copyVerified(id: String, target: File) {
        val source = artifactFile(id)
        artifact(id, true)
        if (target.isFile && target.length() == source.length() && sha256(target) == sha256(source)) return
        val temporary = File(target.parentFile, target.name + ".tmp")
        FileInputStream(source).use { input ->
            FileOutputStream(temporary).use { output ->
                input.copyTo(output, COPY_BUFFER_BYTES)
                output.fd.sync()
            }
        }
        check(temporary.renameTo(target)) { "atomic artifact publication failed: $id" }
    }

    private fun sha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        FileInputStream(file).use { input ->
            val buffer = ByteArray(COPY_BUFFER_BYTES)
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                digest.update(buffer, 0, count)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }

    private fun deleteBounded(root: File, remaining: Int): Int {
        if (!root.exists()) return remaining
        require(remaining > 0) { "runtime deletion exceeded entry bound" }
        var budget = remaining - 1
        root.listFiles()?.forEach { budget = deleteBounded(it, budget) }
        check(root.delete()) { "failed to delete runtime path" }
        return budget
    }

    private companion object {
        val K3S_CHECKS = setOf("cgroup-v2", "namespaces", "overlayfs", "br-netfilter", "vxlan", "tun", "iptables-or-nft", "ip-forwarding", "swap-policy", "minimum-memory", "minimum-storage", "tailscale-reachability")
        const val COPY_BUFFER_BYTES = 1024 * 1024
        const val MAX_ARTIFACT_BYTES = 64L * 1024 * 1024 * 1024
        const val MAX_DELETE_ENTRIES = 4096
        const val GIB = 1024L * 1024 * 1024
    }
}
