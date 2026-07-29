package org.nodehost.store

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(tableName = "runtime_desired")
data class DesiredRuntimeEntity(@PrimaryKey val runtimeId: String, val generation: Long, val state: String, val profileId: String, val specJson: String)
@Entity(
    tableName = "operations",
    indices = [Index(value = ["idempotencyKey"], unique = true)],
)
data class OperationEntity(@PrimaryKey val id: String, val idempotencyKey: String, val requestDigest: String, val runtimeId: String?, val desiredGeneration: Long?, val state: String, val currentStepId: String?, val errorCode: String?)
@Entity(tableName = "operation_steps", primaryKeys = ["operationId", "stepId", "attempt"])
data class OperationStepEntity(val operationId: String, val stepId: String, val attempt: Int, val status: String, val startedAt: Long, val finishedAt: Long?)
