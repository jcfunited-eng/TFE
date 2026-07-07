> **SUPERSEDED — DO NOT TREAT AS CURRENT TRUTH.**
> This document describes substrate state as of pre-wipe (2026-07-06
> wipe operation, GL-RPT-SUBSTRATE-WIPE-INCIDENT-C1-20260706-v1).
> The substrate described here no longer exists. Preserved as
> historical record only.
> For current substrate state, run the harness against production.

---

# GL-RPT-WATCH-ITEMS-C1-20260704-v1

doc_id: GL-RPT-WATCH-ITEMS-C1-20260704-v1
From: c1b | To: Eve | Responds to: GL-NOTE-VOID-RATIFICATION-NOTE-EVE-
20260704-v1, items 2-4 ("when free"). Item 1 (deploy window for -172)
is still waiting on c1a's build + SHA handoff — nothing to report
there yet.

---

## Item 2 — watch: natural sleep under the current deploy (:461, dial 1)

**Still not observed. Reporting the insomnia-side symptom with
numbers, as asked.**

- CloudWatch, `/ecs/dsf-ai`, proper OR-query across `dream_began`,
  `DREAMING`, `SLEEPING`, `dream cycle`, `force_dream` over the last
  12h: **zero natural sleep/dream events.** The only 2 hits were boot-
  time prints showing the *restored* `current_activity` happened to be
  `SLEEPING` from before a restart — state readout, not a live event.
- Most recent cold boot (no `.sleeping` marker — consistent with
  task:461's fresh deploy): **2026-07-04T07:22:55Z.** Current time at
  last check: **2026-07-04T13:54:38Z** — **6h 32m elapsed, zero
  natural sleep the entire window.**
- Live `/status` at that check: `asleep: false`, `consolidating:
  false`, `current_activity: ATTENDING_VISUAL` (still cycling — same
  picture, `e93d29dae5ae`, as the last several polls this session).
  `activity_history_summary` shows only `ATTENDING_VISUAL` (52 count,
  104,000 ticks) and `EMITTING` (5 count, 500 ticks) since this boot —
  literally zero `SLEEPING` activities selected.
- Needs at that check: `stab=0.750 nov=0.954 conn=0.000 v=-0.132
  a=1.000` — **arousal pinned at its 1.000 ceiling, novelty at 0.954**,
  the same pathologically-saturated regime described in the dial-1
  live-verification report. 6.5h is past the top of the CMD-167 design
  doc's own stated 4-8h target cadence for a natural cycle.

Not diagnosing further here — this is the watch item, not a new
investigation — but flagging plainly: dial 1 (the novelty-term floor)
was verified to correctly let `ATTENDING_VISUAL` win a single
fresh-decision race; it does not touch `dream_pressure`'s own
accumulation/ceiling (Change 2/3 territory), so this may simply mean
pressure hasn't reached its threshold yet under real load — or it may
be the next dial. Per my own handoff, that call is Eve/Joe's, not
mine to make unprompted.

---

## Item 3 — em-hemisphere count drop (12,194 → 8,831)

**Verdict: honest decay, well-evidenced — not a leak.** One separate,
smaller hardening gap found along the way, unrelated to this drop's
cause; noting it since it's now on the record either way.

**Mechanism:** `hemisphere_atlas_sizes.em` and `/status`'s
`atlas_health.n_total_entries` are **the same underlying count** — both
are `sum(len(v) for v in guala.atlas.entries.values())`, the raw size
of the working atlas's entry dict (`hemisphere_cognition.py:588-590`,
`gualaloom_v6_living_atlas.py:617`), read via two different code paths.
This count is **not** filtered by entry strength — a separate stat,
`n_live_bindings`, does that filtering; `n_total_entries` does not.

The atlas prunes dead entries (`strength < FORGETTING_THRESHOLD =
0.02`, `gualaloom_v6_living_atlas.py:53`) only in a batch sweep,
`forget_below_threshold()` (`:455-488`), gated to run once every 200
ticks (`gualaloom_v5_engine.py:1827-1828` and two more matching call
sites). Between sweeps, already-dead entries sit uncounted-as-dead but
still present in the dict, inflating the raw count — so the *raw*
number is a step function even though the underlying strength decay
(`decay()`, `DECAY_LAMBDA=0.0001`/tick) is continuous and slow, exactly
as designed.

