#!/usr/bin/env bash
set -euo pipefail
git log --all --format='%h%x09%ad%x09%s%x09%(trailers:key=Agent-Model,valueonly)%x09%(trailers:key=Agent-Run-ID,valueonly)%x09%(trailers:key=Agent-Task-ID,valueonly)' --date=iso-strict
