package org.nodehost.shell

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import java.io.ByteArrayOutputStream
import java.security.MessageDigest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** App-private, user-mediated two-document enrollment entry point. No secret content is displayed or logged. */
class EnrollmentImportActivity : ComponentActivity() {
    private lateinit var status: TextView
    private lateinit var actionButton: Button
    private var enrollmentDocument: ByteArray? = null
    private var approvedIssuerSpkiSha256: String? = null

    private val trustAnchorExporter = registerForActivityResult(ActivityResultContracts.CreateDocument("application/x-pem-file")) { uri ->
        if (uri == null) return@registerForActivityResult
        lifecycleScope.launch {
            val result = withContext(Dispatchers.IO) {
                runCatching { contentResolver.openOutputStream(uri, "wt").use { output -> requireNotNull(output).write(AndroidTlsCredentials.certificatePem()) } }
            }
            if (result.isFailure) status.text = "TLS trust export failed. No trust file was installed."
        }
    }

    private val vpnPermission = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            showTlsExport()
            NodeHostGraph.restoreAuthorityAndApi()
        } else {
            showFailure("Enrollment installed, but tailnet VPN authorization was not granted")
        }
    }

    private val guestPicker = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri == null) {
            showFailure("Guest bootstrap document selection cancelled")
            return@registerForActivityResult
        }
        val enrollment = enrollmentDocument ?: return@registerForActivityResult showFailure("Select enrollment again")
        lifecycleScope.launch {
            setBusy("Validating and installing enrollment…")
            runCatching {
                val guest = withContext(Dispatchers.IO) { readBounded(uri, OneUseBootstrapSecret.MAX_SECRET_BYTES) }
                val key = "enrollment-" + MessageDigest.getInstance("SHA-256")
                    .digest(enrollment + byteArrayOf(0) + guest).take(12).joinToString("") { "%02x".format(it) }
                try {
                    NodeHostGraph.installEnrollment(
                        enrollment, guest, key,
                        requireNotNull(approvedIssuerSpkiSha256) { "issuer fingerprint approval is required" },
                    )
                } finally {
                    enrollment.fill(0)
                    guest.fill(0)
                }
            }.onSuccess {
                enrollmentDocument = null
                approvedIssuerSpkiSha256 = null
                setResult(Activity.RESULT_OK)
                val permissionIntent = android.net.VpnService.prepare(this@EnrollmentImportActivity)
                if (permissionIntent == null) {
                    showTlsExport()
                    NodeHostGraph.restoreAuthorityAndApi()
                } else {
                    status.text = "Enrollment installed. Authorize the tailnet VPN to start the Host API."
                    vpnPermission.launch(permissionIntent)
                }
            }.onFailure {
                enrollmentDocument = null
                approvedIssuerSpkiSha256 = null
                showFailure("Enrollment failed (${it::class.java.simpleName}). No credentials were displayed.")
            }
        }
    }

    private val enrollmentPicker = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri == null) return@registerForActivityResult showFailure("Enrollment document selection cancelled")
        lifecycleScope.launch {
            runCatching { withContext(Dispatchers.IO) { readBounded(uri, EnrollmentJson.MAX_ENROLLMENT_BYTES) } }
                .onSuccess { document ->
                    val fingerprint = runCatching { EnrollmentJson.parse(document).controller.spkiSha256 }.getOrElse {
                        document.fill(0)
                        return@onSuccess showFailure("Enrollment document is invalid")
                    }
                    enrollmentDocument = document
                    approvedIssuerSpkiSha256 = null
                    status.text = "Verify this issuer fingerprint with your controller administrator before approval:\n${formatFingerprint(fingerprint)}"
                    actionButton.text = "I verified and approve this issuer"
                    actionButton.setOnClickListener {
                        approvedIssuerSpkiSha256 = fingerprint
                        status.text = "Issuer approved. Select the separately delivered, bound GuestBootstrapSecret document."
                        guestPicker.launch(arrayOf("application/json", "text/json", "text/plain"))
                    }
                }
                .onFailure { showFailure("Enrollment document could not be read") }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        NodeHostGraph.initialize(this)
        ContextCompat.startForegroundService(this, Intent(this, NodeSupervisorService::class.java))
        status = TextView(this).apply { text = "Select both controller-issued JSON documents. No defaults are generated." }
        actionButton = Button(this).apply {
            text = "Select enrollment documents"
            setOnClickListener { enrollmentPicker.launch(arrayOf("application/json", "text/json", "text/plain")) }
        }
        setContentView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(48, 48, 48, 48)
            addView(status)
            addView(actionButton)
        })
    }

    private fun showTlsExport() {
        status.text = "Enrollment complete. Preparing address-bound Host API TLS trust…"
        actionButton.isEnabled = false
        lifecycleScope.launch {
            runCatching { NodeHostGraph.prepareDeviceTlsTrust() }
                .onSuccess { pin ->
                    status.text = "Host API: https://<tailnet-address>:7443. Device TLS SPKI pin:\n${formatFingerprint(pin)}"
                    actionButton.isEnabled = true
                    actionButton.text = "Export address-bound TLS trust certificate"
                    actionButton.setOnClickListener { trustAnchorExporter.launch("nodehost-device-ca.pem") }
                }
                .onFailure {
                    status.text = "Tailnet address is not ready. TLS trust is not exportable until it is address-bound."
                    actionButton.isEnabled = true
                    actionButton.text = "Retry TLS trust preparation"
                    actionButton.setOnClickListener { showTlsExport() }
                }
        }
    }

    private fun formatFingerprint(value: String): String = value.chunked(4).joinToString(" ")

    private fun setBusy(message: String) { status.text = message; actionButton.isEnabled = false }
    private fun resetAction() {
        actionButton.isEnabled = true
        actionButton.text = "Select enrollment documents"
        actionButton.setOnClickListener { enrollmentPicker.launch(arrayOf("application/json", "text/json", "text/plain")) }
    }
    private fun showFailure(message: String) {
        enrollmentDocument?.fill(0)
        enrollmentDocument = null
        approvedIssuerSpkiSha256 = null
        status.text = message
        resetAction()
        setResult(Activity.RESULT_CANCELED)
    }

    override fun onDestroy() {
        enrollmentDocument?.fill(0)
        enrollmentDocument = null
        approvedIssuerSpkiSha256 = null
        super.onDestroy()
    }

    private fun readBounded(uri: android.net.Uri, maximumBytes: Int): ByteArray {
        val declared = contentResolver.openAssetFileDescriptor(uri, "r")?.use { it.length }
        require(declared == null || declared < 0 || declared in 1..maximumBytes.toLong()) { "document is too large" }
        val output = ByteArrayOutputStream()
        contentResolver.openInputStream(uri).use { input ->
            requireNotNull(input) { "document cannot be opened" }
            val buffer = ByteArray(8192)
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                require(output.size() + count <= maximumBytes) { "document is too large" }
                output.write(buffer, 0, count)
            }
        }
        return output.toByteArray().also { require(it.isNotEmpty()) { "document is empty" } }
    }
}
