package org.nodehost.store

import androidx.room.Database
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

@Database(
    entities = [DesiredRuntimeEntity::class, CurrentRuntimeEntity::class, OperationEntity::class, OperationStepEntity::class],
    version = 2,
    exportSchema = true,
)
abstract class NodeHostDatabase : RoomDatabase() {
    abstract fun dao(): NodeHostDao

    companion object {
        /** Explicitly preserves all v1 desired state and journal rows. */
        val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("CREATE TABLE runtime_desired_v2 (`runtimeId` TEXT NOT NULL, `generation` INTEGER NOT NULL, `state` TEXT NOT NULL, `profileId` TEXT NOT NULL, `memoryMiB` INTEGER NOT NULL, `vcpus` INTEGER NOT NULL, `dataDiskGiB` INTEGER NOT NULL, `preserveDataOnDelete` INTEGER NOT NULL, PRIMARY KEY(`runtimeId`))")
                db.execSQL("INSERT INTO runtime_desired_v2 (runtimeId, generation, state, profileId, memoryMiB, vcpus, dataDiskGiB, preserveDataOnDelete) SELECT runtimeId, generation, state, profileId, 256, 1, 1, 1 FROM runtime_desired")
                db.execSQL("DROP TABLE runtime_desired")
                db.execSQL("ALTER TABLE runtime_desired_v2 RENAME TO runtime_desired")
                db.execSQL("CREATE TABLE IF NOT EXISTS runtime_current (`runtimeId` TEXT NOT NULL, `kind` TEXT NOT NULL, `profileId` TEXT, `processId` INTEGER, `guestReady` INTEGER, `gracefulDeadlineExceeded` INTEGER, `detail` TEXT, `observedAtEpochMillis` INTEGER NOT NULL, PRIMARY KEY(`runtimeId`))")
                db.execSQL("ALTER TABLE operations ADD COLUMN createdAtEpochMillis INTEGER NOT NULL DEFAULT 0")
                db.execSQL("ALTER TABLE operations ADD COLUMN updatedAtEpochMillis INTEGER NOT NULL DEFAULT 0")
                db.execSQL("CREATE INDEX IF NOT EXISTS index_operations_runtimeId_desiredGeneration ON operations (`runtimeId`, `desiredGeneration`)")
                db.execSQL("CREATE TABLE operation_steps_v2 (`operationId` TEXT NOT NULL, `stepId` TEXT NOT NULL, `attempt` INTEGER NOT NULL, `status` TEXT NOT NULL, `startedAtEpochMillis` INTEGER NOT NULL, `finishedAtEpochMillis` INTEGER, `changed` INTEGER, `resultDetail` TEXT, `errorCode` TEXT, PRIMARY KEY(`operationId`, `stepId`, `attempt`))")
                db.execSQL("INSERT INTO operation_steps_v2 (operationId, stepId, attempt, status, startedAtEpochMillis, finishedAtEpochMillis) SELECT operationId, stepId, attempt, status, startedAt, finishedAt FROM operation_steps")
                db.execSQL("DROP TABLE operation_steps")
                db.execSQL("ALTER TABLE operation_steps_v2 RENAME TO operation_steps")
                db.execSQL("CREATE INDEX IF NOT EXISTS index_operation_steps_operationId ON operation_steps (`operationId`)")
            }
        }
    }
}
