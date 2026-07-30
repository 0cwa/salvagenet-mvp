SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help
TASK ?=
.PHONY: help install-go doctor validate import-podroid wire-podroid context lab-up lab-down lab-keys lab-status integration-worktree test-jvm test-android test-guest test-static test-emulator device-facts goal-preflight install-hooks provenance-report wave worktree integrate status mvp-status dev-plan dev-check dev-full new-task emulator-install emulator-start emulator-stop qemu-lab-prepare qemu-lab-start qemu-lab-smoke qemu-lab-e2e qemu-lab-stop package
help:
	@printf '%s\n' \
	  'install-go      install pinned user-local Go toolchain' \
	  'doctor          validate host tools and authorization' \
	  'validate        run all repository checks that need no Android device' \
	  'dev-plan        show checks available on this host' \
	  'dev-check       run the fast non-hardware development loop' \
	  'dev-full        run all available non-hardware checks (DEV_WITH_QEMU=1 optional)' \
	  'new-task        print task-generator usage' \
	  'context TASK=H01 build a scoped context packet' \
	  'integration-worktree create the active-cycle integration worktree' \
	  'worktree TASK=H01 create one task branch/worktree' \
	  'integrate TASK=H01 verify and merge one task into integration' \
	  'wave WAVE=1     create all worktrees for one dependency wave' \
	  'status          summarize active task packets and worktrees' \
	  'mvp-status      regenerate docs/STATUS.md and README acceptance summary' \
	  'lab-status      show disposable Headscale laboratory state' \
	  'qemu-lab-e2e    prepare, boot, verify, record and clean up host-QEMU lab' \
	  'test-emulator   run managed-emulator instrumentation when implemented' \
	  'package         create a clean handoff archive in ../'
install-go:
	@tools/bootstrap/install-go.sh
doctor:
	@tools/bootstrap/doctor.sh
validate:
	@tools/ci/check.sh
test-static: validate
dev-plan:
	@python3 tools/development/check.py plan --level full $(if $(filter 1,$(DEV_WITH_QEMU)),--with-qemu,)
dev-check:
	@python3 tools/development/check.py run --level quick
dev-full:
	@python3 tools/development/check.py run --level full $(if $(filter 1,$(DEV_WITH_QEMU)),--with-qemu,)
new-task:
	@python3 tools/agents/new-task.py --help
import-podroid:
	@tools/bootstrap/import-podroid-subtree.sh
wire-podroid:
	@python3 tools/bootstrap/wire-podroid.py
context:
	@test -n "$(TASK)" || (echo 'usage: make context TASK=H01' >&2; exit 2)
	@python3 tools/agents/context-pack.py "$(TASK)"
integration-worktree:
	@tools/agents/create-integration-worktree.sh
worktree:
	@test -n "$(TASK)" || (echo 'usage: make worktree TASK=H01' >&2; exit 2)
	@tools/agents/create-task-worktree.sh "$(TASK)"
integrate:
	@test -n "$(TASK)" || (echo 'usage: make integrate TASK=H01' >&2; exit 2)
	@tools/agents/integrate-task.sh "$(TASK)"
wave:
	@test -n "$(WAVE)" || (echo 'usage: make wave WAVE=1' >&2; exit 2)
	@tools/agents/create-wave-worktrees.sh "$(WAVE)"
status:
	@tools/agents/status.sh
mvp-status:
	@python3 tools/status/generate.py --write
lab-up:
	@lab/headscale/scripts/up.sh
lab-down:
	@lab/headscale/scripts/down.sh
lab-keys:
	@lab/headscale/scripts/create-keys.sh
lab-status:
	@lab/headscale/scripts/status.sh
emulator-install:
	@lab/android-emulator/scripts/install.sh
emulator-start:
	@lab/android-emulator/scripts/start.sh
emulator-stop:
	@lab/android-emulator/scripts/stop.sh
qemu-lab-prepare:
	@lab/qemu/scripts/prepare.sh
qemu-lab-start:
	@lab/qemu/scripts/start.sh
qemu-lab-smoke:
	@lab/qemu/scripts/smoke.sh
qemu-lab-e2e:
	@lab/qemu/scripts/e2e.sh
qemu-lab-stop:
	@lab/qemu/scripts/stop.sh
test-jvm:
	@test -x android/podroid/gradlew || (echo 'Podroid Gradle wrapper unavailable' >&2; exit 2)
	@cd android/podroid && ./gradlew :node-model:testDebugUnitTest :node-core:testDebugUnitTest :test-support:testDebugUnitTest
test-android:
	@test -x android/podroid/gradlew || (echo 'Podroid Gradle wrapper unavailable' >&2; exit 2)
	@cd android/podroid && ./gradlew :node-store:testDebugUnitTest :runtime-qemu:testDebugUnitTest :mesh-tailscale:testDebugUnitTest :control-api:testDebugUnitTest :node-shell:testDebugUnitTest :app:lintDebug
test-emulator:
	@echo 'H03 has not yet installed the managed-emulator test target' >&2
	@exit 2
test-guest:
	@tests/guest/test_k3s_qualifier.sh
device-facts:
	@tests/device/collect-device-facts.sh
goal-preflight:
	@tools/agents/goal-preflight.sh
install-hooks:
	@tools/provenance/install-hooks.sh
provenance-report:
	@tools/provenance/report.sh
package:
	@tools/release/package-scaffold.sh