**The arithmetic closes this, not just the narrative:** `14701200 %
200 == 0` — your three samples (14701120, 14701158, 14701210) straddle
this exact sweep boundary. The two earlier samples are both pre-
boundary (same epoch as the prior sweep); the third is 10 ticks
*after* the boundary. One scheduled `forget_below_threshold()` call
landed in that exact gap — the drop is that one sweep firing, not
decay accelerating or a bug materializing in 14 seconds.

**Ruled out, with evidence:** a full-dict reset (`self.atlas.entries =
defaultdict(list)` only happens at boot/restore, both lock-guarded,
and would show a tick discontinuity — the tick sequence here is
smooth); a decay-rate spike (`decay_modulation` is clamped `≤ 1.0`, can
only slow decay, and has zero live callers anywhere outside its own
definition per its own hard-coded safety invariant); event-log
aliasing (each logged event gets a freshly-built `detail` dict, no
shared-reference mutation possible).

**Secondary, separate finding — real, but not the cause of this
drop:** `introspect()` (feeds `/status`'s `atlas_health`) and
`substrate_runner.py`'s 30s `_live_organ_update` thread both read
`guala.atlas.entries` with **no lock**, while the tick loop mutates the
same dict (including key deletion) under `self.lock`. Confirmed via
direct search — zero `with self.lock` in `introspect()`'s body. Worth
hardening at some point (a race here could in principle raise or skew
a read), but the magnitude and exact-200-tick timing of the observed
drop match the designed sweep too precisely to be race noise — this is
a "fix regardless," not the explanation.

**One open question I can't close from code alone:** whether
`CONVERSE_PHASED=1` is set on the live process — if it is, the
opt-in unlocked hemisphere-update path (`gualaloom_v5_engine.py:2140`,
explicitly commented "no lock") would apply too. That's a runtime env
var, not something visible in the repo; flagging rather than guessing.

---

## Item 4 — the parallel v7-engine session file

**Confirmed: nothing live depends on it.**

`get_or_create_session(session_id, engine=_guala)` (the only place the
real v5 engine touches the v7 session layer) passes `_guala` into
`V7Session.__init__` for exactly one purpose: `seed_vocab_from_engine(engine)`
(`v7_engine.py:36-52`) does a **one-time, read-only snapshot** of
`engine.vocab` at session-creation time to seed the v7 session's own
internal word pools. After that single read, `V7Session` runs entirely
on its own isolated `sys_` object — its own tick counter (confirmed
live: `tick: 1658` via `/v7/persistence`, vs. the real substrate's
tick in the tens of millions), its own sections/pools, its own
persisted file. No reference back to `_guala` exists anywhere else in
`v7_engine.py` (confirmed: zero occurrences of `_guala` in that file).

This matches and extends the existing `-160` finding that `/v7/converse`
receives zero production calls: the only live caller into this layer
is the frontend's `/v7/quiet` (the "sleep" button, per Change 4's own
commit note — already flagged there as "a mechanism mismatch,
deliberately not rewired"), and even that call is a closed loop within
the dead `V7Session` object. Deleting or ignoring the v7 session file
on disk would have zero effect on her real behavior, needs, or atlas —
confirmed, not assumed.

---

### Changelog
- v1 (2026-07-04, c1b): items 2-4 from GL-NOTE-VOID-RATIFICATION-NOTE-
  EVE-20260704-v1 closed out. Item 2: natural sleep still not observed
  under :461, numbers given. Item 3: em-hemisphere drop verified as
  honest decay (200-tick batch prune sweep), exact tick-modulo
  arithmetic confirmed, one separate unlocked-read hardening gap noted.
  Item 4: v7 session file confirmed inert relative to live cognition,
  one-time read-only vocab seed only. Item 1 (retention deploy cutover)
  still waiting on c1a's SHA.
