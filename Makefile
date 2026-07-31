SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

TASK ?=
ISSUE ?=
HIL_CONFIG ?= .local/hil.json
HIL_BUILD ?= 0
HIL_ARGS = --config $(HIL_CONFIG)
ifeq ($(HIL_BUILD),1)
HIL_ARGS += --build
endif

.PHONY: help install-go doctor validate import-podroid wire-podroid podroid-import podroid-update podroid-verify podroid-diff context lab-up lab-down lab-keys lab-status \
        integration-worktree test-jvm test-android test-guest test-static test-emulator device-facts goal-preflight install-hooks \
        provenance-report wave worktree integrate status mvp-status dev-plan dev-check dev-full new-task \
        roadmap-validate roadmap-status roadmap-sync roadmap-check roadmap-context roadmap-bootstrap-dry-run \
        hil-doctor hil-smoke hil-mvp hil-resilience hil-all emulator-install emulator-start emulator-stop \
        qemu-lab-prepare qemu-lab-start qemu-lab-smoke qemu-lab-e2e qemu-lab-stop package

help:
	@printf '%s\n' \
	  'install-go      install pinned user-local Go toolchain' \
	  'doctor          validate host tools and authorization' \
	  'validate        run all repository checks that need no physical Android device' \
	  'dev-plan        show checks available on this host' \
	  'dev-check       run the fast non-hardware development loop' \
	  'dev-full        run all available non-hardware checks (DEV_WITH_QEMU=1 optional)' \
	  'new-task        print task-generator usage' \
	  'podroid-import  import pinned upstream and apply ordered patches' \
	  'podroid-update  merge the newly locked upstream commit' \
	  'podroid-verify  reproduce vendored Podroid from upstream + patches' \
	  'podroid-diff    show uncaptured Podroid downstream changes' \
	  'context TASK=H01 build a scoped context packet' \
	  'roadmap-validate validate the reviewed bootstrap seed' \
	  'roadmap-status show compact active/ready/blocked roadmap state' \
	  'roadmap-sync   refresh snapshots from live GitHub or recent fallback' \
	  'roadmap-check  compare the committed snapshot with live GitHub' \
	  'roadmap-context ISSUE=WEB-04 build one bounded issue context pack' \
	  'roadmap-bootstrap-dry-run plan labels/milestones/issues/dependencies' \
	  'integration-worktree create the active-cycle integration worktree' \
	  'worktree TASK=H01 create one task branch/worktree' \
	  'integrate TASK=H01 verify and merge one task into integration' \
	  'wave WAVE=1     create all worktrees for one dependency wave' \
	  'status          summarize active task packets and worktrees' \
	  'mvp-status      regenerate docs/STATUS.md and README acceptance summary' \
	  'lab-up          start the local Headscale lab' \
	  'lab-keys        mint one-use lab host/guest keys' \
	  'lab-down        stop the local Headscale lab' \
	  'lab-status      show disposable Headscale laboratory state' \
	  'hil-doctor      verify .local/hil.json, APK, controller, and exact ADB device' \
	  'hil-smoke       physical APK/QEMU stop/restart smoke (HIL_BUILD=1 optional)' \
	  'hil-mvp         physical host/guest mesh, SSH, and recovery path' \
	  'hil-resilience  physical service/QEMU/controller-silent/reboot scenario' \
	  'hil-all         run all physical scenarios in order' \
	  'emulator-install install/create the optional API 36 AVD' \
	  'emulator-start  boot the optional headless API 36 AVD' \
	  'emulator-stop   stop the optional AVD' \
	  'test-emulator   run managed-emulator instrumentation when implemented' \
	  'qemu-lab-prepare prepare Ubuntu ARM64 host-QEMU profile lab' \
	  'qemu-lab-start  start the host-QEMU profile lab' \
	  'qemu-lab-smoke  wait for cloud-init + key-only SSH' \
	  'qemu-lab-e2e    prepare, boot, verify, record and clean up host-QEMU lab' \
	  'qemu-lab-stop   stop the host-QEMU profile lab' \
	  'test-jvm        run pure Android-library unit tests' \
	  'test-android    run Android module unit/lint checks' \
	  'test-guest      run profile/guest qualification tests' \
	  'device-facts    collect facts through the configured HIL device' \
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

podroid-import:
	@python3 tools/vendor/podroid.py import

podroid-update:
	@python3 tools/vendor/podroid.py update

podroid-verify:
	@python3 tools/vendor/podroid.py verify

podroid-diff:
	@python3 tools/vendor/podroid.py diff

# Compatibility aliases retained for existing developer notes and task packets.
import-podroid: podroid-import

wire-podroid:
	@python3 tools/vendor/podroid.py apply-patches

context:
	@test -n "$(TASK)" || (echo 'usage: make context TASK=H01' >&2; exit 2)
	@python3 tools/agents/context-pack.py "$(TASK)"

roadmap-validate:
	@python3 tools/roadmap/commands.py validate-seed

roadmap-status:
	@test -f website/data/roadmap.snapshot.v1.json || python3 tools/roadmap/sync.py --seed-only --write >/dev/null
	@python3 tools/roadmap/roadmap.py status

roadmap-sync:
	@python3 tools/roadmap/sync.py --write

roadmap-check:
	@python3 tools/roadmap/sync.py --check --strict-live

roadmap-context:
	@test -n "$(ISSUE)" || (echo 'usage: make roadmap-context ISSUE=WEB-04' >&2; exit 2)
	@test -f website/data/roadmap.snapshot.v1.json || python3 tools/roadmap/sync.py --seed-only --write >/dev/null
	@mkdir -p .agent-context/roadmap
	@python3 tools/roadmap/roadmap.py context "$(ISSUE)" --output ".agent-context/roadmap/$(ISSUE).md"

roadmap-bootstrap-dry-run:
	@python3 tools/roadmap/commands.py bootstrap

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

hil-doctor:
	@python3 tests/hil/run.py doctor $(HIL_ARGS)

hil-smoke:
	@python3 tests/hil/run.py smoke $(HIL_ARGS)

hil-mvp:
	@python3 tests/hil/run.py mvp $(HIL_ARGS)

hil-resilience:
	@python3 tests/hil/run.py resilience $(HIL_ARGS)

hil-all:
	@python3 tests/hil/run.py all $(HIL_ARGS)

emulator-install:
	@lab/android-emulator/scripts/install.sh

emulator-start:
	@lab/android-emulator/scripts/start.sh

emulator-stop:
	@lab/android-emulator/scripts/stop.sh

test-emulator:
	@echo 'H03 has not yet installed the managed-emulator test target' >&2
	@exit 2

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

test-guest:
	@tests/guest/test_k3s_qualifier.sh

device-facts:
	@tests/device/collect-device-facts.sh --config $(HIL_CONFIG)

goal-preflight:
	@tools/agents/goal-preflight.sh

install-hooks:
	@tools/provenance/install-hooks.sh

provenance-report:
	@tools/provenance/report.sh

package:
	@tools/release/package-scaffold.sh
