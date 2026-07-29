package org.nodehost.shell

import org.json.JSONArray
import org.json.JSONObject
import org.nodehost.model.GuestAccessEnrollment
import org.nodehost.model.GuestSshAuthorization
import org.nodehost.model.SensitiveValue

/** Parsed form of the public GuestBootstrapSecret contract. Raw bytes are retained for one-use delivery. */
data class GuestBootstrapSecretArtifact(
    val mesh: GuestMeshBootstrap,
    val sshAccess: GuestAccessEnrollment,
    val callbackCapability: SensitiveValue,
    internal val raw: ByteArray,
)

object GuestBootstrapSecretJson {
    fun parse(raw: ByteArray): GuestBootstrapSecretArtifact {
        require(raw.isNotEmpty() && raw.size <= OneUseBootstrapSecret.MAX_SECRET_BYTES) {
            "guest bootstrap secret is empty or too large"
        }
        val root = JSONObject(raw.toString(Charsets.UTF_8)).exactly("apiVersion", "kind", "mesh", "ssh", "callback")
        require(root.string("apiVersion") == "nodehost.example/v1alpha1") { "unsupported guest bootstrap apiVersion" }
        require(root.string("kind") == "GuestBootstrapSecret") { "unsupported guest bootstrap kind" }
        val mesh = root.obj("mesh").exactly("controlUrl", "oneUseAuthKey", "hostname")
        val ssh = root.obj("ssh")
        val sshKeys = ssh.namesSet()
        require(sshKeys == setOf("user", "userCaPublicKey") || sshKeys == setOf("user", "emergencyAuthorizedKeys")) {
            "guest bootstrap must contain exactly one SSH authorization form"
        }
        val authorization = if (ssh.has("userCaPublicKey")) {
            GuestSshAuthorization.UserCertificateAuthority(ssh.string("userCaPublicKey"))
        } else {
            GuestSshAuthorization.AuthorizedKeys(ssh.stringSet("emergencyAuthorizedKeys", 4))
        }
        val callback = root.obj("callback").exactly("readyUrl", "capability")
        require(callback.string("readyUrl") == "http://10.0.2.2:8080/v1/bootstrap/ready") {
            "guest callback must target the fixed bootstrap service"
        }
        return GuestBootstrapSecretArtifact(
            mesh = GuestMeshBootstrap(mesh.string("controlUrl"), SensitiveValue(mesh.string("oneUseAuthKey")), mesh.string("hostname")),
            sshAccess = GuestAccessEnrollment(ssh.string("user"), authorization),
            callbackCapability = SensitiveValue(callback.string("capability")),
            raw = raw.copyOf(),
        )
    }

    private fun JSONObject.exactly(vararg expected: String) = apply {
        require(namesSet() == expected.toSet()) { "invalid guest bootstrap fields" }
    }
    private fun JSONObject.namesSet(): Set<String> = buildSet {
        val names = keys()
        while (names.hasNext()) add(names.next())
    }
    private fun JSONObject.obj(name: String): JSONObject = get(name).also { require(it is JSONObject) { "$name must be an object" } } as JSONObject
    private fun JSONObject.string(name: String): String = get(name).also { require(it is String && it.isNotEmpty()) { "$name must be a string" } } as String
    private fun JSONObject.stringSet(name: String, maximum: Int): Set<String> {
        val values = get(name)
        require(values is JSONArray && values.length() in 1..maximum) { "$name is out of range" }
        return buildSet {
            repeat(values.length()) { index -> add(values.getString(index)) }
        }.also { require(it.size == values.length()) { "$name contains duplicates" } }
    }
}
