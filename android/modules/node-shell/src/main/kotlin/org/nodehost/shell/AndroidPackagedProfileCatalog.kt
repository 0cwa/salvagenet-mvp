package org.nodehost.shell

import android.content.Context
import java.io.ByteArrayOutputStream
import java.io.InputStream
import org.json.JSONArray
import org.json.JSONObject
import org.nodehost.model.Acceleration
import org.nodehost.model.Architecture
import org.nodehost.model.ArtifactRef
import org.nodehost.model.BootKind
import org.nodehost.model.BootSpec
import org.nodehost.model.DataDiskSpec
import org.nodehost.model.DeviceTransport
import org.nodehost.model.DiskFormat
import org.nodehost.model.HealthKind
import org.nodehost.model.HealthSpec
import org.nodehost.model.InitializationKind
import org.nodehost.model.InitializationSpec
import org.nodehost.model.MachineFamily
import org.nodehost.model.MachineSpec
import org.nodehost.model.ProfileRequirements
import org.nodehost.model.RecoverySshSpec
import org.nodehost.model.SystemDiskSpec
import org.nodehost.model.VmProfile
import org.nodehost.model.VmProfileId
import org.nodehost.model.WritableLayer

internal data class PackagedProfileSummary(
    val id: VmProfileId,
    val version: Int,
    val bootKind: BootKind,
)

/** Reads the three qualified profiles from immutable APK assets and rejects contract drift before side effects. */
internal class AndroidPackagedProfileCatalog(context: Context) {
    private val assets = context.applicationContext.assets
    private val documents: Map<String, JSONObject> by lazy(::loadDocuments)

    fun summaries(): List<PackagedProfileSummary> = EXPECTED_PROFILE_IDS.sorted().map { id ->
        val document = documents.getValue(id)
        val metadata = document.getJSONObject("metadata")
        val boot = document.getJSONObject("spec").getJSONObject("boot")
        PackagedProfileSummary(VmProfileId(id), metadata.getInt("version"), bootKind(boot.getString("type")))
    }

