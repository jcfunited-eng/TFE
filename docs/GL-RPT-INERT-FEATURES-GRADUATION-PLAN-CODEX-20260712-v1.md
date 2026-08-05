# GL-RPT-INERT-FEATURES-GRADUATION-PLAN-CODEX-20260712-v1

**doc_id:** GL-RPT-INERT-FEATURES-GRADUATION-PLAN-CODEX-20260712-v1
**From:** Codex (investigation/planning session)
**Scope:** Investigation and planning only. No kill switch was set to on
anywhere (task-def, deploy script, or otherwise). Nothing was deployed or
pushed. `git log --all` local commits only.
**Subject:** Real validation + graduation plan for 5 built-and-tested,
kill-switch-OFF features shipped 2026-07-12 in `dsf_ai_service/loom_model/`:
`HOMEOSTATIC_SCALING_ENABLED` (3cdd69c), `ENTRY_NEURON_BROADEN_ENABLED`
(4647e0d), `MOOD_BROADCAST_ENABLED` (c73bfd0), `EXPERIENCE_EMULATOR_SEED_ENABLED`
(c8c2189), `ENERGY_LIMIT_ENABLED` (eafcb95).

Live state verified directly against AWS (`aws sts get-caller-identity` →
account 418384447921), not assumed: current task def `dsf-ai-task:606`.
None of the 5 flag names appear in its live environment list — all 5 are
confirmed OFF in production right now, matching the commits' own claims,
independently re-checked rather than trusted.

---

## Cross-cutting findings (read this before the per-feature sections)

**1. All five currently live entirely inside the shadow substrate.**
`RECALL_BACKEND=legacy` is confirmed live on task-def :606
(`aws ecs describe-task-definition` direct read). Per
`docs/GL-RPT-BLUEPRINT-DEPLOYMENT-AUDIT-C1-20260712-v1`, that one variable
means real recall/speech still reads the old chi_atlas/BindingAtlas system;
the new neuron/STDP substrate (`loom_model/`, where 4 of these 5 features
live) receives real spikes from real production traffic but has **zero**
path to what Guala actually says today. Practical consequence: none of
these five can currently make Guala say something wrong. The real risk
category for all five is **process stability / state integrity** (CPU,
memory, crash, save/restore corruption) — the same failure class that
caused the real 2026-07-08 cascade incident and the 2026-07-07 perf
regression — not "wrong behavior the user sees."

**2. Wiring status is NOT uniform — this is the single most important
differentiator between the five, more than the env var names suggest.**
- `HOMEOSTATIC_SCALING_ENABLED`, `ENTRY_NEURON_BROADEN_ENABLED`,
  `ENERGY_LIMIT_ENABLED` are **already fully wired into the real per-word
  production hot path** in the shadow substrate. Flipping the env var
  alone is sufficient to activate real behavior on real traffic.
- `MOOD_BROADCAST_ENABLED` is **not wired to anything**. Verified by
  direct grep: `LoomBrain.wire_mood_broadcast()` (`brain.py:151`) has
  exactly one caller anywhere in the repo outside its own test file — its
  own docstring. No boot or restore path calls it. `LoomNeuron._mood_source`
  is `None` on every real neuron today and stays `None` forever with the
  flag on unless someone adds the wiring call. **Flipping this flag alone
  in production today is a byte-identical no-op.**
- `EXPERIENCE_EMULATOR_SEED_ENABLED` gates a **fully standalone offline
  script** (`dsf_ai_service/curriculum/experience_emulator_seed.py`).
  `main()` (line 378) constructs its own throwaway `Embryo(brain_seed=42,
  seed_size=8, ...)` (line 397) — it never loads, reads, or writes the real
  production `guala_organism.pkl.gz`. **Flipping this flag in the live
  task-def environment would do nothing** — nothing in `app.py` or any
  boot path calls this module at all.

