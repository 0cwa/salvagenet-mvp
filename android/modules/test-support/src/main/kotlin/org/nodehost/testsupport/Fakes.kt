package org.nodehost.testsupport

import org.nodehost.core.*
import org.nodehost.model.*

class FakeClock(var now: Long = 0) : Clock { override fun epochMillis(): Long = now }
class FakeRuntimeBackend(var observation: RuntimeObservation = RuntimeObservation.Absent(RuntimeId.DEFAULT)) : RuntimeBackend {
    val executed = mutableListOf<RuntimeStep>()
    var failOn: String? = null
    override suspend fun observe(id: RuntimeId): RuntimeObservation = observation
    override suspend fun execute(context: OperationContext, step: RuntimeStep): StepOutcome {
        if (step.id == failOn) error("injected failure: ${step.id}")
        executed += step
        return StepOutcome(changed = true)
    }
}