    fun profile(
        id: VmProfileId,
        verifyArtifacts: Boolean,
        artifactResolver: (String, Boolean) -> ArtifactRef,
    ): VmProfile {
        val root = documents[id.value] ?: error("unsupported profile: ${id.value}")
        requireKeys(root, ROOT_FIELDS, "profile root")
        require(root.getString("apiVersion") == API_VERSION) { "unsupported profile API version" }
        require(root.getString("kind") == KIND) { "unsupported profile kind" }

        val metadata = root.getJSONObject("metadata")
        requireKeys(metadata, if (metadata.has("extends")) METADATA_FIELDS_WITH_EXTENDS else METADATA_FIELDS, "profile metadata")
        require(metadata.getString("id") == id.value) { "profile asset id does not match requested id" }
        val version = metadata.getInt("version").also { require(it >= 1) }
        val extends = metadata.optString("extends").takeIf(String::isNotEmpty)?.let(::VmProfileId)

        val spec = root.getJSONObject("spec")
        requireKeys(spec, SPEC_FIELDS, "profile spec")
        require(spec.getString("architecture") == "aarch64") { "Android QEMU supports only aarch64 profiles" }

        val machine = spec.getJSONObject("machine")
        requireKeys(machine, MACHINE_FIELDS, "profile machine")
        require(machine.getString("family") == "virt") { "Android QEMU supports only the virt machine" }
        require(machine.getString("acceleration") == "tcg") { "stock Android supports only the qualified TCG profile" }
        require(machine.getString("deviceTransport") == "pci") { "qualified profiles require PCI virtio transport" }
        val machineSpec = MachineSpec(
            family = MachineFamily.VIRT,
            acceleration = Acceleration.TCG,
            deviceTransport = DeviceTransport.PCI,
            cpuModel = machine.getString("cpuModel"),
        )

        val bootObject = spec.getJSONObject("boot")
        val boot = when (bootKind(bootObject.getString("type"))) {
            BootKind.DIRECT_KERNEL -> {
                requireKeys(bootObject, DIRECT_BOOT_FIELDS, "direct-kernel boot")
                BootSpec.DirectKernel(
                    artifactResolver(bootObject.getString("kernelArtifact"), verifyArtifacts),
                    artifactResolver(bootObject.getString("initramfsArtifact"), verifyArtifacts),
                    bootObject.getString("kernelArgumentProfile"),
                )
            }
            BootKind.UEFI -> {
                requireKeys(bootObject, UEFI_BOOT_FIELDS, "UEFI boot")
                BootSpec.Uefi(
                    artifactResolver(bootObject.getString("firmwareCodeArtifact"), verifyArtifacts),
                    artifactResolver(bootObject.getString("firmwareVarsArtifact"), verifyArtifacts),
                )
            }
        }

        val systemDisk = spec.getJSONObject("systemDisk")
        requireKeys(systemDisk, SYSTEM_DISK_FIELDS, "system disk")
        val systemDiskSpec = SystemDiskSpec(
            artifactResolver(systemDisk.getString("artifact"), verifyArtifacts),
            diskFormat(systemDisk.getString("format")),
            writableLayer(systemDisk.getString("writableLayer")),
        )

        val dataDisk = spec.getJSONObject("dataDisk")
        requireKeys(dataDisk, DATA_DISK_FIELDS, "data disk")
        require(dataDisk.getString("format") == "raw") { "qualified data disks must use raw format" }
        val dataDiskSpec = DataDiskSpec(dataDisk.getInt("defaultSizeGiB"), dataDisk.getBoolean("persistent"))

        val initialization = spec.getJSONObject("initialization")
        val initializationKind = initializationKind(initialization.getString("type"))
        requireKeys(
            initialization,
            if (initializationKind == InitializationKind.NOCLOUD_NET) NOCLOUD_FIELDS else LEGACY_INIT_FIELDS,
            "initialization",
        )
        val vendorAsset = initialization.getString("vendorData")
        requireVendorAsset(vendorAsset)
        val initializationSpec = InitializationSpec(
            initializationKind,
            vendorAsset,
            initialization.optString("metadataPath").takeIf(String::isNotEmpty),
        )

        val network = spec.getJSONObject("network")
        requireKeys(network, NETWORK_FIELDS, "network")
        val primary = network.getJSONObject("primary")
        requireKeys(primary, PRIMARY_NETWORK_FIELDS, "primary network")
        require(primary.getString("type") == "slirp") { "qualified MVP profiles require SLIRP" }
        val recovery = network.getJSONObject("recoverySsh")
        requireKeys(recovery, RECOVERY_FIELDS, "recovery SSH")
        val recoverySpec = RecoverySshSpec(
            recovery.getInt("guestPort"),
            recovery.getString("bind") == "loopback",
        )

        val health = spec.getJSONObject("health")
        val healthKind = healthKind(health.getString("type"))
        requireKeys(health, if (healthKind == HealthKind.CONSOLE_MARKER) HEALTH_MARKER_FIELDS else HEALTH_FIELDS, "health")
        val healthSpec = HealthSpec(healthKind, health.optString("marker").takeIf(String::isNotEmpty))

        val requirements = spec.getJSONObject("requirements")
        requireKeys(requirements, REQUIREMENT_FIELDS, "requirements")
        val checks = requirements.getJSONArray("qualificationChecks").strictStringSet("qualificationChecks", 32)
        val requirementSpec = ProfileRequirements(
            requirements.getInt("minimumMemoryMiB"),
            requirements.getInt("minimumStorageGiB"),
            checks,
        )

        return VmProfile(
            id = id,
            version = version,
            extends = extends,
            architecture = Architecture.AARCH64,
            machine = machineSpec,
            boot = boot,
            systemDisk = systemDiskSpec,
            dataDisk = dataDiskSpec,
            initialization = initializationSpec,
            recoverySsh = recoverySpec,
            health = healthSpec,
            requirements = requirementSpec,
        )
    }

    fun vendorData(profileId: VmProfileId): ByteArray {
        val document = documents[profileId.value] ?: error("unsupported profile: ${profileId.value}")
        val relative = document.getJSONObject("spec").getJSONObject("initialization").getString("vendorData")
        return readAsset(assetPath(relative), MAX_VENDOR_DATA_BYTES).also { bytes ->
            require(bytes.isNotEmpty() && bytes.toString(Charsets.UTF_8).startsWith("#cloud-config\n")) {
                "profile vendor data is not rendered cloud-config: $relative"
            }
            require(!bytes.toString(Charsets.UTF_8).contains("{{")) { "profile vendor data contains unresolved template markers" }
        }
    }

    private fun loadDocuments(): Map<String, JSONObject> {
        val values = EXPECTED_PROFILE_IDS.associateWith { id ->
            val root = JSONObject(readAsset("$PROFILE_ASSET_ROOT/$id/profile.json", MAX_PROFILE_BYTES).toString(Charsets.UTF_8))
            requireKeys(root, ROOT_FIELDS, "profile root")
            val metadata = root.getJSONObject("metadata")
            require(metadata.getString("id") == id) { "profile asset path and metadata id differ" }
            root
        }
        values.forEach { (id, root) ->
            val parent = root.getJSONObject("metadata").optString("extends").takeIf(String::isNotEmpty)
            require(parent == null || parent in values) { "profile $id extends an unavailable profile" }
            require(parent != id) { "profile cannot extend itself" }
        }
        return values
    }

    private fun requireVendorAsset(relative: String) {
        require(VENDOR_ASSET.matches(relative)) { "invalid vendor-data asset path" }
        readAsset(assetPath(relative), MAX_VENDOR_DATA_BYTES)
    }

