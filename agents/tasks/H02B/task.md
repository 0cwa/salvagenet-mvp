# H02B — Guest mesh identity and recovery qualification

## Status

**QUEUED FOR PHASE-START REVIEW — not active work.** H02A must pass and merge first.

## Outcome

Qualify one-use guest Headscale enrollment, a distinct guest identity, ordinary tailnet SSH, `tailscaled` restart, Headscale interruption, and recovery without conflating those failures with guest boot or NoCloud behavior.

## Phase-start review

Before activation:

1. Inspect the merged H02A evidence and remove boot/NoCloud/loopback-SSH assertions already proved there.
2. Confirm a disposable Headscale environment, one-use key creation, cleanup, and redacted evidence can be provisioned without committed credentials.
3. Confirm guest mesh runs through the canonical H02A guest image and bootstrap path rather than adding a second image/profile definition.
4. Separate coordination-server interruption from guest network loss and from recovery-SSH behavior.
5. Reconfirm that host-QEMU guest-mesh evidence cannot close Android or physical gates.

## Acceptance criteria

Provisional until the phase-start review:

- The guest redeems a one-use key and appears as a distinct, exactly matched Headscale identity/tag.
- The one-use key and callback capability are erased after enrollment and are absent from guest disk/log inspection.
- Ordinary SSH succeeds through the guest tailnet identity independently of loopback recovery SSH.
- `tailscaled` restart preserves identity and restores tailnet SSH without reusing enrollment material.
- Temporary Headscale interruption and restoration produce bounded, correctly classified results.
- Loopback recovery SSH remains usable while guest mesh is unavailable.
- All evidence is redacted, machine-readable, bounded, and labeled `host-qemu-guest-mesh` with no Android/physical eligibility.
- Existing H02A guest-boot evidence remains valid and unchanged.

## Required checks

Provisional:

```sh
make validate
make test-guest
make qemu-lab-e2e
make lab-status
python3 tools/agents/verify-scope.py H02B
```

## Phase-end verification

Do not define final exit criteria until H02A has passed and the H02B phase-start review has inspected its evidence. At phase end, verify every mesh, interruption, recovery, secret-hygiene, and cleanup assertion from actual host-QEMU evidence.

## Handoff

Do not implement from this queued packet. Rewrite dependencies, allowed paths, checks, and acceptance criteria after H02A. Never store live Headscale keys or claim Android behavior.
