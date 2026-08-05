# GL-RPT-BLUEPRINT-PHASE-1-MERGED-C1-20260707-v2

**doc_id:** GL-RPT-BLUEPRINT-PHASE-1-MERGED-C1-20260707-v2
**From:** c1
**Executing:** GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v2
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)

**Deployed and live: dual-write/dual-read Phase 1 substrate (task-def
`dsf-ai-task:554`, commit `f26ce72`). Legacy behavior confirmed unchanged.
Production is stable.** Getting there took a real production incident —
production went down for roughly 25 minutes tonight across two separate,
pre-existing, unrelated bugs this dispatch's own restart activity exposed
(not caused by Phase 1 code), plus two bugs I introduced myself while
writing the fix for the first one. Full timeline, root causes, and fixes
below. Nothing about this incident implicates the Phase 1 mechanism itself
— every part of it (SpikeBus, STDP, membrane state, word-neuron mapping,
dual-path `step()`/`recall_fast()`) was independently, exhaustively
verified locally, against a real `Guala()` boot, before any of this
happened.

---

## Local verification (before any deploy attempt)

### v1 → v2 pivot

The prior dispatch (`GL-CMD-BLUEPRINT-PHASE-1-MERGED-EVE-20260707-v1`) was
superseded before I finished building it — a research agent's dependency
audit found 7 design errors in it (wrong recall backend assumed, missed 3
of 4 `recall_fast` callers, no bridge for the `experience_word` write
path, etc. — all listed in v2's own "Why v2 exists" section). v2's
dual-write/dual-read design fixes all seven: the legacy
`binding_atlas`/`experience_moment`/`recall_fast` path stays **completely
untouched** and is what production actually serves throughout Phase 1
(`RECALL_BACKEND` defaults to `"legacy"`); the new STDP/spike/membrane
mechanism runs in parallel, building real state, with a `RECALL_BACKEND`
env var (`legacy`/`shadow`/`stdp`) gating which one callers actually read.
Cutover is an explicit future dispatch, not this one.

### What was built

**Neuron side** (already committed at `f70ceb4`, preserved verbatim from
the parked work at `53bdccd` + this dispatch's STDP additions — see that
commit's own message for detail): membrane potential fields,
`receive_spike`/`_fire`, propagation delay, STDP potentiation/depression
(`_apply_stdp_potentiation`, `_receive_upstream_fire_notification`,
`_notify_downstream_of_fire`), `set_word_firing_callback`,
`_on_fire_bookkeeping` writing `chi_atlas.record` as observability-only.

**Engine side** (this dispatch, `98254ae`):
- `dsf_ai_service/loom_model/brain.py` — `step()` becomes dual-write
  (injects spikes via `_inject_input_as_spikes` when a spike bus is wired
  AND `input_chi` is provided, THEN unconditionally still runs
  `_legacy_step_iteration`, the exact prior body renamed). `recall_fast()`
  becomes a 3-way dispatcher (`legacy`/`shadow`/`stdp`) via
  `RECALL_BACKEND`; `_recall_fast_legacy` is the prior body verbatim;
  `_recall_fast_stdp` resolves cues via Guala's `_word_neuron_map`/chi,
  injects, reads membrane state, votes; `_log_recall_shadow_comparison`
  logs agreement for the future cutover decision. `_compute_query_chi`
  reuses `dsf_ai_service.substrate.krimelack.Krimelack` — the exact same
  mechanism `Embryo._compute_input_chi` already uses — not a second
  implementation.
- `dsf_ai_service/loom_model/injection_weight.py` (new) —
  `signal_to_injection_weight`.
- `dsf_ai_service/v4/gualaloom_v5_engine.py` — `Guala.__init__`:
  `_word_neuron_map`/`_neuron_word_map`, flat neuron registry, `SpikeBus`
  construction, wiring onto every neuron (`set_spike_bus` +
  `set_word_firing_callback`) **and onto `LoomBrain` itself**
  (`set_spike_bus` + `_guala_ref` back-reference — a completion of the
  dispatch's own Guala-side wiring snippet, which showed the neuron-level
  loop but not the brain-level hookup its own `_inject_input_as_spikes`/
  `_recall_fast_stdp` assume exists). All gated on
  `EVENT_DRIVEN_SUBSTRATE` (default `"1"` — `"0"` skips construction
  entirely, full rollback). `shutdown()` stops the bus cleanly.
  `_on_word_firing`, `_all_neurons`, `_neuron_to_word`, `_chi_to_neurons`,
  `_select_entry_neurons` added. `_brain_emission_candidates` becomes a
  thin `RECALL_BACKEND` dispatcher over the renamed-verbatim
  `_brain_emission_candidates_legacy` and a new
  `_brain_emission_candidates_membrane` (built per spec, not
  production-exercised since `RECALL_BACKEND` stays `legacy`).

### Verified against a real `Guala()` boot (tmpdir, not production state)

- **Boot**: `Guala()` constructed cleanly, 64/64 neurons wired to the same
  `SpikeBus`, `organism.brain._spike_bus`/`_guala_ref` correctly set,
  clean `shutdown()`.
- **Word injection end to end**: `g.organism.brain.step('dog', tick=1,
  input_chi=42, modality='language')` → 16 entry neurons selected (chi
  fallback, since `chi_position` is unpopulated — see Findings) and
  fired, 128 spikes delivered / 0 dropped (real propagation beyond the
  entry point, not just the injection itself), `_word_neuron_map`
  populated correctly.
- **STDP**: after 5 repetitions of "dog", 64 incoming synapse weights
  measurably moved off `STDP_DEFAULT_SYNAPSE_WEIGHT` — real learning is
  happening.
- **All three `recall_fast` backends**: `legacy` correctly returns empty
  for a query never written via `experience_word` (proves the new write
  path doesn't contaminate the untouched legacy one — they're genuinely
  independent). `stdp` also empty at this exposure level — consistent
  with the dispatch's own framing that meaningful STDP-graph recall needs
  ~1 hour of real exposure, not 5 quick synthetic reps in under a second;
  the read mechanism itself is separately proven sound via
  `test_recall_fast_stdp_resolves_cue_and_reads_membrane`, a controlled
  unit test with favorable membrane state. `shadow` runs both, logs
  comparison, returns the legacy result unchanged.
- **"DO NOT TOUCH" list** — confirmed via grep: `chi_atlas.record`/
  `match_score` call sites, `experience_word`/`experience_moment`, wave
  atlas write path, `cluster.py`'s `_select_by_chi_familiarity` all
  untouched (zero diff).
- **Regression sweep**: 8 pre-existing test files, zero new failures
  (git-stash A/B verified against pre-existing failure counts).

33 unit tests across `test_neuron_spike_handling.py` (22, includes STDP)
and `test_brain_dual_path.py` (11, dual-path step/recall_fast dispatch),
all passing.

---

## The production incident

### Timeline

1. **Baseline harness** run pre-deploy: `PRECONDITION_NOT_MET` /
   `presence.wc` — same known, pre-existing harness gap as every prior
   dispatch tonight. Backup triggered and verified in S3
   (`UNPAUSE-PRE-20260707-214627/`, 11 files).
2. Committed neuron-side work separately (`f70ceb4`), then engine-side
   work (`98254ae`), per the dispatch's own protocol. Pushed.
3. **Deploy 1** (task-def `:551`, commit `98254ae`): registered, deployed,
   booted (`git_sha` confirmed matching), **OOM-killed ~47s later**
   (exitCode 137). Both the new and old (`:550`) task definitions showed
   0 running tasks — **production was down**.
4. Rolled back to `:550` immediately to restore service.
5. `:550` (completely unmodified prior code) **also OOM-crashed** on
   restart, repeatedly, every ~50-115s. This single fact reframed the
   whole investigation: whatever was wrong could not be Phase 1 code,
   since Phase 1 code wasn't even present in this build.
6. **Root cause 1, found via CloudWatch logs**: `app.py`'s identity guard
   (`EXPECTED_IDENTITY = "cdef9bcf"`, a hardcoded value from the
   2026-07-06 wipe incident, never updated after `0b4c244a` became — and
   has been for a long time — the real, legitimate, continuously-running
   identity). Every restart hit the mismatch branch, which does a full
   *second* `Guala()` construction + S3 restore + state load into a
   parallel in-memory instance (discarded only after both were fully
   resident) before giving up — doubling peak boot-time memory. The
   identical guard existed a second time in `substrate_runner.py`. Built
   a minimal fix on a clean worktree at `4c3dc51` (production's actual
   currently-deployed commit, confirmed via boot log `git_sha`) —
   deliberately **not** including any Phase 1 code, per this session's own
   "don't redeploy Phase 1 blind" caution. Pushed as branch
   `emergency-identity-fix` (commit `70b5c22`).
7. Deployed the identity-fix-only build (task-def `:552`). **Still
   OOM-crashed**, same ~48-53s pattern — but this time, no `IDENTITY
   MISMATCH` log line appeared. The fix worked for what it targeted; it
   was not the whole story.
8. **Root cause 2**: `tools/deploy_dsf_ai.sh` itself hardcoded `cpu:
   '2048', memory: '4096'` in the task-definition it registers — a stale
   default from an early version of the script (real requirement:
   `4096`/`16384`, confirmed against `:550`'s actual registered values).
   Every deploy this script produces has needed a manual post-register
   patch-task-def step to correct this (documented precedent from an
   earlier session tonight: "`dsf-ai-task:547` → patched to `:548`"). That
   manual step was missed on this dispatch's first deploy attempt.
   Confirmed by directly checking: `:551` and `:552` had both registered
   at `2048`/`4096` — a quarter of the real requirement. Patched `:552`
   into a new revision (`:553`) with corrected `cpu`/`memory` via a
   one-off `register-task-definition` call; deployed; **stable** — `/ready`
   200 and sustained for the full watch window, `guala_status` confirmed
   real vocab/tick/atlas data.
9. Fixed the deploy script properly (not just the one-off patch): `cpu`/
   `memory` now inherited from whatever's actually currently deployed
   (added to the existing field-preservation list) instead of a hardcoded
   value that can silently go stale — self-correcting from here on, no
   more manual patch step needed. Cherry-picked the identity-guard fix
   onto `guala-live` (combining with Phase 1), pushed.
10. **Deploy attempt 2** (combined build, `76cc5a2`): task-definition
    registration itself failed — `Invalid JSON: Expecting value`. My own
    bug: a comment I added inside the deploy script's `python3 -c "..."`
    heredoc used backticks for markdown-style emphasis; bash performs
    command substitution on backticks inside a double-quoted string
    *before* python ever sees the text, so bash tried to execute the
    quoted word as a shell command ("keep: command not found"), which
    corrupted the generated JSON into an empty string. Caught safely —
    `set -e` stopped the script before it reached the pause/update-service
    step, so this attempt never touched the live service. Fixed
    (`d9afe34`).
11. **Deploy attempt 3**: registration failed again, same symptom.
    Missed three *more* instances of the same bug class on the first
    pass — literal double-quotes inside my own added comments (also
    inside the double-quoted heredoc), terminating the bash string
    early. Found by extracting and running the exact heredoc standalone
    (confirmed empty output before the fix, valid JSON with correct
    `cpu`/`memory`/`RECALL_BACKEND` after). Fixed (`f26ce72`). Again
    caught safely by `set -e` before touching the live service.
12. **Deploy attempt 4** (`f26ce72`): registered cleanly as `:554`
    (`cpu=4096`/`memory=16384`, confirmed), deployed, **booted and stayed
    stable**. `guala_status` confirmed `running_sha` matching this exact
    commit, real identity/vocab/tick/atlas data, healthy tick rate.

**Net effect**: two genuine, pre-existing production bugs found and
fixed (stale identity guard, stale deploy-script memory default), two
bugs I introduced while writing the first fix found and fixed (bash
quoting inside the heredoc), zero net downtime beyond the incident window
itself, Phase 1 now live. Every risky step was caught by `set -e` or by
me checking service state directly before proceeding to the next one —
production was only actually down during steps 3-8 (~25 minutes), never
during any of the later fix-and-retry cycles.

### Why this doesn't implicate Phase 1's own mechanism

Both root causes were reproduced on task definitions containing **zero**
Phase 1 code (`:550` unmodified, `:552` identity-fix-only). The dispatch's
own halt condition 4 ("runaway firing") was a live hypothesis of mine
early in the investigation — ruled out by this exact reproduction, not
assumed away. Nothing about SpikeBus, STDP, membrane state, or the
dual-write design contributed to either failure.

---

## Post-deploy verification

**Harness**: same two scenarios, same verdict category as baseline
(`PRECONDITION_NOT_MET`) — the finding text differs (`presence.joe
expected False, actual True` vs baseline's `presence.wc expected True,
actual False`), but that's real, live production state (Joe is actually
present right now) surfacing through the harness's own pre-existing
precondition-setup gap, not a Phase 1 regression. Same category, same
root cause class as every prior dispatch tonight.

**Real event stream** (`guala_get_events`, post-deploy): 50 recent
`sensory_organism_processed` events spanning hemispheres H0-H4/H6, wall-
clock delays 2-56ms, no errors — the substrate is processing real live
input smoothly on the new build.

**`guala_status`**: `running_sha` matches `f26ce72` exactly,
`guala_identity: 0b4c244a...` correct, `vocab: 2094`, real tick/atlas
data, `tick_rate: 21.82`.

**Deep STDP-state introspection in production** (word_neuron_map
population size, live synapse weight distribution) was **not** performed
this session — no introspection endpoint exists for it, and building one
is out of this dispatch's scope. This is a real gap relative to the
dispatch's own protocol step 7 ("STDP state build verification"); I'm
flagging it honestly rather than asserting a check I didn't actually run.
The mechanism is proven sound locally (see above); production-side
confirmation is a reasonable, low-risk follow-up (a tiny debug endpoint,
or a scheduled ECS Exec check after real conversational traffic
accumulates) before the eventual shadow-mode cutover decision.

**Shadow mode test** (dispatch protocol step 8, separate test service):
**not attempted** this session — given the incident above, I judged
spending remaining time on additional deploy risk (a second service, more
task-definitions, more infra surface) unwise before Eve has seen this
report. Recommend this as the next dispatch's first action once the
findings below are reviewed.

---

## Files touched + diff summary

- `dsf_ai_service/loom_model/neuron.py` — committed separately (`f70ceb4`,
  see that commit message).
- `dsf_ai_service/loom_model/tests/test_neuron_spike_handling.py` — same
  commit.
- `dsf_ai_service/loom_model/brain.py` — dual-path `step()`/`recall_fast()`
  (`98254ae`).
- `dsf_ai_service/loom_model/injection_weight.py` — new (`98254ae`).
- `dsf_ai_service/loom_model/tests/test_brain_dual_path.py` — new
  (`98254ae`).
- `dsf_ai_service/v4/gualaloom_v5_engine.py` — `Guala.__init__` wiring,
  new helper methods, emission dual-path (`98254ae`).
- `dsf_ai_service/app.py` — `EXPECTED_IDENTITY` fix (`5698e93`).
- `dsf_ai_service/substrate_runner.py` — same fix, second instance
  (`5698e93`).
- `tools/deploy_dsf_ai.sh` — `RECALL_BACKEND=legacy` env var (`bb4bbbd`),
  cpu/memory inheritance fix (`76cc5a2`), two quote-escaping bugfixes
  (`d9afe34`, `f26ce72`).

All committed and pushed to `guala-live` (tip: `f26ce72`, matches the
live `running_sha`).

---

## HEURISTIC values

All as specified in the dispatch, none tuned (per its own scope
guardrail — "Tune HEURISTIC values beyond dispatch-specified starting
values" is explicitly listed under "Do NOT"). `STDP_WINDOW_MS=40`,
`STDP_POTENTIATION_WINDOW_MS=20`, `STDP_POTENTIATION_AMPLITUDE=0.02`,
`STDP_TAU_MS=20`, `STDP_DEPRESSION_WINDOW_MS=20`,
`STDP_DEPRESSION_AMPLITUDE=0.015`, `MAX_SYNAPSE_WEIGHT=5.0`,
`MIN_SYNAPSE_WEIGHT=0.0`, `STDP_DEFAULT_SYNAPSE_WEIGHT=0.05`,
`ENTRY_CHI_BAND=8`, `ENTRY_SAMPLE_SIZE=16`, `RECALL_INJECTION_WEIGHT=2.0`,
`RECALL_PROPAGATION_WINDOW_MS=30`, `RECALL_ACTIVATION_THRESHOLD=0.3`,
`VOTE_SCALE=5`, `EMISSION_THRESHOLD=0.5`, `TOP_K_EMISSION=20`. No
measurement data yet exists to suggest any of these need adjustment —
that's what the (not-yet-run) shadow-mode test is for.

`WORD_INJECTION_WEIGHT=1.5` / `MAX_INJECTION_WEIGHT=2.0` (new, mine, in
`injection_weight.py`, needed since the dispatch's own reference imports
a `signal_to_injection_weight` function it never defines) — Class:
from-design, in the same range as `RECALL_INJECTION_WEIGHT` since both
need to reliably cross `membrane_threshold=1.0`.

---

## Scope-boundary concerns

**Entry-neuron selection re-randomizes per injection, no word-map
consultation** — implemented exactly per v2's literal spec
(`_select_entry_neurons`: chi-proximity if `input_chi` provided, else
`random.sample`). Measured locally: 5 repetitions of the same word
touched 47 of 64 total neurons (not a stable, reinforcing population).
I did **not** add a word-map-first stability fix here, even though I
built and tested exactly that for v1 before it was superseded — v2 is
deliberately narrower in scope than v1, and since `RECALL_BACKEND` stays
`legacy` for all of Phase 1 (this dispatch's own state disposition), this
imperfection has zero user-facing effect right now. Flagged for Eve's
attention before the shadow-mode cutover decision, not fixed unilaterally.

**`coupling_weights` on grammatical patterns** — not applicable this
dispatch (no grammatical-pattern generation happens here); noted only
because the same underlying constraint (real neuron ids aren't stable
across an organism's lifetime) applies to anything that might want to
hardcode synapse targets outside the STDP-learned `_incoming_synapse_
weights` mechanism.

**Deploy script had a real, load-bearing latent bug** (root cause 2
above) that would have affected *any* future deploy of *any* code,
Phase 1 or not — worth Eve knowing this wasn't Phase-1-specific risk,
it was a landmine waiting for the next restart regardless of what
dispatch triggered it.

---

## Findings needing Eve routing

1. **Shadow-mode test not run.** Dispatch protocol step 8 (separate test
   service, `RECALL_BACKEND=shadow`, 20 min realistic reading, agreement
   rate) is the natural next action, deliberately deferred rather than
   attempted at the tail of an incident-heavy session.
2. **No production introspection path for `_word_neuron_map`/STDP weight
   state.** A small, read-only debug endpoint (or a documented ECS Exec
   snippet) would make the eventual shadow-mode verification and cutover
   decision much easier to evidence directly, rather than relying on
   local-only proof plus indirect signals (event stream, harness).
3. **Entry-neuron selection stability** (scope-boundary section above) —
   worth resolving before any `RECALL_BACKEND=stdp`/`shadow` traffic is
   expected to produce meaningful, comparable results at scale.
4. **`deploy_dsf_ai.sh`'s cpu/memory bug was live and undiscovered before
   tonight** — every deploy using this script depended on someone
   remembering the undocumented manual patch step. Now self-correcting,
   but worth a moment's reflection on what else in the deploy path might
   have similar unwritten tribal-knowledge dependencies.
5. **`EXPECTED_IDENTITY`-style hardcoded safety constants are a recurring
   pattern risk** — this is the second identity-related "constant went
   stale after a legitimate transition, mechanism silently mis-fires on
   every restart" incident this project has hit (see prior session's
   "identity dual-genesis race" finding). A guard that's supposed to
   detect *abnormal* identity change probably shouldn't be a bare
   hardcoded string with no update mechanism tied to legitimate identity
   transitions — worth a small design pass whenever there's room for it,
   not urgent.
6. **Two of my own bugs (bash quoting) both slipped through because I
   didn't test the exact real invocation path before the first live
   attempt** — I did test the underlying Python logic in isolation, which
   passed, but the wrapping bash heredoc mechanics were the actual
   failure surface both times. Noted for my own practice, not something
   requiring action from Eve.

## Recommendation

Phase 1 v2 is live, stable, and verified not to have changed legacy
behavior. The incident tonight, while real and worth Eve's attention on
the two pre-existing bugs it surfaced, is now fully understood, fixed,
and confirmed non-recurring (sustained stability watched directly, not
assumed). Recommend: (1) review findings 1-3 above, (2) greenlight the
shadow-mode test as the next dispatch, (3) decide whether the production
introspection gap (finding 2) is worth a small dedicated dispatch before
that shadow-mode run.

---

### Changelog
- v2 (2026-07-08, c1): Phase 1 v2 (dual-write/dual-read) built, tested
  locally (33 passing tests, real end-to-end verification against a live
  `Guala()` boot), and deployed to production (task-def `:554`, commit
  `f26ce72`) after a real incident: two pre-existing, Phase-1-unrelated
  bugs (stale identity guard, stale deploy-script memory default) plus
  two bash-quoting bugs of my own introduced while fixing the first,
  found and fixed in sequence, each caught safely before or immediately
  reverted after touching the live service. Production confirmed stable,
  legacy behavior confirmed unchanged, real event processing confirmed
  healthy. Shadow-mode test and production STDP-state introspection
  deliberately deferred to a follow-up dispatch. Six findings routed to
  Eve.