    private fun assetPath(relative: String) = "$NODEHOST_ASSET_ROOT/$relative"

    private fun readAsset(path: String, maximumBytes: Int): ByteArray = assets.open(path).use { input ->
        input.readBounded(maximumBytes)
    }

    private fun InputStream.readBounded(maximumBytes: Int): ByteArray {
        val output = ByteArrayOutputStream()
        val buffer = ByteArray(8 * 1024)
        var total = 0
        while (true) {
            val count = read(buffer)
            if (count < 0) break
            total += count
            require(total <= maximumBytes) { "packaged asset exceeds size bound" }
            output.write(buffer, 0, count)
        }
        return output.toByteArray()
    }

    private fun requireKeys(value: JSONObject, expected: Set<String>, name: String) {
        require(value.keys().asSequence().toSet() == expected) { "$name fields are invalid" }
    }

    private fun JSONArray.strictStringSet(name: String, maximum: Int): Set<String> {
        require(length() <= maximum) { "$name contains too many values" }
        val values = buildSet { for (index in 0 until length()) add(getString(index)) }
        require(values.size == length()) { "$name contains duplicate values" }
        return values
    }

    private fun bootKind(value: String) = when (value) {
        "direct-kernel" -> BootKind.DIRECT_KERNEL
        "uefi" -> BootKind.UEFI
        else -> error("unsupported boot type: $value")
    }

    private fun diskFormat(value: String) = when (value) {
        "raw" -> DiskFormat.RAW
        "qcow2" -> DiskFormat.QCOW2
        "squashfs" -> DiskFormat.SQUASHFS
        else -> error("unsupported disk format: $value")
    }

    private fun writableLayer(value: String) = when (value) {
        "qcow2-overlay" -> WritableLayer.QCOW2_OVERLAY
        "separate-ext4-overlay" -> WritableLayer.SEPARATE_EXT4_OVERLAY
        "none" -> WritableLayer.NONE
        else -> error("unsupported writable layer: $value")
    }

    private fun initializationKind(value: String) = when (value) {
        "legacy-podroid" -> InitializationKind.LEGACY_PODROID
        "nocloud-net" -> InitializationKind.NOCLOUD_NET
        else -> error("unsupported initialization type: $value")
    }

    private fun healthKind(value: String) = when (value) {
        "console-marker" -> HealthKind.CONSOLE_MARKER
        "metadata-callback" -> HealthKind.METADATA_CALLBACK
        "ssh" -> HealthKind.SSH
        else -> error("unsupported health type: $value")
    }

    private companion object {
        const val API_VERSION = "nodehost.example/v1alpha1"
        const val KIND = "VirtualMachineProfile"
        const val NODEHOST_ASSET_ROOT = "nodehost"
        const val PROFILE_ASSET_ROOT = "$NODEHOST_ASSET_ROOT/profiles"
        const val MAX_PROFILE_BYTES = 64 * 1024
        const val MAX_VENDOR_DATA_BYTES = 128 * 1024
        val EXPECTED_PROFILE_IDS = setOf(
            "alpine-direct-qualification",
            "ubuntu-2404-arm64-uefi",
            "k3s-worker-lab",
        )
        val VENDOR_ASSET = Regex("guest-init/[a-z0-9./_-]+")
        val ROOT_FIELDS = setOf("apiVersion", "kind", "metadata", "spec")
        val METADATA_FIELDS = setOf("id", "version")
        val METADATA_FIELDS_WITH_EXTENDS = setOf("id", "version", "extends")
        val SPEC_FIELDS = setOf("architecture", "machine", "boot", "systemDisk", "dataDisk", "initialization", "network", "health", "requirements")
        val MACHINE_FIELDS = setOf("family", "acceleration", "deviceTransport", "cpuModel")
        val DIRECT_BOOT_FIELDS = setOf("type", "kernelArtifact", "initramfsArtifact", "kernelArgumentProfile")
        val UEFI_BOOT_FIELDS = setOf("type", "firmwareCodeArtifact", "firmwareVarsArtifact")
        val SYSTEM_DISK_FIELDS = setOf("artifact", "format", "writableLayer")
        val DATA_DISK_FIELDS = setOf("format", "defaultSizeGiB", "persistent")
        val LEGACY_INIT_FIELDS = setOf("type", "vendorData")
        val NOCLOUD_FIELDS = setOf("type", "vendorData", "metadataPath")
        val NETWORK_FIELDS = setOf("primary", "recoverySsh")
        val PRIMARY_NETWORK_FIELDS = setOf("type")
        val RECOVERY_FIELDS = setOf("guestPort", "bind")
        val HEALTH_FIELDS = setOf("type")
        val HEALTH_MARKER_FIELDS = setOf("type", "marker")
        val REQUIREMENT_FIELDS = setOf("minimumMemoryMiB", "minimumStorageGiB", "qualificationChecks")
    }
}
