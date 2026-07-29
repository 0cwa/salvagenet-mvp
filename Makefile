SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

TASK ?=

.PHONY: help install-go doctor validate import-podroid wire-podroid context lab-up lab-down lab-keys lab-status \
        integration-worktree test-jvm test-android test-guest test-static device-facts goal-preflight install-hooks \
        provenance-report wave worktree integrate status mvp-status emulator-install emulator-start emulator-stop qemu-lab-prepare qemu-lab-start qemu-lab-smoke qemu-lab-stop package

help:
	@printf '%s\n' \
	  'install-go      install pinned user-local Go toolchain' \
	  'doctor          validate host tools and authorization' \
	  'validate        run all scaffold checks that need no Android SDK/device' \
	  'import-podroid  import the pinned Podroid snapshot into android/podroid' \
	  'wire-podroid    wire sibling modules into Podroid Gradle settings' \
	  'context TASK=T02 build a scoped context packet' \
	  'integration-worktree create the integration branch/worktree' \
	  'worktree TASK=T02 create the task branch/worktree' \
	  'integrate TASK=T02 verify and merge one task into integration' \
	  'wave WAVE=1     create all worktrees for one dependency wave' \
	  'status          summarize task packets and git worktrees' \
	  'mvp-status      regenerate docs/STATUS.md and README acceptance summary' \
	  'lab-up          start the local Headscale lab' \
	  'lab-keys        mint one-use lab host/guest keys' \
	  'lab-down        stop the local Headscale lab' \
	  'emulator-install install/create the optional API 36 AVD' \
	  'emulator-start  boot the optional headless API 36 AVD' \
	  'emulator-stop   stop the optional AVD' \
	  'qemu-lab-prepare prepare Ubuntu ARM64 host-QEMU profile lab' \
	  'qemu-lab-start  start the host-QEMU profile lab' \
	  'qemu-lab-smoke  wait for cloud-init + key-only SSH' \
	  'qemu-lab-stop   stop the host-QEMU profile lab' \
	  'test-jvm        run pure Android-library unit tests after import' \
	  'test-android    run Android module unit/lint checks after import' \
	  'test-guest      run profile/guest qualification tests' \
	  'test-static     alias for validate' \
	  'device-facts    collect authorized physical-device facts' \
	  'goal-preflight  check overnight goal prerequisites' \
	  'install-hooks   install provenance hooks' \
	  'provenance-report show agent trailers in git history' \
	  'package         create a clean handoff archive in ../'

install-go:
	@tools/bootstrap/install-go.sh

doctor:
	@tools/bootstrap/doctor.sh

validate:
	@tools/ci/check.sh

test-static: validate

import-podroid:
	@tools/bootstrap/import-podroid-subtree.sh

wire-podroid:
	@python3 tools/bootstrap/wire-podroid.py

context:
	@test -n "$(TASK)" || (echo 'usage: make context TASK=T02' >&2; exit 2)
	@python3 tools/agents/context-pack.py "$(TASK)"

integration-worktree:
	@tools/agents/create-integration-worktree.sh

worktree:
	@test -n "$(TASK)" || (echo 'usage: make worktree TASK=T02' >&2; exit 2)
	@tools/agents/create-task-worktree.sh "$(TASK)"

integrate:
	@test -n "$(TASK)" || (echo 'usage: make integrate TASK=T02' >&2; exit 2)
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

qemu-lab-stop:
	@lab/qemu/scripts/stop.sh

test-jvm:
	@test -x android/podroid/gradlew || (echo 'import Podroid first' >&2; exit 2)
	@cd android/podroid && ./gradlew \
	  :node-model:testDebugUnitTest \
	  :node-core:testDebugUnitTest \
	  :test-support:testDebugUnitTest

test-android:
	@test -x android/podroid/gradlew || (echo 'import Podroid first' >&2; exit 2)
	@cd android/podroid && ./gradlew \
	  :node-store:testDebugUnitTest \
	  :runtime-qemu:testDebugUnitTest \
	  :mesh-tailscale:testDebugUnitTest \
	  :control-api:testDebugUnitTest \
	  :node-shell:testDebugUnitTest \
	  :app:lintDebug

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
