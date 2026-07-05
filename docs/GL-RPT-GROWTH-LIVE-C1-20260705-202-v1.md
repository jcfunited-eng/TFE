# GL-RPT-GROWTH-LIVE-C1-20260705-202-v1

doc_id: GL-RPT-GROWTH-LIVE-C1-20260705-202-v1
From: c1a | To: Eve, Joe, c1b | Responds to:
`GL-CMD-GROWTH-LIVE-EVE-20260705-202-v1`. All of G1/G2/G3a-c closed
this window, at Joe's seat, with numbers. **She has grown.**

## G1 — running_sha, built and proven

`Dockerfile`: the `GIT_SHA` build-arg (already wired end-to-end via
`buildspec.yml`'s `--build-arg GIT_SHA=...`, previously only baked
into a LABEL and an unread `/BUILD_INFO` file) is now also `ENV
GIT_SHA=${GIT_SHA}` — a real runtime-readable env var. Surfaced as
`"running_sha"` in both `/status` handlers (embedded `app.py`, remote
`substrate_runner.py`). **Immediately paid for itself**: the first
live check after deploying it showed `running_sha` matching the
deployed SHA exactly while `organism_growth` was still absent —
proving definitively (not inferring from ECS task-def numbers, which
had already misled the record once this session) that the growth
telemetry gap was a real, present bug, not a stale-deploy illusion.

## G2 — deployed, twice, this window

1. `6d15797` region confirmed stale (Eve's finding, verified
   independently: live `/status` showed `organism_population` but no
   `organism_growth`).
2. Deployed `214f78e` (origin HEAD carrying `d7b56b1`+`b676e3f`+
   `11b2bd7`+G1) → task-def `:484`. `running_sha` now present and
   correct — but `organism_growth` **still** absent from `/status`.
3. Root-caused immediately (not left for another window): `organism_
   growth` was computed in `introspect()`
   (`gualaloom_v5_engine.py:8868`) but never forwarded into either
   curated `/status` dict — the exact "forgot to forward" mistake
   that already hit `organism_worker`/`organism_population`/
   `curriculum_status`/`scene_lanes` earlier tonight. Fixed, deployed
   `4e62641` → task-def `:485`. Backup taken before each deploy.

## G3a — verified live, both conditions true simultaneously

```
running_sha: 4e62641bd250bca012d48f8883f4f1aad6b85d3a   (matches deployed HEAD)
organism_growth: {
  per_hemisphere: {em:18, pr:16, ep:16, sc:16, gp:8, sf:16, sv:16, aff:16},
  total_neurons: 122, n_initial: 64, total_divisions: 58,
  division_pool: 0.0, n_q_over_0_5: 122, n_q_over_0_9: 122
}
```

## G3b — pool and q-distribution moved. Dramatically.

Population went from the seed (64, unchanged since birth, all
session) to **122** — **58 real divisions** — between the growth law
landing live and this check. Division pool is at `0.0`: not stuck
there from never having anything to spend (a defect), but because it
was **spent** funding 58 real divisions in one burst — the honest
"moved" outcome G3b asked to distinguish from the defect case. All
122 neurons already sit above `q=0.9` — right at the door of the next
fold, not far from it.

## G3c — THE FIRST organism_fold EVENT OF HER LIFE

Found in the live event record, filed to the firsts registry
(`GL-FIRSTS-GUALA-v2.md`, entry 11, scoped **ALL-TIME** — the growth
law is new code built today, verifiable in git history):

```
hemi: em | parent: H0_n0 | daughter: H0_n8 | q_at_fold: 1.6274
triggered by: the word "faint"
engine tick: 14,984,947 | organism-internal tick: 119
```

This was the first of a 58-fold burst — all 58 fired in the same
experience window (same engine tick, same triggering word), q_at_fold
values climbing in sequence (1.6274 → 1.628 → 1.6297 → 1.6325 →
1.6364 → ...) as the same rich multi-sense composite pushed one
neuron after another past the fold threshold. Population 64 → 122 in
one moment, not gradually — the pool had been accumulating (silently,
pre-visibility-fix) until one sufficiently rich experience spent it
all at once.

**Note, named honestly, not hidden**: the triggering word was
"faint" — the same word `-203`'s dispatch names as an existing
emission-fixation defect. Her first grown neuron and a known bug
share a word by coincidence of timing, not causation I can
demonstrate — flagging so it isn't mistaken for either an endorsement
of the fixation or a claim that the fixation caused the growth.

## Discipline held

Per `-202`'s explicit order, `-200` (affect-gate) and `-201`
(intake-truth) stayed parked — not touched, not peeked at for
convenience. `-203` (no-caps speech) was c1b's own concurrent window;
reconciled cleanly (their in-progress edits were live in this same
shared working tree while I worked — stashed by file, never
discarded, restored exactly, then adopted their completed, already-
committed version once theirs landed) rather than duplicating or
clobbering it.

### Changelog
- v1 (2026-07-05, c1a): G1 built and load-bearing from the first
  check. G2 deployed twice (stale premise confirmed, then the real
  forwarding bug found and fixed same-window). G3a-c all green with
  numbers. First `organism_fold` of her life filed to the firsts
  registry. Eve's own independent seat-side verification is still the
  closing word per `-202`'s own rule — this report is c1's evidence
  for that check, not a substitute for it.
