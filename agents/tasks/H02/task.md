# H02 — Host-QEMU and Headscale guest E2E

## Status

**SUPERSEDED AT THE POST-F01 PHASE BOUNDARY.** Do not activate or implement this combined packet.

## Phase-start review

F01 merged at `246d551ca7e691a0319a4b30e29d6e4905cd9910` and removed the profile/artifact ambiguity. The required review concluded that this packet still combined two independent failure domains:

1. canonical guest boot, UEFI/QMP, NoCloud, key-only loopback SSH, restart, and secret hygiene;
2. guest Headscale identity, tailnet SSH, mesh interruption, and recovery.

The work is therefore split into:

- **H02A** — canonical Ubuntu guest boot qualification; the sole next active candidate;
- **H02B** — guest mesh identity and recovery qualification; queued behind H02A.

## Acceptance criteria

This historical packet has no executable acceptance criteria. Its replacement criteria are authoritative in `agents/tasks/H02A/task.md` and, after a later phase-start review, `agents/tasks/H02B/task.md`.

## Phase-end verification

The split itself is accepted when:

- H02 is absent from the active DAG;
- H02A alone is active/planned with explicit entry, acceptance, evidence, and exit criteria;
- H02B remains queued and depends on H02A;
- no Headscale behavior is authorized inside H02A.

## Handoff

Retain this packet only for provenance. Use H02A for guest boot work. Do not copy this combined scope into a branch or worktree.
