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
    private var enrollmentDocument: ByteArray? = null

    private val vpnPermission = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            status.text = "Tailnet authorization accepted. Starting the authenticated Host API…"
            NodeHostGraph.restoreAuthorityAndApi()
        } else {
            showFailure("Enrollment installed, but tailnet VPN authorization was not granted")
        }
    }

    private val guestPicker = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri == null) {
            enrollmentDocument = null
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
                    NodeHostGraph.installEnrollment(enrollment, guest, key)
                } finally {
                    enrollment.fill(0)
                    guest.fill(0)
                }
            }.onSuccess {
                enrollmentDocument = null
                setResult(Activity.RESULT_OK)
                val permissionIntent = android.net.VpnService.prepare(this@EnrollmentImportActivity)
                if (permissionIntent == null) {
                    status.text = "Enrollment installed. Host API will start on the authenticated tailnet."
                    NodeHostGraph.restoreAuthorityAndApi()
                } else {
                    status.text = "Enrollment installed. Authorize the tailnet VPN to start the Host API."
                    vpnPermission.launch(permissionIntent)
                }
            }.onFailure {
                enrollmentDocument = null
                showFailure("Enrollment failed (${it::class.java.simpleName}). No credentials were displayed.")
            }
        }
    }

    private val enrollmentPicker = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri == null) return@registerForActivityResult showFailure("Enrollment document selection cancelled")
        lifecycleScope.launch {
            runCatching { withContext(Dispatchers.IO) { readBounded(uri, EnrollmentJson.MAX_ENROLLMENT_BYTES) } }
                .onSuccess {
                    enrollmentDocument = it
                    status.text = "Now select the separate GuestBootstrapSecret JSON document."
                    guestPicker.launch(arrayOf("application/json", "text/json", "text/plain"))
                }
                .onFailure { showFailure("Enrollment document could not be read") }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        NodeHostGraph.initialize(this)
        ContextCompat.startForegroundService(this, Intent(this, NodeSupervisorService::class.java))
        status = TextView(this).apply { text = "Select both controller-issued JSON documents. No defaults are generated." }
        val button = Button(this).apply {
            text = "Select enrollment documents"
            setOnClickListener { enrollmentPicker.launch(arrayOf("application/json", "text/json", "text/plain")) }
        }
        setContentView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(48, 48, 48, 48)
            addView(status)
            addView(button)
        })
    }

    private fun setBusy(message: String) { status.text = message }
    private fun showFailure(message: String) { status.text = message; setResult(Activity.RESULT_CANCELED) }

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
