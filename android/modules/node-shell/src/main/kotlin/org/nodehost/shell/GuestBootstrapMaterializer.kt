package org.nodehost.shell

import java.security.MessageDigest
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.nodehost.model.GuestAccessEnrollment
import org.nodehost.model.GuestSshAuthorization
import org.nodehost.model.NodeEnrollment
import org.nodehost.model.SensitiveValue

/** A separately minted guest identity. The host mesh key is never reused by the guest. */
data class GuestMeshBootstrap(
    val controlUrl: String,
    val oneUseAuthKey: SensitiveValue,
    val hostname: String,
) {
    init {
        require(controlUrl.startsWith("https://") || controlUrl.startsWith("http://"))
        require(Regex("[a-z0-9][a-z0-9-]{0,62}").matches(hostname))
    }

    override fun toString(): String = "GuestMeshBootstrap(controlUrl=$controlUrl, hostname=$hostname, oneUseAuthKey=<redacted>)"
}

data class GuestBootstrapProfile(
    val token: String,
    val metadataPath: String,
    val metaData: String,
    val userData: String,
) {
    init {
        require(Regex("[A-Za-z0-9_-]{32,128}").matches(token))
        require(metadataPath == "/v1/bootstrap/$token/")
        require(userData.length <= MAX_BOOTSTRAP_DOCUMENT_CHARS)
        require(metaData.length <= MAX_BOOTSTRAP_DOCUMENT_CHARS)
    }

    private companion object { const val MAX_BOOTSTRAP_DOCUMENT_CHARS = 128 * 1024 }
}

