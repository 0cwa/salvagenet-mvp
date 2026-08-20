package org.nodehost.api

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class ArtifactUploadJsonTest {
    @Test fun parsesStrictUploadCreateRequest() {
        val raw = """{"artifactId":"ubuntu-arm64","sha256":"${"a".repeat(64)}","expectedSizeBytes":8}""".toByteArray()
        val (request, canonical) = HostApiJson.parseArtifactUploadCreate(raw)
        assertEquals("ubuntu-arm64", request.artifactId)
        assertEquals(8L, request.expectedSizeBytes)
        assertEquals(HostApiJson.encode(request), canonical.toString(Charsets.UTF_8))
    }

    @Test fun rejectsUnknownUploadCreateField() {
        val raw = """{"artifactId":"ubuntu-arm64","sha256":"${"a".repeat(64)}","expectedSizeBytes":8,"path":"/tmp/x"}""".toByteArray()
        assertThrows(IllegalArgumentException::class.java) { HostApiJson.parseArtifactUploadCreate(raw) }
    }
}
