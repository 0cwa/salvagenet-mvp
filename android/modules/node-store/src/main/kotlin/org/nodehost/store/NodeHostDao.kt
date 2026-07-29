package org.nodehost.store

import androidx.room.*

@Dao
interface NodeHostDao {
    @Query("SELECT * FROM runtime_desired WHERE runtimeId = :id") suspend fun desired(id: String): DesiredRuntimeEntity?
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun putDesired(entity: DesiredRuntimeEntity)
    @Query("SELECT * FROM operations WHERE id = :id") suspend fun operation(id: String): OperationEntity?
    @Query("SELECT * FROM operations WHERE idempotencyKey = :key") suspend fun operationByKey(key: String): OperationEntity?
    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun putOperation(entity: OperationEntity)
    @Insert(onConflict = OnConflictStrategy.ABORT) suspend fun beginStep(entity: OperationStepEntity)
    @Update suspend fun updateStep(entity: OperationStepEntity)
}