/** Materializes NoCloud documents and a single-use secret without passwords or reusable defaults. */
class GuestBootstrapMaterializer(
    private val tokenFactory: () -> String,
) {
    fun materialize(enrollment: NodeEnrollment, artifact: GuestBootstrapSecretArtifact): MaterializedGuestBootstrap {
        val guestMesh = artifact.mesh
        require(guestMesh.controlUrl == enrollment.hostMesh.controlUrl) {
            "host and guest must enroll with the same authoritative control server"
        }
        require(guestMesh.oneUseAuthKey.value != enrollment.hostMesh.oneUseAuthKey.value) {
            "host and guest mesh identities require distinct one-use keys"
        }
        require(artifact.sshAccess == enrollment.guestAccess) {
            "guest bootstrap SSH authority must match enrollment"
        }
        val token = tokenFactory()
        require(Regex("[A-Za-z0-9_-]{32,128}").matches(token)) { "invalid generated bootstrap token" }
        val path = "/v1/bootstrap/$token/"
        val metaData = "instance-id: default\nlocal-hostname: ${guestMesh.hostname}\n"
        val userData = cloudConfig(enrollment.guestAccess, token)
        return MaterializedGuestBootstrap(
            GuestBootstrapProfile(token, path, metaData, userData),
            OneUseBootstrapSecret(token, artifact.raw),
            artifact.callbackCapability,
        )
    }

    private fun cloudConfig(access: GuestAccessEnrollment, token: String): String = buildString {
        append("#cloud-config\n")
        append("package_update: true\npackages: [openssh-server, ca-certificates, curl, jq]\n")
        append("ssh_pwauth: false\ndisable_root: true\n")
        append("users:\n  - name: ${access.sshUser}\n    lock_passwd: true\n    shell: /bin/bash\n")
        append("write_files:\n")
        append("  - path: /var/lib/nodehost/bootstrap.env\n    owner: root:root\n    permissions: '0600'\n    content: |\n")
        append("      NODEHOST_METADATA_BASE=http://10.0.2.2:8080/v1/bootstrap/$token/\n")
        append("      NODEHOST_BOOTSTRAP_TOKEN=$token\n")
        append("  - path: /etc/ssh/sshd_config.d/90-nodehost.conf\n    owner: root:root\n    permissions: '0644'\n    content: |\n")
        append("      PasswordAuthentication no\n      KbdInteractiveAuthentication no\n      PermitRootLogin no\n")
        when (val authorization = access.authorization) {
            is GuestSshAuthorization.AuthorizedKeys -> {
                append("ssh_authorized_keys:\n")
                authorization.publicKeys.sorted().forEach { append("  - ").append(it).append('\n') }
            }
            is GuestSshAuthorization.UserCertificateAuthority -> {
                append("  - path: /etc/ssh/nodehost-user-ca.pub\n    owner: root:root\n    permissions: '0644'\n    content: |\n")
                append("      ").append(authorization.publicKey).append('\n')
            }
        }
        append("  - path: /usr/local/sbin/nodehost-bootstrap\n    owner: root:root\n    permissions: '0700'\n    content: |\n")
        bootstrapScript().lineSequence().forEach { append("      ").append(it).append('\n') }
        append("runcmd:\n  - [/usr/local/sbin/nodehost-bootstrap]\n")
    }

    private fun bootstrapScript() = """#!/bin/bash
set -euo pipefail
umask 077
. /var/lib/nodehost/bootstrap.env
case "${'$'}NODEHOST_METADATA_BASE" in http://10.0.2.2:8080/v1/bootstrap/*/) ;; *) exit 2;; esac
secret=${'$'}(mktemp /run/nodehost-bootstrap.XXXXXX)
trap 'rm -f "${'$'}secret"' EXIT
curl --fail --silent --show-error --max-time 30 --max-filesize 65536 --proto '=http' \
  -H "Authorization: Bearer ${'$'}NODEHOST_BOOTSTRAP_TOKEN" \
  "${'$'}{NODEHOST_METADATA_BASE}bootstrap-secret" -o "${'$'}secret"
unset NODEHOST_BOOTSTRAP_TOKEN
rm -f /var/lib/nodehost/bootstrap.env
control_url=${'$'}(jq -er '.mesh.controlUrl|select(test("^https?://"))' "${'$'}secret")
auth_key=${'$'}(jq -er '.mesh.oneUseAuthKey|select(length>=16 and length<=512)' "${'$'}secret")
hostname=${'$'}(jq -er '.mesh.hostname|select(test("^[a-z0-9][a-z0-9-]{0,62}${'$'}"))' "${'$'}secret")
ssh_user=${'$'}(jq -er '.ssh.user|select(test("^[a-z_][a-z0-9_-]{0,31}${'$'}"))' "${'$'}secret")
id "${'$'}ssh_user" >/dev/null
install -d -m 0700 -o "${'$'}ssh_user" -g "${'$'}ssh_user" "/home/${'$'}ssh_user/.ssh"
jq -r '.ssh.emergencyAuthorizedKeys[]?' "${'$'}secret" > "/home/${'$'}ssh_user/.ssh/authorized_keys"
chown "${'$'}ssh_user:${'$'}ssh_user" "/home/${'$'}ssh_user/.ssh/authorized_keys"
chmod 0600 "/home/${'$'}ssh_user/.ssh/authorized_keys"
if jq -e '.ssh.userCaPublicKey' "${'$'}secret" >/dev/null; then
  jq -er '.ssh.userCaPublicKey' "${'$'}secret" > /etc/ssh/nodehost-user-ca.pub
  echo 'TrustedUserCAKeys /etc/ssh/nodehost-user-ca.pub' >> /etc/ssh/sshd_config.d/90-nodehost.conf
fi
systemctl reload ssh
if ! command -v tailscale >/dev/null; then
  install -d -m 0755 /usr/share/keyrings
  curl --fail --silent --show-error --max-time 30 --proto '=https' https://pkgs.tailscale.com/stable/ubuntu/noble.noarmor.gpg -o /usr/share/keyrings/tailscale-archive-keyring.gpg
  curl --fail --silent --show-error --max-time 30 --proto '=https' https://pkgs.tailscale.com/stable/ubuntu/noble.tailscale-keyring.list -o /etc/apt/sources.list.d/tailscale.list
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y tailscale
fi
systemctl enable --now tailscaled
tailscale up --login-server "${'$'}control_url" --auth-key "${'$'}auth_key" --hostname "${'$'}hostname" --accept-dns=true
unset auth_key
callback=${'$'}(jq -er '.callback.readyUrl' "${'$'}secret")
capability=${'$'}(jq -er '.callback.capability' "${'$'}secret")
rm -f "${'$'}secret"
trap - EXIT
curl --fail --silent --show-error --max-time 30 --proto '=http' -X POST \
  -H "Authorization: Bearer ${'$'}capability" "${'$'}callback"
""".trimIndent()

}

class MaterializedGuestBootstrap internal constructor(
    val profile: GuestBootstrapProfile,
    val secret: OneUseBootstrapSecret,
    val callbackCapability: SensitiveValue,
)

/** Concurrent redemption has one winner; a successful response permanently consumes the payload. */
class OneUseBootstrapSecret internal constructor(token: String, secret: ByteArray) {
    private val expectedTokenDigest = digest(token)
    private val lock = Mutex()
    private var payload: ByteArray? = secret.copyOf()

    internal suspend fun persistenceCopy(): ByteArray? = lock.withLock { payload?.copyOf() }

    suspend fun redeem(presentedToken: String): ByteArray? = lock.withLock {
        if (presentedToken.length !in 32..128 || !MessageDigest.isEqual(digest(presentedToken), expectedTokenDigest)) return@withLock null
        val result = payload ?: return@withLock null
        payload = null
        result.copyOf()
    }

    companion object {
        const val MAX_SECRET_BYTES = 64 * 1024
        private fun digest(value: String): ByteArray = MessageDigest.getInstance("SHA-256").digest(value.toByteArray())
    }
}
