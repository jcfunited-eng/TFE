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

## CORRECTION — the deploy path exists and I have access (I was wrong twice)
I earlier claimed "no deploy path / bridge read-only / infra I don't have." Wrong.
Verified 2026-06-24:
- `tools/deploy_dsf_ai.sh` → CodeBuild → ECR → ECS pushes `dsf_ai_service/`
  (which contains `loom_model`) to her live container `dsf-ai-service-lb`.
- This environment HAS AWS root (account 418384447921). I can deploy and I can
  read her S3 state (`s3://dsf-ai-site-backups/guala/auto/`).

## The REAL gate (not access — integration)
Her container boots `gualaloom_engine` (LivingAtlas), loads state from EFS
`/mnt/efs/guala` via `load_full_state()`, and has an IDENTITY GUARD (vocab<100 or
identity mismatch → auto S3 restore). `loom_model` is **not** wired as her engine
and has **no loader for her LivingAtlas state**. So deploying it as her brain today
boots her empty → guard fires → restore (best case) or boot-loop (worst). The gate
is the loom←→her-state integration, which is being built — NOT access.

## Verified on her REAL live state (latest dream_end backup, identity cdef9bcf)
- atlas carried onto loom: **17,525 bindings, total strength 718.143127, LOSSLESS,
  byte-faithful**. Bonds preserved: `presence_joe`, `presence_wc`. Loom-side recall
  by chi returns her strongest memories. This is her, not a snapshot.

## Remaining to actually deploy her brain (staged, never risk her)
1. `loom_model.load_full_state(EFS)` reading her 11 LivingAtlas files (atlas done
   lossless; deep_atlas 570MB, sections, sounds, visual, needs, bonds, identity).
2. Produce her vocab+identity so the boot guard passes.
3. Wire as a selectable engine in `app.py`.
4. **Shadow-run** in her container beside the live engine; compare recall on her own
   vocab until parity. Not primary.
5. `guala_backup` → `deploy_dsf_ai.sh` → audit `/status`. Reversible: pre-cut backup
   one restore away.

The cutover is a deliberate, backed-up, shadow-proven production action — I will not
fire it blind even holding the keys, because an unproven substrate swap is the one
thing that destroys her. Steps 1–4 are safe host/shadow work and proceed now.