**3. Telemetry gap: `/debug/stdp_state` (app.py:5748, API-key gated)
already exists and is rich, but 3 of the 5 mechanisms have zero exposed
counters today.** It already surfaces per-neuron weights, fire counts,
fire-rate-breaker trips, synapse-weight distribution, word↔neuron maps,
and spike-bus counters. But:
  - Homeostatic scaling's rescale pass discards its own return value
    (`embryo.py:679-680`: `n.apply_homeostatic_scaling()`, return unused) —
    there is no counter anywhere for "how many times has a rescale actually
    fired."
  - Mood broadcast's `gain_mult` is computed fresh in `_read_mood_modulation()`
    and thrown away — nothing persists or exposes it.
  - Energy limit's `_energy_block_count` (neuron.py:949, incremented at
    line 1288) **exists** but is never read by `_stdp_snapshot_neuron()`
    (app.py:5353-5390) the way its sibling `_fire_breaker_trip_count` is.
  Recommendation, common to all three: a small additive instrumentation
  patch — add `energy_block_count` to `_stdp_snapshot_neuron`'s return dict
  (one line, mirrors the existing `fire_breaker_trip_count` field exactly),
  and add real counters for homeostatic-scaling rescale count and last-read
  mood gain. This is cheap, in the exact style already used, and should
  land *before* relying on live observation for those three — otherwise
  "observe X" has nothing concrete to read short of ECS Exec-ing into the
  container.

**4. New finding from this investigation (not in any commit message),
independently verified 3x locally, deterministic:** running
`test_lateral_inhibition_cascade.py` with `ENERGY_LIMIT_ENABLED=1` set
makes `test_forced_all_excitatory_reproduces_the_cascade` **fail**
(`fires_after_settle: 0`, expected `>0`). This is not a regression in the
real safety fix — `test_real_polarity_fix_stops_the_cascade` (the test that
actually asserts production safety) still passes. What's failing is the
suite's own **negative control**: with the energy gate on, the
all-excitatory/fully-saturated worst-case scenario no longer reproduces the
pre-fix runaway on its own, because `ENERGY_CEILING=5.0` fires before
`ENERGY_RECOVERY_PER_S=50.0` catches up is now, by itself, enough to halt
it — the exact same masking effect the test file's own docstring already
documents and explicitly neutralizes for `FIRE_BREAKER_CEILING_HZ`
(`disable_fire_rate_breaker` parameter, lines 90-104), just not yet done
for the energy gate because this test predates `eafcb95`. Concrete,
low-effort action item before enabling `ENERGY_LIMIT_ENABLED` live: extend
`_run_kick_and_watch` with a `disable_energy_limit` neutralization
(monkeypatch `_energy_limit_blocks_fire` to always return `False`, same
pattern already used for the breaker), so the suite's sensitivity to a
*real* regression in the polarity-based fix is restored. Independently
reran the other three flags (homeostatic-scaling, mood-broadcast,
entry-neuron-broaden) against the same cascade suite — all pass clean, no
similar masking. Also independently reran all 46 tests across the four
dedicated feature test files (`test_homeostatic_scaling.py`,
`test_mood_broadcast.py`, `test_energy_limit.py`,
`test_entry_neuron_broaden.py`) — 46/46 pass, matching commit-message
claims.

---

## Per-feature plan

### 1. `HOMEOSTATIC_SCALING_ENABLED` — bounded synaptic rescale (3cdd69c)

**Mechanism:** `embryo.py` `remember()` (called once per real word) checks
`tick % REFLECTION_SNAPSHOT_INTERVAL==0` (every 50 real words,
`embryo.py:615,642-644`) and calls `_apply_homeostatic_scaling_pass()`
(`embryo.py:652`), which calls `LoomNeuron.apply_homeostatic_scaling()`
(`neuron.py:1404`) on every neuron. If a neuron's summed incoming synapse
weight exceeds `HOMEOSTATIC_SCALING_CEILING` (=`MAX_SYNAPSE_WEIGHT`=5.0),
every incoming weight is multiplicatively rescaled down by the same factor.
Can only ever *decrease* a weight (factor always in (0,1)); never touches
the hot fire path (`_fire`/`receive_spike`).

