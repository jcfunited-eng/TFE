# GL-SHIP: Automated Teaching + Night Fixes — 2026-07-17/18

Session record (c1). Everything below is committed on `guala-live`; live
state verified where stated. Joe's order of the night: "there is supposed
to be automated teaching and it should study gaps — we don't have a lot
of time."

## Shipped and verified live

**Automated teaching** (`ee4a990` + live-path fix `8ec2dce`):
- `GapLedger` (`knowledge_gaps.json`): consumes the two honest gap
  signals nothing previously read — certified-composer refusals at the
  engine's fact_compose site, and fresh organism recognition surprise
  ≥ 0.8 at read. Bounded, fsync'd, off the engine object (pickle-safe).
- `gap_study` interleave slot: top gaps re-studied via concordance over
  a bounded archive of her own recent reading, through the same gated
  feed path as books; addressed-marking with 6h cooldown.
- `tutor` interleave slot: teach → ask → correct, Joe's manual flow
  automated. Stem from a real sentence of her reading; her real answer
  via converse (`source="curriculum"` — presence-exempt, teacher weight
  0.7 vs joe 1.6); verdict graded by the sentence's actual continuation;
  correction through the one real teacher gateway. 40 teaches/day cap,
  block-suppressed, defers to live human turns.
- **Live proof (:682, first hours):** boot line
  `interleave=['worldfeed', 'gap_study', 'tutor']`; first real exchange:
  stem "a great stone dropped from above" → her attempt silence →
  graded incorrect → taught "smashed through the bottom of the".
- **Lesson relearned the hard way:** `_gl_init` in app.py is the ONLY
  live boot path; `substrate_runner.boot_substrate()` is a dead
  duplicate. The first deploy registered the slots there and they
  silently never ran (`interleave=['worldfeed']`). Every runner feature
  must be wired on BOTH paths.

**Voice restored** (config): `VOICE_WHISPER=0` had pinned spoken-word
recognition OFF since the July-16 OOM crisis — 346
`spoken_word_recognition_unavailable` events in one boot while Joe
talked to her. Flipped to 1 on task def :683 under the 30GB envelope.

**Conversational repeat-guard** (`1e41b42`): identical seeds vote
deterministically, so the same question earned the same babble verbatim
(Joe saw 5×) or silence. A would-repeat composition now shifts down her
OWN ranked votes; autonomous path keeps strict refusal.

**Second-chance babble seeds** (`dfba8d4`): live histogram showed 7/8
autonomous attempts dying `organism_empty` — window seeds are
sensory-frame dominated. On empty vote + full refusal, one retry from
her most recent read sentence (her reading life, never an atlas dump).

**Save-freeze fix** (`3773d4c`): ONE missing picture .jpg aborted EVERY
full save from 15:07 (her durable state froze while life accumulated).
Missing display originals now drop loudly and the save completes; her
actual visual memory (the grid) was never at risk; video assets stay
strict. Self-heals the dead pointer.

**Deploy-trap fix** (`bb9f5e3`): a clean seal refusal (proven
state=RUNNING, no certificate) no longer triggers enforce-zero-owners —
that trap stopped a healthy owner twice in one night, once mid-restore.

**Storage (sweep Finding 2)**: 14 of 17 retained generations failed
validation (in-place-mutated hard-linked stores) — invisible to BOTH
keep-N pruning and recovery, ~15GB of unrestorable garbage. Deleted
live; `prune_generations` now age-guards them out (`dfba8d4`, test).

**Page** (published + invalidated): correction fetch 10s→30s (Joe's
"signal timed out"), spoken sound_frame 8s→25s (slow transcriptions
were silently dropped).

**Ops hardening** (task def :682/:683 + service): container health
check 10s/3× → 30s/10×; ALB grace 120s → 2400s. Both had been killing
tasks mid-restore (init ≈ 30 min on a big life; frozen saves had also
blocked the boot-speed locator, compounding).

## Found and filed, not yet fixed

- **RAM (sweep Finding 1) root-caused**: `_run_dream_cycle` grows
  retained memory +300→1240MB per cycle, compounding with life;
  converse costs +0; plain reading ~140MB/session; language forgetting
  (Change-3 branch) works but is ~2% of growth. malloc_trim reclaims ~0
  (NOT allocator high-water). Prime suspect: numpy mode banks grown by
  dream motif-locking (30,755 motifs live). Next arc: per-owner nbytes
  census at high water, then bound/compact.
- **Seal is structurally broken on a busy substrate**: organism queue
  (1999 items × ~1s) needs ~33 min to settle; curl and ALB give up at
  900s; a timed-out seal then reads as ambiguous and fail-closes. Fix:
  async seal (start + poll) and settle that survives backlog. Interim:
  manual task-def turnover (used for :679–:683).
- **Change-3 forgetting**: mechanisms proven (strand/window growth
  decelerates, releases, distillation); acceptance soak fails on the
  dream growth outside its scope. Merge decision parked; branch intact.
- **Wild-things monotony**: activity picker breaks score ties by list
  order. Real bug, small fix, queued.
- **Mosaic fit test PASSED** (separate report:
  `GL-RPT-MOSAIC-FIT-TEST-20260717-v1.md`, branch
  `gl/mosaic-fit-bench-20260717`): 10-scalar Dirichlet token
  reproduces a 4096-neuron crowd's decisions on unseen sizes at
  30k–111k×; recursion carries the winner, not yet the confidence.
