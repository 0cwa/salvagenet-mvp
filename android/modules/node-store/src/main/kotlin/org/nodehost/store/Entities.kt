package org.nodehost.store

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(tableName = "runtime_desired")
data class DesiredRuntimeEntity(
    @PrimaryKey val runtimeId: String,
    val generation: Long,
    val state: String,
    val profileId: String,
    val memoryMiB: Int,
    val vcpus: Int,
    val dataDiskGiB: Int,
    val preserveDataOnDelete: Boolean,
)

/** Last durable observation. It is derived state and never changes desired state. */
@Entity(tableName = "runtime_current")
data class CurrentRuntimeEntity(
    @PrimaryKey val runtimeId: String,
    val kind: String,
    val profileId: String?,
    val processId: Long?,
    val guestReady: Boolean?,
    val gracefulDeadlineExceeded: Boolean?,
    val detail: String?,
    val observedAtEpochMillis: Long,
)

@Entity(
    tableName = "operations",
    indices = [
        Index(value = ["idempotencyKey"], unique = true),
        Index(value = ["runtimeId", "desiredGeneration"]),
    ],
)
data class OperationEntity(
    @PrimaryKey val id: String,
    val idempotencyKey: String,
    val requestDigest: String,
    val runtimeId: String?,
    val desiredGeneration: Long?,
    val state: String,
    val currentStepId: String?,
    val errorCode: String?,
    val createdAtEpochMillis: Long,
    val updatedAtEpochMillis: Long,
)

@Entity(
    tableName = "operation_steps",
    primaryKeys = ["operationId", "stepId", "attempt"],
    indices = [Index(value = ["operationId"])],
)
data class OperationStepEntity(
    val operationId: String,
    val stepId: String,
    val attempt: Int,
    val status: String,
    val startedAtEpochMillis: Long,
    val finishedAtEpochMillis: Long?,
    val changed: Boolean?,
    val resultDetail: String?,
    val errorCode: String?,
)
