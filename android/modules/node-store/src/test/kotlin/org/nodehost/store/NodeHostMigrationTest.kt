package org.nodehost.store

import android.content.Context
import androidx.room.Room
import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.sqlite.db.SupportSQLiteOpenHelper
import androidx.sqlite.db.framework.FrameworkSQLiteOpenHelperFactory
import androidx.test.core.app.ApplicationProvider
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith
import org.nodehost.model.RuntimeId
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class NodeHostMigrationTest {
    private val context = ApplicationProvider.getApplicationContext<Context>()
    private val databaseName = "nodehost-migration-test.db"

    @After fun cleanUp() { context.deleteDatabase(databaseName) }

    @Test
    fun migrationOneToTwoPreservesDesiredStateAndJournal() = runBlocking {
        context.deleteDatabase(databaseName)
        val helper = FrameworkSQLiteOpenHelperFactory().create(
            SupportSQLiteOpenHelper.Configuration.builder(context)
                .name(databaseName)
                .callback(object : SupportSQLiteOpenHelper.Callback(1) {
                    override fun onCreate(db: SupportSQLiteDatabase) {
                        db.execSQL("CREATE TABLE runtime_desired (`runtimeId` TEXT NOT NULL, `generation` INTEGER NOT NULL, `state` TEXT NOT NULL, `profileId` TEXT NOT NULL, `specJson` TEXT NOT NULL, PRIMARY KEY(`runtimeId`))")
                        db.execSQL("CREATE TABLE operations (`id` TEXT NOT NULL, `idempotencyKey` TEXT NOT NULL, `requestDigest` TEXT NOT NULL, `runtimeId` TEXT, `desiredGeneration` INTEGER, `state` TEXT NOT NULL, `currentStepId` TEXT, `errorCode` TEXT, PRIMARY KEY(`id`))")
                        db.execSQL("CREATE UNIQUE INDEX index_operations_idempotencyKey ON operations (`idempotencyKey`)")
                        db.execSQL("CREATE TABLE operation_steps (`operationId` TEXT NOT NULL, `stepId` TEXT NOT NULL, `attempt` INTEGER NOT NULL, `status` TEXT NOT NULL, `startedAt` INTEGER NOT NULL, `finishedAt` INTEGER, PRIMARY KEY(`operationId`, `stepId`, `attempt`))")
                        db.execSQL("INSERT INTO runtime_desired VALUES ('default', 7, 'RUNNING', 'alpine-direct', '{}')")
                        db.execSQL("INSERT INTO operations VALUES ('op-700', 'idempotency-key-0700', '${"a".repeat(64)}', 'default', 7, 'ACCEPTED', 'qemu.start_process', NULL)")
                        db.execSQL("INSERT INTO operation_steps VALUES ('op-700', 'qemu.start_process', 1, 'STARTED', 123, NULL)")
                    }
                    override fun onUpgrade(db: SupportSQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit
                })
                .build(),
        )
        helper.writableDatabase
        helper.close()

        val migrated = Room.databaseBuilder(context, NodeHostDatabase::class.java, databaseName)
            .addMigrations(NodeHostDatabase.MIGRATION_1_2)
            .build()
        val repository = RoomOperationRepository(migrated, object : org.nodehost.core.Clock {
            override fun epochMillis(): Long = 999
        })
        assertEquals(7L, repository.loadDesiredRuntime(RuntimeId.DEFAULT)?.generation)
        assertEquals("op-700", repository.operationForDesired(repository.loadDesiredRuntime(RuntimeId.DEFAULT)!!)?.id?.value)
        assertEquals(StepStatus.STARTED.name, repository.steps(org.nodehost.model.OperationId("op-700")).single().status)
        migrated.close()
    }
}
