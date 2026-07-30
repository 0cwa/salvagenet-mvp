package org.nodehost.shell

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.nodehost.model.BootKind
import org.nodehost.model.BootSpec
import org.nodehost.model.VmProfileId
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class AndroidPackagedProfileCatalogTest {
    private val context: Context = ApplicationProvider.getApplicationContext()
    private val catalog = AndroidPackagedProfileCatalog(context)
    private val placeholderArtifact: (String, Boolean) -> org.nodehost.model.ArtifactRef = { id, _ ->
        org.nodehost.model.ArtifactRef(id, "0".repeat(64), 1)
    }

    @Test fun allCanonicalProfilesLoadFromPackagedJson() {
        val summaries = catalog.summaries()
        assertEquals(3, summaries.size)
        assertEquals(
            setOf("alpine-direct-qualification", "ubuntu-2404-arm64-uefi", "k3s-worker-lab"),
            summaries.map { it.id.value }.toSet(),
        )
        assertEquals(BootKind.DIRECT_KERNEL, summaries.single { it.id.value == "alpine-direct-qualification" }.bootKind)
        assertEquals(BootKind.UEFI, summaries.single { it.id.value == "ubuntu-2404-arm64-uefi" }.bootKind)
    }

    @Test fun alpineDirectKernelProfileResolvesArtifactsAndLegacyVendorData() {
        val alpine = catalog.profile(VmProfileId("alpine-direct-qualification"), false, placeholderArtifact)
        assertTrue(alpine.boot is BootSpec.DirectKernel)
        assertTrue(catalog.vendorData(alpine.id).isNotEmpty())
    }

    @Test fun ubuntuRetainsEveryQualificationCheckFromCanonicalJson() {
        val ubuntu = catalog.profile(VmProfileId("ubuntu-2404-arm64-uefi"), false, placeholderArtifact)
        assertTrue(ubuntu.boot is BootSpec.Uefi)
        assertTrue(
            ubuntu.requirements.qualificationChecks.containsAll(
                setOf("uefi", "virtio-block", "virtio-net", "serial-console", "cloud-init", "openssh")
            )
        )
    }

    @Test fun k3sInheritanceAndRenderedVendorDataArePackaged() {
        val k3s = catalog.profile(VmProfileId("k3s-worker-lab"), false, placeholderArtifact)
        assertEquals(VmProfileId("ubuntu-2404-arm64-uefi"), k3s.extends)
        val vendor = catalog.vendorData(k3s.id).toString(Charsets.UTF_8)
        assertTrue(vendor.startsWith("#cloud-config\n"))
        assertFalse(vendor.contains("{{"))
        assertTrue(vendor.contains("nodehost-qualify-k3s"))
    }

    @Test fun vendorAssetPathsRejectTraversalSegments() {
        requirePackagedVendorAssetPath("guest-init/ubuntu/vendor-data.yaml")
        assertTrue(runCatching { requirePackagedVendorAssetPath("guest-init/../../etc/passwd") }.isFailure)
        assertTrue(runCatching { requirePackagedVendorAssetPath("guest-init/ubuntu/../secret") }.isFailure)
        assertTrue(runCatching { requirePackagedVendorAssetPath("guest-init//vendor-data.yaml") }.isFailure)
    }
}
