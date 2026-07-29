package org.nodehost.model

import org.junit.Assert.assertThrows
import org.junit.Test

class OperationTransitionsTest {
    @Test fun acceptedCanEnterPreflight() = OperationTransitions.requireAllowed(OperationState.ACCEPTED, OperationState.PREFLIGHT)
    @Test fun terminalCannotRestartSilently() = assertThrows(IllegalArgumentException::class.java) {
        OperationTransitions.requireAllowed(OperationState.SUCCEEDED, OperationState.PREFLIGHT)
    }
}
