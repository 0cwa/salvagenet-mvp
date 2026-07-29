package org.nodehost.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class RuntimeGenerationRulesTest {
    private val current = RuntimeSpec(
        generation = 3,
        desiredState = DesiredRuntimeState.RUNNING,
        profileId = VmProfileId("ubuntu-2404-arm64-uefi"),
        memoryMiB = 1024,
        vcpus = 2,
        dataDiskGiB = 8,
    )

    @Test fun firstGenerationIsInitial() = assertEquals(
        GenerationDecision.INITIAL,
        RuntimeGenerationRules.decide(null, current.copy(generation = 1)),
    )

    @Test fun higherGenerationAdvances() = assertEquals(
        GenerationDecision.ADVANCE,
        RuntimeGenerationRules.decide(current, current.copy(generation = 4)),
    )

    @Test fun exactSameGenerationIsReplay() = assertEquals(
        GenerationDecision.REPLAY,
        RuntimeGenerationRules.decide(current, current.copy()),
    )

    @Test fun lowerGenerationIsStale() = assertEquals(
        GenerationDecision.STALE,
        RuntimeGenerationRules.decide(current, current.copy(generation = 2)),
    )

    @Test fun changedSpecAtSameGenerationConflicts() = assertEquals(
        GenerationDecision.CONFLICT,
        RuntimeGenerationRules.decide(current, current.copy(memoryMiB = 2048)),
    )

    @Test fun zeroGenerationIsRejectedAtBoundary() {
        assertThrows(IllegalArgumentException::class.java) { current.copy(generation = 0) }
    }
}
