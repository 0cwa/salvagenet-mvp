# Acceptance evidence

T08 writes one small redacted JSON record per acceptance criterion. Large logs
and device captures stay under ignored `.local/evidence/`; committed records may
reference their digest and collection command but not their secret-bearing
contents.

```sh
python3 tools/evidence/record.py \
  --gate B03 --status PASS \
  --command 'cd android/podroid && ./gradlew :runtime-qemu:testDebugUnitTest' \
  --summary 'Alpine and Ubuntu typed command compiler invariants pass'
```

Then link `evidence/gates/B03.json` from the acceptance ledger.
