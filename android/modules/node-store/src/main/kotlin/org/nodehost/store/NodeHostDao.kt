package org.nodehost.store

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update

@Dao
interface NodeHostDao {
    @Query("SELECT * FROM runtime_desired WHERE runtimeId = :id")
    suspend fun desired(id: String): DesiredRuntimeEntity?

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertDesired(entity: DesiredRuntimeEntity)

    @Update
    suspend fun updateDesired(entity: DesiredRuntimeEntity)

    @Query("SELECT * FROM runtime_current WHERE runtimeId = :id")
    suspend fun current(id: String): CurrentRuntimeEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun putCurrent(entity: CurrentRuntimeEntity)

    @Query("SELECT COUNT(*) FROM operations")
    suspend fun operationCount(): Long

    @Query("SELECT * FROM operations WHERE id = :id")
    suspend fun operation(id: String): OperationEntity?

    @Query("SELECT * FROM operations WHERE idempotencyKey = :key")
    suspend fun operationByKey(key: String): OperationEntity?

    @Query("SELECT * FROM operations WHERE runtimeId = :runtimeId AND desiredGeneration = :generation ORDER BY createdAtEpochMillis DESC LIMIT 1")
    suspend fun operationForGeneration(runtimeId: String, generation: Long): OperationEntity?

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertOperation(entity: OperationEntity)

    @Query("""
        UPDATE operations SET state = :newState, currentStepId = :newStepId, errorCode = :newErrorCode,
            updatedAtEpochMillis = :updatedAtEpochMillis
        WHERE id = :id AND state = :expectedState
    """)
    suspend fun compareAndSetOperation(
        id: String,
        expectedState: String,
        newState: String,
        newStepId: String?,
        newErrorCode: String?,
        updatedAtEpochMillis: Long,
    ): Int

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertStep(entity: OperationStepEntity)

    @Query("""
        UPDATE operation_steps SET status = :newStatus, finishedAtEpochMillis = :finishedAtEpochMillis,
            changed = :changed, resultDetail = :resultDetail, errorCode = :errorCode
        WHERE operationId = :operationId AND stepId = :stepId AND attempt = :attempt AND status = 'STARTED'
    """)
    suspend fun completeStartedStep(
        operationId: String,
        stepId: String,
        attempt: Int,
        newStatus: String,
        finishedAtEpochMillis: Long,
        changed: Boolean?,
        resultDetail: String?,
        errorCode: String?,
    ): Int

    @Query("SELECT * FROM operation_steps WHERE operationId = :operationId ORDER BY startedAtEpochMillis, attempt")
    suspend fun steps(operationId: String): List<OperationStepEntity>

    @Query("SELECT * FROM operation_steps WHERE operationId = :operationId AND stepId = :stepId ORDER BY attempt DESC LIMIT 1")
    suspend fun latestStep(operationId: String, stepId: String): OperationStepEntity?
}
