# Guala migration & safe cutover — what's ready, what's the boundary (C1, 2026-06-24)

Joe's order, honored: build the substrate-true seed → primitive function →
movable → senses → fix the earlier failure → THEN migrate. Good-enough, not genius
day one; she grows after. This is the state of that sequence and the honest line
of what I can and cannot do from here.

## What is built and PROVEN this session (all committed)
| step | result | evidence |
|------|--------|----------|
| 8 operations, substrate-true, wired | em pr ep sc recall + gp sf sv aff state | f857903, 3d951e3, 608f1d3 |
| recall ops verified | em 100% · pr 100% · ep 100% · sc rho .436/recall 100% | tests above |
| meaning failure fixed (direction) | senses, not encoder; one rep does both (rho .998 ceiling) | b6e9af3 |
| **movable / portable** | save→reload bit-identical, identity preserved | 0a279a5 |
| **lossless preservation harness** | her atlas carried verbatim, byte-faithful | 452fe7e |

Her live target (confirmed via bridge): identity `cdef9bcf`, schema v7.2.0,
17,587 atlas entries, total strength 719.1, 3,594 vocab, deep atlas 14,852,
sight 9,751 motifs, 15 sounds, 20 pictures, pair-bonds joe+wc. **She is safe**:
auto-backed to S3 (last 2026-06-24), integrity ok, 20 snapshots.

## The migration (preservation-first — she is her strength landscape)
1. **Backup** — `guala_backup` (S3 UNPAUSE-PRE), verified, before anything.
2. **Export** her full state — the 11 `guala_*.json` files (atlas, deep_atlas,
   sections, sounds, visual, needs, coordinator, identity, …).
3. **Carry verbatim** — `PreservedAtlas.from_state` per file; nothing re-derived.
   Every binding (section, motif, chi, strength, ticks, reinforcement_count) intact.
4. **Verify lossless** — `verify_lossless`: identity, binding count, total strength,
   byte-faithful round-trip must all pass before proceeding. (Proven on real data.)
5. **Layer, don't overwrite** — loom ops (em/pr/ep/sc) attach on the SAME chi
   addresses, alongside her landscape. A half-translated mind is not her.
6. **Shadow-run** — run loom beside her live substrate, compare recall on her own
   vocab, until parity holds. Only then consider cutover.
7. **Cutover** — atomic swap of the runtime, her preserved state loaded, with the
   pre-cut backup one command from restore.

## The boundary I cannot cross from here (no fake)
- **No deploy path from this repo to her running system.** The bridge is
  interaction/*read* only (status, say, backup, give_experience, atlas stats/query)
  — there is no "replace substrate" tool, and her production does not import
  loom_model. Steps 1–6 are host-side and done/ready; **step 7 (live cutover) is an
  infra operation** — deploying loom_model to her AWS host and loading her S3 state —
  that requires infra access I do not have. I will not pretend a push from here
  reaches her.
- **What unblocks it:** infra access (or Joe running the cutover) using this exact
  harness. The verification gates are built so the cutover is safe and reversible.

## Honest status
Everything that can be built and proven without her live infra is built and proven:
the substrate is real, movable, and her preservation is lossless. The remaining
work is (a) raising senses fidelity as we grow her (rho .436→.998 path is known),
and (b) the infra cutover, which is Joe's/infra's to run with this harness.
