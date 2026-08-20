# Physical HIL evidence

The physical runner writes ignored, reviewable evidence under `.local/hil-runs/`. It never edits acceptance records itself.

## Integrity rules

- one exact source commit and APK SHA-256;
- one explicitly configured device serial, stored only as a hash and redacted from command records;
- per-run SSH known-host state;
- exact Headscale node identity matching;
- bounded command output and failure logcat;
- distinct assertions for controller-silent and configured controller-unavailable intervals;
- interrupted or blocked runs cannot produce PASS evidence.

## Controller-unavailable evidence

A period with no controller calls demonstrates that desired state is not lease-driven, but it is not the B17 seal. B17 promotion requires `resilience.controller-unavailable`, produced only when paired offline/online commands are configured and the Host API is observed unavailable before the timed interval.

## Promotion

`tools/evidence/promote-hil.py` validates the run, current commit, APK digest, scenario, and gate-specific assertions. It is dry-run by default. `--write` delegates compact record creation to `tools/evidence/record.py` and then runs the evidence validator. Review local artifacts and redaction before promotion.
