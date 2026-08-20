# E2E compatibility-wrapper instructions

`tests/hil/` is the authoritative physical vertical-slice runner. This directory may only delegate to it or retain non-device contract fixtures.

- Fake or emulator results never close physical gates.
- Host and guest mesh identities must be asserted separately.
- Real ordinary SSH and host-mediated recovery SSH are distinct assertions.
- Exit 77 requires the HIL runner's recorded setup blocker, not a generic manual-follow-up message.
