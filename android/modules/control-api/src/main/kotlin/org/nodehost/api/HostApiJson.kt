package org.nodehost.api

import com.google.gson.Gson
import com.google.gson.JsonElement
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import java.math.BigDecimal
import org.nodehost.model.OperationRecord

internal object HostApiJson {
    private val gson = Gson()

    fun encode(value: Any?): String = gson.toJson(value)

    fun operation(value: OperationRecord): Map<String, Any?> = linkedMapOf(
        "id" to value.id.value,
        "state" to value.state.name,
        "currentStepId" to value.currentStepId,
        "errorCode" to value.errorCode,
    )

    fun parseImageImport(raw: ByteArray): Pair<ImageImportRequest, ByteArray> {
        val objectValue = parseObject(raw)
        objectValue.requireKeys(setOf("sourceUrl", "sha256", "expectedSizeBytes"))
        val request = ImageImportRequest(
            sourceUrl = objectValue.requiredString("sourceUrl", 2048),
            sha256 = objectValue.requiredString("sha256", 64),
            expectedSizeBytes = objectValue.requiredLong("expectedSizeBytes"),
        )
        return request to encode(request).toByteArray(Charsets.UTF_8)
    }

    fun parseApplyVm(vmId: String, raw: ByteArray): Pair<ApplyVmRequest, ByteArray> {
        val root = parseObject(raw)
        root.requireKeys(setOf("generation", "desiredState", "profileId", "resources", "dataDisk"))
        val resources = root.requiredObject("resources")
        resources.requireKeys(setOf("memoryMiB", "vcpus"))
        val dataDisk = root.requiredObject("dataDisk")
        dataDisk.requireKeys(setOf("sizeGiB", "preserveOnDelete"))
        val request = ApplyVmRequest(
            id = vmId,
            generation = root.requiredLong("generation"),
            desiredState = root.requiredString("desiredState", 16),
            profileId = root.requiredString("profileId", 64),
            memoryMiB = resources.requiredInt("memoryMiB"),
            vcpus = resources.requiredInt("vcpus"),
            dataDiskGiB = dataDisk.requiredInt("sizeGiB"),
            preserveOnDelete = dataDisk.requiredBoolean("preserveOnDelete"),
        )
        val canonical = linkedMapOf<String, Any?>(
            "vmId" to request.id,
            "generation" to request.generation,
            "desiredState" to request.desiredState,
            "profileId" to request.profileId,
            "memoryMiB" to request.memoryMiB,
            "vcpus" to request.vcpus,
            "dataDiskGiB" to request.dataDiskGiB,
            "preserveOnDelete" to request.preserveOnDelete,
        )
        return request to encode(canonical).toByteArray(Charsets.UTF_8)
    }

    private fun parseObject(raw: ByteArray): JsonObject {
        require(raw.isNotEmpty()) { "request body is required" }
        require(raw.size <= HostApiController.MAX_REQUEST_BYTES) { "request body is too large" }
        val element = JsonParser.parseString(raw.toString(Charsets.UTF_8))
        require(element.isJsonObject) { "request body must be a JSON object" }
        return element.asJsonObject
    }

    private fun JsonObject.requireKeys(allowed: Set<String>) {
        val actual = keySet()
        require(actual == allowed) {
            val unknown = actual - allowed
            val missing = allowed - actual
            "invalid fields; unknown=$unknown missing=$missing"
        }
    }

    private fun JsonObject.required(name: String): JsonElement =
        get(name)?.takeUnless { it.isJsonNull } ?: throw IllegalArgumentException("$name is required")

    private fun JsonObject.requiredObject(name: String): JsonObject {
        val value = required(name)
        require(value.isJsonObject) { "$name must be an object" }
        return value.asJsonObject
    }

    private fun JsonObject.requiredString(name: String, maxLength: Int): String {
        val value = required(name)
        require(value.isJsonPrimitive && value.asJsonPrimitive.isString) { "$name must be a string" }
        return value.asString.also { require(it.isNotEmpty() && it.length <= maxLength) { "$name is out of range" } }
    }

    private fun JsonObject.requiredLong(name: String): Long {
        val value = required(name)
        require(value.isJsonPrimitive && value.asJsonPrimitive.isNumber) { "$name must be an integer" }
        val decimal = runCatching { BigDecimal(value.asString) }.getOrNull()
            ?: throw IllegalArgumentException("$name must be an integer")
        return try {
            decimal.longValueExact()
        } catch (_: ArithmeticException) {
            throw IllegalArgumentException("$name must be an integer")
        }
    }

    private fun JsonObject.requiredInt(name: String): Int {
        val number = requiredLong(name)
        require(number in Int.MIN_VALUE..Int.MAX_VALUE) { "$name is out of range" }
        return number.toInt()
    }

    private fun JsonObject.requiredBoolean(name: String): Boolean {
        val value = required(name)
        require(value.isJsonPrimitive && value.asJsonPrimitive.isBoolean) { "$name must be a boolean" }
        return value.asBoolean
    }
}
