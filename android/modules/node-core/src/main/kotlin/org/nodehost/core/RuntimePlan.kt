package org.nodehost.core

sealed interface RuntimeStep { val id: String
    data object VerifyProfile : RuntimeStep { override val id = "qemu.verify_profile" }
    data object ResolveArtifacts : RuntimeStep { override val id = "qemu.resolve_artifacts" }
    data object PrepareDisks : RuntimeStep { override val id = "qemu.prepare_disks" }
    data object PrepareBoot : RuntimeStep { override val id = "qemu.prepare_boot" }
    data object StartProcess : RuntimeStep { override val id = "qemu.start_process" }
    data object WaitForQmp : RuntimeStep { override val id = "qemu.wait_for_qmp" }
    data object WaitForGuest : RuntimeStep { override val id = "qemu.wait_for_guest" }
    data object RequestShutdown : RuntimeStep { override val id = "qemu.request_shutdown" }
    data object ForceStop : RuntimeStep { override val id = "qemu.force_stop" }
    data object RemoveSystem : RuntimeStep { override val id = "qemu.remove_system" }
}

data class RuntimePlan(val steps: List<RuntimeStep>)
