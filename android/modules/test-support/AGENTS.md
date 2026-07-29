# test-support instructions

- No production shortcuts depend on test-support.
- Fakes must model unknown outcomes and retries, not only happy paths.
- Fault injectors are deterministic and excluded from release artifacts.
