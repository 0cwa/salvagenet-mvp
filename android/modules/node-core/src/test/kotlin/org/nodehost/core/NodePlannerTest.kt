package org.nodehost.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.nodehost.model.DesiredRuntimeState
import org.nodehost.model.RuntimeId
import org.nodehost.model.RuntimeObservation
import org.nodehost.model.RuntimeSpec
import org.nodehost.model.VmProfileId

class NodePlannerTest {
    private val runningDesired = RuntimeSpec(
        id = RuntimeId.DEFAULT,
        generation = 1,
        desiredState = DesiredRuntimeState.RUNNING,
        profileId = VmProfileId("ubuntu-2404-arm64-uefi"),
        memoryMiB = 1024,
        vcpus = 2,
        dataDiskGiB = 8,
    )

    @Test
    fun absentRuntimeGetsStartPlan() {
        val plan = NodePlanner.plan(
            runningDesired,
            RuntimeObservation.Absent(RuntimeId.DEFAULT),
        )
        assertEquals(RuntimeStep.VerifyProfile, plan.steps.first())
        assertEquals(RuntimeStep.WaitForGuest, plan.steps.last())
    }

    @Test
    fun stopRequestsGracefulShutdownWithoutImmediateForce() {
        val desired = runningDesired.copy(desiredState = DesiredRuntimeState.STOPPED)
        val plan = NodePlanner.plan(
            desired,
            RuntimeObservation.Running(RuntimeId.DEFAULT, processId = 123, guestReady = true),
        )
        assertEquals(listOf(RuntimeStep.RequestShutdown), plan.steps)
    }

    @Test
    fun forceStopAppearsOnlyAfterGracefulDeadline() {
        val desired = runningDesired.copy(desiredState = DesiredRuntimeState.STOPPED)
        val beforeDeadline = NodePlanner.plan(
            desired,
            RuntimeObservation.Stopping(
                RuntimeId.DEFAULT,
                processId = 123,
                gracefulDeadlineExceeded = false,
            ),
        )
        val afterDeadline = NodePlanner.plan(
            desired,
            RuntimeObservation.Stopping(
                RuntimeId.DEFAULT,
                processId = 123,
                gracefulDeadlineExceeded = true,
            ),
        )
        assertTrue(beforeDeadline.steps.isEmpty())
        assertEquals(listOf(RuntimeStep.ForceStop), afterDeadline.steps)
    }
}