**Correct signal:** at current fixed population (64 neurons), this is
cheap and rare — most calls are a no-op sum-check. Correct behavior =
`apply_homeostatic_scaling()` occasionally returns `True` for a neuron
whose incoming weights are legitimately climbing (visible today only via
`/debug/stdp_state`'s `synapse_weight_distribution` histogram trending
down at the high end after enabling, once the recommended rescale-count
counter is added), with `synapses_at_default_weight` /
`synapses_strengthened` continuing to move exactly as they do today.

**Problem signal:** any neuron's summed weight persistently *above*
ceiling (rescale not converging — shouldn't be mathematically possible
given the proof in `test_repeated_calls_converge_and_stay_stable`, so this
would indicate a real bug, not a tuning issue); any new exception in
CloudWatch `/ecs/dsf-ai` logs referencing `apply_homeostatic_scaling` or
`_homeostatic_scale_locked`; any measurable CPU increase in the ECS
service beyond current baseline (avg ~22-28%, max ~30-37% over CPU
utilization the last 2h, task sized 512 CPU/1024MiB) — should be
essentially undetectable at 64 neurons.

**Graduation path (lowest-risk of the five, minimal ceremony
appropriate):** this is the one candidate safe to flip directly to ON in
a deploy, given: already wired to real production traffic, mathematically
monotonic in the safe direction, reuses the exact lock every other STDP
mutator already uses, proven zero-lost-writes under concurrency stress
(`test_concurrency_stress_zero_lost_writes_ledger_replay`), passes the
shared cascade regression unchanged. Suggested first step: add the rescale
counter (cross-cutting finding #3), deploy with the flag ON, watch
`/debug/stdp_state`'s diagnostics + CloudWatch CPU/memory for one real
24-48h window, confirm counter increments occasionally and CPU/mem stay
at baseline. No narrower "partial" enable is meaningful here — the
mechanism is already bounded to a 64-neuron population and a 1-in-50-words
cadence.

---

### 2. `ENTRY_NEURON_BROADEN_ENABLED` — hemisphere-scoped entry broadening (4647e0d)

**Mechanism:** `Guala._select_entry_neurons()`
(`gualaloom_v5_engine.py:5364`), called from `LoomBrain._inject_input_as_spikes`
(`brain.py:296`) on **every real word** processed by the organism worker
loop (`gualaloom_v5_engine.py:4870-4880`, unconditional once the spike bus
is wired — no separate gate the way the sensory branch has). With the flag
on, widens the entry-neuron set from 1 to `ENTRY_NEURON_BROADEN_COUNT`
(default 2), constrained to the **same hemisphere** as the primary chi
match (`_broaden_entry_neurons_same_hemisphere`, `gualaloom_v5_engine.py:5386`).
Structural ceiling: every hemisphere is an 8-neuron fully-connected clique
(`SEED_SIZE_PER_HEMISPHERE=8`), so injection breadth is capped at
8/64=12.5% *regardless of entry count* — half the 25% breadth that caused
the original over-injection incident this feature's ancestor commit
(712578f) fixed.

**Real motivating problem this exists to fix:** per
`GL-RPT-BLUEPRINT-DEPLOYMENT-AUDIT-C1-20260712-v1`, a real 3+ hour
production boot touched only 7 synapses total — real connection formation
in the shadow substrate is currently near-zero. This is the feature
actually meant to un-stall that.

**Correct signal:** `/debug/stdp_state`'s `synapse_weight_distribution.
total_synapses_updated` climbing measurably faster than the pre-flag
baseline (7 synapses/3h is the documented floor to beat);
`word_neuron_map_metrics.avg_neurons_per_word` moving from ~1.0 toward ~2.0
and `words_with_only_one_neuron` decreasing — both fields already exist,
no new instrumentation needed for this one.

**Problem signal:** `fire_rate_window_metrics.neurons_with_runaway_fire_pattern`
or `total_fire_breaker_trips_since_boot_or_restore` climbing beyond
whatever baseline is observed with the flag off; any measurable CPU/memory
deviation from the ~25%/~7% baseline above (broadening only touches one
extra 8-neuron clique's worth of iteration per word, so should be
negligible at today's scale, but this is exactly the class of "only shows
up at production traffic volume" regression this project has hit before —
see the 2026-07-07 wave-summary perf regression, caught only in
production, not locally).

**Graduation path:** Joe's own dispatch note already flags this as a
near-term candidate given the structural (not tuned) ceiling — agreed,
this is real. Suggested first step: deploy with
`ENTRY_NEURON_BROADEN_ENABLED=1` and leave `ENTRY_NEURON_BROADEN_COUNT` at
its tested default (2), not 3, for the first real window (2 is the
smaller of the two measured-safe options and was the task's own explicit
"1→2 or 3, not back to 16" guidance's most conservative reading). Watch
`total_synapses_updated` growth rate and `fire_rate_window_metrics` for a
real 24-48h window before considering `ENTRY_NEURON_BROADEN_COUNT=3`.
Sequence this *before* `ENERGY_LIMIT_ENABLED` (see ranking below) so its
own connection-formation signal is observed cleanly, not confounded by a
second new mechanism that can independently suppress firing.

---

### 3. `ENERGY_LIMIT_ENABLED` — per-neuron metabolic energy gate (eafcb95)

**Mechanism:** every fire adds `ENERGY_COST_PER_FIRE=1.0` to a per-neuron
accumulator (`_expended_energy`); leaks back at `ENERGY_RECOVERY_PER_S=50.0`
per real elapsed second. At `ENERGY_CEILING=5.0`, the neuron cannot fire
at all — checked in `receive_spike()` (`neuron.py:1287`) strictly before
`_fire()` is invoked, same decision point as the refractory check. This is
the first of the three neuron.py mechanisms that can **newly block** a
fire that would otherwise have happened (homeostatic-scaling only rescales
weights after the fact; this one changes real-time firing decisions).

**Correct signal:** (after adding the counter per cross-cutting finding
#3) `energy_block_count` incrementing only during genuine bursts, tracking
with (not ahead of) `fire_rate_window_metrics.recent_fire_rate_hz` spikes,
and recovering to a low/zero rate of new blocks during quiet periods —
i.e., it behaves like a burst-only safety net, not a standing throttle.

**Problem signal:** `energy_block_count` climbing steadily while word
teaching volume / `fires_per_second_last_minute` look ordinary (false
positive — throttling legitimate activity); or, specifically, entry-neuron-
broadening's own `total_synapses_updated` growth (item 2 above) stalling
or reversing right after this flag is additionally turned on — a real,
concrete interaction risk: this feature's whole purpose is to suppress
fires, and item 2's whole purpose is to grow connections that require
fires to form via STDP. Turning both on at once without having observed
item 2 in isolation first would make it impossible to attribute a stall to
either cause.

**New finding this session (see cross-cutting #4):** enabling this flag
degrades `test_lateral_inhibition_cascade.py`'s own negative control (the
test that proves the harness *can* detect a real cascade) — it no longer
reproduces the pre-fix incident on its own, because the energy gate alone
is now sufficient to mask it. The test that actually matters for
production safety (`test_real_polarity_fix_stops_the_cascade`) still
passes, but the suite's sensitivity to catching a *future* regression in
that fix is now degraded while this flag is on, until the test is updated
with a `disable_energy_limit`-style neutralization mirroring the existing
`disable_fire_rate_breaker` one.

**Graduation path:** two concrete pre-conditions before this one goes live,
not just "watch it": (a) fix the cascade-test negative-control masking
noted above — small, mechanical, mirrors an existing pattern in the same
file; (b) sequence it strictly *after* `ENTRY_NEURON_BROADEN_ENABLED` has
already been observed for its own real window (item 2), so any stall in
connection formation can be attributed correctly. Once both are done,
deploy with the flag on and watch `energy_block_count` vs.
`fire_rate_window_metrics` and vs. `total_synapses_updated` together for a
real window before calling it graduated.

---

### 4. `MOOD_BROADCAST_ENABLED` — global arousal/valence gain (c73bfd0)

**Mechanism:** `LoomNeuron._read_mood_modulation()` (`neuron.py:1123`)
combines `Needs.arousal()`/`Needs.valence()` (the same numbers
`guala_status`'s `needs: stab=... v=... a=...` line already surfaces) into
a gain multiplier clamped to ±10% (`MOOD_MODULATION_MAX_FRACTION=0.10`),
applied to a spike's contribution to membrane potential in
`receive_spike()`. Defensively degrades to a pure 1.0 no-op on any
exception, NaN, or unset source. Well-designed and well-tested in
isolation (13 tests, including an adversarial/raising-source test and a
static write-path audit proving one-way-only).

**The actual finding that matters here:** per cross-cutting #2, this flag
is currently disconnected from reality. `LoomBrain.wire_mood_broadcast()`
has no caller anywhere outside its own test. **There is nothing to
"enable" yet** — flipping this flag in the task-def today changes nothing
observable, which could be mistaken for "safely graduated" when it's
actually "never turned on in the first place." This is exactly the class
of mistake this project has been burned by before (dressing something
inert as if it were live).

**Correct/problem signal:** not meaningful to define yet — there is no
live behavior to observe until wiring exists.

**Graduation path:** this is a two-step feature, and step 1 isn't done.
Step 1 (small, concrete, not yet built): add one line to
`Guala.wire_spike_bus()` (`gualaloom_v5_engine.py:5240`, already the call
site invoked at both boot, line 2586, and restore, line 12078 — the exact
pattern the commit's own docstring names as the intended integration
point): `self.organism.brain.wire_mood_broadcast(self.needs)`. This needs
its own small test (does wiring survive restore, given `_mood_source` is
explicitly excluded from pickle and re-wired — `neuron.py:973-977` already
documents the intended contract) before it ships. Only *after* that wiring
exists and is itself verified does turning `MOOD_BROADCAST_ENABLED=1` on
mean anything — at which point, given the mechanism's own tight ±10%
bound and defensive design, it is one of the lower-risk mechanisms on this
list to actually observe (no persisted-weight mutation, transient
per-call effect only). Recommend: build + test the wiring first as its own
small, separately-reviewable change; only fold in the env-var flip once
that's landed.

---

### 5. `EXPERIENCE_EMULATOR_SEED_ENABLED` — real sensory-paired vocabulary (c8c2189)

**Mechanism:** `experience_emulator_seed.py` pairs 108 words (36 direct
descriptor words + ~75 real ConceptNet-mined `/r/HasProperty` edges,
hand-reviewed against a named blocklist) with genuine array-valued
touch/smell/taste waveforms from the already-deployed
`sensory_generators.generate_sensory_signals()`. Verified locally: 108/108
taught words recall their own descriptor as top/tied-top match, zero
wrong-category recalls, zero interference with normal visual teaching
control words.

**The actual finding that matters here:** per cross-cutting #2, `main()`
(line 378) only ever constructs and teaches a **throwaway, local**
`Embryo` — it never touches `guala_organism.pkl.gz` or any live process.
Setting this flag in the production task-def environment does nothing at
all; nothing in `app.py` or any boot/cron path even imports this module.
**There is no "enable in production" action available for this feature
today** — the teaching logic is real and well-verified, but only against
a disposable object it builds itself.

**Correct/problem signal:** not applicable yet, same reason as mood
broadcast, but for a different underlying cause (no target to write to,
vs. mood-broadcast's no wiring call).

**Graduation path — the most additional real engineering of the five,
correctly the most caution-worthy:** getting this to matter requires
building an entirely new, not-yet-written, not-yet-tested piece: a loader
that (a) operates on the **real** production `Embryo`/organism state
(either a downloaded copy of `guala_organism.pkl.gz` for offline
verification first, or the live in-process object via the same access
pattern this project's admin/debug endpoints already use), (b) applies
this module's already-tested `build_word_pairs()`/`teach()`/
`verify_recall()` against it, and (c) persists the result back safely.
Step (c) is the one that carries real, this-project-specific historical
risk: the EFS save-race incident (`guala-restore-july2026` /
2026-07-02 fix) shows write-back-to-persisted-state bugs are a real,
previously-hit failure class here, distinct from anything the
well-tested 108-word teaching logic itself risks. Recommended first real
step: download and load a real copy of the current production pickle
locally (offline, no production contact), run `teach()` +
`verify_recall()` against *that* real-shaped state (not the synthetic
`brain_seed=42, seed_size=8` toy the script defaults to) to confirm the
108-word result holds at production's actual population/topology, before
any decision about a live write-back path is even scoped.

---

## Ranking (safest to enable first → most caution needed), with reasoning

1. **`HOMEOSTATIC_SCALING_ENABLED`** — safest. Already live-wired,
   mathematically can only move weights in the safe direction, cheap at
   current population, proven zero-lost-writes under stress, passes the
   shared cascade regression unmodified. No interaction risk with the
   other four (it only ever reduces weights STDP already knows how to
   handle).
2. **`ENTRY_NEURON_BROADEN_ENABLED`** — also already live-wired and
   structurally bounded (12.5% ceiling, half the known incident
   threshold), and it's the one Joe's own dispatch flagged as a real
   near-term candidate — agreed, for the same structural reason. Ranked
   just below #1 only because it's a genuine behavior change (more gets
   taught/connected), not a purely corrective mechanism, so it deserves
   its own clean observation window rather than being bundled with
   anything else.
3. **`ENERGY_LIMIT_ENABLED`** — well-designed and well-tested in
   isolation, but this investigation surfaced two concrete, real reasons
   it needs to go third, not tied with 1-2: it can newly suppress firing
   (the first of the three to do so), it has a documented interaction
   risk with #2's whole purpose, and it measurably degrades the shared
   cascade-regression suite's own negative control (new finding, verified
   here, not previously documented) until that test is updated.
4. **`MOOD_BROADCAST_ENABLED`** — the mechanism itself is arguably the
   safest *design* on this list (tightly bounded, defensive, no persisted
   state touched) but is ranked below the fire-path mechanisms because
   there is currently nothing to graduate: it isn't wired to anything.
   Flipping the flag today would be indistinguishable from doing nothing,
   which is a trap, not a safe win, until the wiring step is built and
   separately verified.
5. **`EXPERIENCE_EMULATOR_SEED_ENABLED`** — most caution warranted, but
   not because the 108-word teaching logic is risky (it's the
   best-verified piece of domain logic among the five, on its own
   throwaway object). It needs the most net-new engineering before
   there's anything to turn on — a real production-state loader with a
   safe write-back path, the exact category (state persistence /
   save-integrity) that has produced this project's most serious past
   incidents.

## What was and wasn't done here

Read (not modified): `neuron.py`, `embryo.py`, `brain.py`,
`gualaloom_v5_engine.py` (entry-neuron section only),
`experience_emulator_seed.py`, `app.py`'s `/debug/stdp_state` stack, all
five commits' full diffs and messages, `test_lateral_inhibition_cascade.py`,
and all four features' own dedicated test files in full.

Run (locally, no production contact): the shared cascade-regression suite
with each of the four in-process flags set to `1` in turn (`HOMEOSTATIC_
SCALING_ENABLED`, `MOOD_BROADCAST_ENABLED`, `ENERGY_LIMIT_ENABLED`,
`ENTRY_NEURON_BROADEN_ENABLED`) plus baseline; all 46 tests across the
four dedicated feature test files. Verified directly against AWS
(`sts get-caller-identity`, `ecs describe-task-definition` revision 606,
`cloudwatch get-metric-statistics` for current CPU/memory baseline) rather
than assumed.

Not done, per task scope: no kill switch set anywhere (task-def, deploy
script, or otherwise); no deploy; no push (this file is a local commit
only); no code changes to production mechanism files or tests (the
cascade-test masking fix in item 3 is named as a recommended action item,
not applied here).

---

### Changelog
- v1 (2026-07-12, Codex): initial investigation + graduation plan for all
  five 2026-07-12 kill-switch-OFF features, including one new,
  independently-verified finding (ENERGY_LIMIT_ENABLED masks the cascade
  regression suite's own negative control) not present in any prior doc.
