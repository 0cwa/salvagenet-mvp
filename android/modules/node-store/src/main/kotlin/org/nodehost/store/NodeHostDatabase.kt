package org.nodehost.store

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(entities = [DesiredRuntimeEntity::class, OperationEntity::class, OperationStepEntity::class], version = 1, exportSchema = true)
abstract class NodeHostDatabase : RoomDatabase() { abstract fun dao(): NodeHostDao }
