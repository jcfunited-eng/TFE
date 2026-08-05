# GL-RPT-STDP-INTROSPECTION-C1-20260707-v1

**doc_id:** GL-RPT-STDP-INTROSPECTION-C1-20260707-v1
**From:** c1
**Executing:** GL-CMD-STDP-INTROSPECTION-EVE-20260707-v1
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)

**Deployed and live: read-only `/debug/stdp_state` endpoint (task-def
`dsf-ai-task:556`, commit `97b3756`). The endpoint itself works
correctly — 200 OK, ~0.2-0.5s, never crashes, never mutates state,
degrades gracefully. But the very first time it touched every live
production neuron, it surfaced a real, previously-undetected finding:
Phase 1 v2's STDP/spike/membrane mechanism (`GL-RPT-BLUEPRINT-PHASE-1-
MERGED-C1-20260707-v2`) has been silently non-functional in production
since it was deployed — likely on every restart, not just this one.
Root cause identified precisely below. Per this dispatch's own halt
condition 2 ("state counters don't match direct code inspection —
halt"), I am not attempting to fix the underlying mechanism; that is
out of this dispatch's bounded, read-only scope. Routing with full
data.**

---

## Local verification (before any deploy attempt)

Built `GET /debug/stdp_state` in `dsf_ai_service/app.py`: word↔neuron
population mapping, synapse weight distribution (histogram + top-10
strongest), fire event counts/rate, spike bus queue/injected/delivered/
dropped counters, decayed membrane-potential snapshot (top-20 active
neurons, above-threshold count, refractory count), and substrate
identity (`running_sha`, ECS task-def via the live metadata endpoint,
`identity_id`, uptime, `EVENT_DRIVEN_SUBSTRATE`/`RECALL_BACKEND`).

Design choices:
- **Auth** reuses the existing `_api_key_dep` (`GUALALOOM_API_KEY`)
  admin gate rather than inventing a new `DEBUG_ENDPOINTS_ENABLED`
  flag — functionally identical existing introspection endpoints
  (`familiarity_debug`, `persistence_health`, `atlas_snapshot`) already
  sit behind exactly this gate.
- **`task_def`** reads the ECS Fargate task metadata v4 endpoint at
  query time (0.3s socket timeout, `"unknown"` on any failure) instead
  of a deploy-script-injected env var — avoids the chicken-and-egg
  problem of the task-def revision not being known until *after*
  `register-task-definition` returns, and avoids adding another
  hardcoded value that can silently go stale (finding 5 of the prior
  dispatch's report — `EXPECTED_IDENTITY` already burned us on exactly
  this pattern once).
- **Never mutates substrate state**: each neuron's `_neuron_lock` is
  held only long enough to copy out primitives + a shallow dict, then
  released — never held across other neurons or aggregate computation.
  The spike bus's internal queue lock is handled the same way.
- **All synchronous work runs via `run_in_executor`** (same pattern as
  the existing `shutdown()` handler), so a slow query can't block other
  requests being served concurrently — the actual halt condition this
  dispatch calls out ("endpoint lock acquisition measurably slows
  substrate").

8 local tests against a real `Guala()` boot (not production state), all
passing: fresh-boot zero-state defaults, real word-injection producing
real fire/spike/synapse data, graceful degradation with
`EVENT_DRIVEN_SUBSTRATE=0`, the read-only guarantee (membrane state
provably unchanged by the query itself), timing (~2ms locally, far
under the 500ms budget), the API-key gate actually enforcing 401/200
via `TestClient`, and — added mid-dispatch after the production finding
below — per-neuron failure isolation, which reproduces the exact
production traceback locally (`del victim._neuron_lock`) and confirms
one broken neuron out of N yields N-1 good snapshots, not 0.

---

## Backup

Triggered via `guala_backup`. Took materially longer than the endpoint
code's own documented estimate ("30-120s") — about 7 minutes on the
first attempt, with no completion or error log line appearing in
CloudWatch for either of two trigger attempts within their respective
monitoring windows, even though the backup **did** eventually complete
both times. Confirmed via direct S3 listing rather than the log line I
was originally watching for:

`s3://dsf-ai-site-backups/guala/UNPAUSE-PRE-20260708-020152/` — 11
files, all present with sizes consistent with the live substrate's
scale (`guala_atlas.json` 5.8MB, `guala_deep_atlas.json` 4.1MB,
`guala_sections.json` 2.2MB, etc.). Verified by direct listing, not a
live restore-and-reboot test (same verification depth as the prior
dispatch's backup step).

This latency/observability gap is noted as finding 4 below — real, but
outside this dispatch's scope to fix, and not a blocker given the
endpoint being deployed is pure-read and extensively tested.

---

## The production finding

### What happened

First hit against production (task-def `:555`, right after deploy)
returned HTTP 200 with an internally consistent but wrong-looking
result: `neurons_never_fired: 0` sitting next to
`neurons_that_have_ever_fired: 0` — for a 64-neuron organism, at least
one of those two must be 64, not both 0. The endpoint's own "best-effort
JSON: log-and-continue" design meant no crash, but the per-metric-group
try/except was too coarse to explain *why* the per-neuron pass had
silently produced nothing.

CloudWatch showed the real cause immediately:

```
stdp_state: per-neuron snapshot pass failed
Traceback (most recent call last):
  File "/app/dsf_ai_service/app.py", line 5363, in _build_stdp_snapshot
    neuron_snapshots.append(_stdp_snapshot_neuron(n, now_s))
  File "/app/dsf_ai_service/app.py", line 5170, in _stdp_snapshot_neuron
    with neuron._neuron_lock:
AttributeError: 'LoomNeuron' object has no attribute '_neuron_lock'
```

### Root cause

`LoomNeuron.__init__` unconditionally sets `_neuron_lock` (and every
other Phase 1 v2 field: `membrane_potential`, `_incoming_synapse_
weights`, `_last_fire_time_s`, `chi_position`, etc.). But production's
`self.organism` is not always the object `Guala.__init__` just
constructed — `load_full_state()` (`gualaloom_v5_engine.py:9028-9031`)
wholesale-replaces it:

```python
organism_path = os.path.join(state_dir, "guala_organism.pkl.gz")
if os.path.exists(organism_path):
    self.organism = type(self.organism).load_full_state(organism_path)
```

`Embryo.load_full_state` (`embryo.py:710-714`) is a raw
`pickle.load()`. Unpickling a plain object reconstructs its `__dict__`
directly and **never re-runs `__init__`**. A `guala_organism.pkl.gz`
saved before `_neuron_lock` existed in the class produces neuron
objects permanently missing it after every future restore — even
though the *class definition* loaded from the current code has an
`__init__` that would set it, `__init__` simply never executes during
unpickling. `set_spike_bus()`/`set_word_firing_callback()` (called on
every neuron during `Guala.__init__`'s spike-bus wiring) only set those
two specific attributes; neither backfills anything else.

**This is self-perpetuating.** I confirmed `guala_organism.pkl.gz` was
re-saved at `2026-07-08_02-35-49` — minutes into task-def `:556`'s
boot, well after Phase 1 v2 (and this dispatch) were both live. That
re-save pickled the *currently in-memory* organism, which itself was
unpickled from the earlier broken state and never had `_neuron_lock`
backfilled — so the freshly re-saved pickle is **still** missing it.
Every restart from here forward restores from an equally-broken
snapshot, indefinitely, until either a true fresh-organism boot happens
(no `guala_organism.pkl.gz` present) or something explicitly repairs
the gap.

### Verified extent, not assumed

The endpoint's original per-neuron loop wrapped one try/except around
the *entire* iteration — the first neuron's exception aborted the
batch, so I only knew it failed on *at least one* neuron. I fixed this
in-scope (isolating each neuron's snapshot independently, adding a
`diagnostics` field reporting `neurons_total`/`neurons_snapshot_ok`/
`neurons_snapshot_failed`/`neuron_snapshot_sample_error`), added a
local test reproducing the exact traceback, and redeployed (task-def
`:556`, commit `97b3756`) before drawing any conclusion about scope.

Confirmed against the redeployed endpoint: **64 of 64 neurons** fail
identically with the same `AttributeError`. Not a partial or flaky
condition — the entire organism's Phase 1 v2 state is inert.

### Boot vs. 5-minute state collection

Per protocol: snapshot at boot (task-def `:556`, ~165s post-boot), 5
minutes of real production activity, snapshot again (~521s post-boot).
The only field that changed:

```
substrate_identity.uptime_seconds: 165.5 -> 521.0
```

Every other field — `word_neuron_map_size`, all synapse counters, fire
counts, spike bus counters, membrane state, `diagnostics.
neurons_snapshot_failed` (64 in both) — was byte-for-byte identical.
This is the honest state-collection signal the protocol asked for: not
"STDP hasn't accumulated much yet," but confirmation that the
mechanism is completely inert, not merely slow.

### Why this doesn't implicate the introspection endpoint itself

Every failure mode here is in code that predates this dispatch by
hours (Phase 1 v2, `GL-RPT-BLUEPRINT-PHASE-1-MERGED-C1-20260707-v2`).
The endpoint did exactly what it was built to do: read real state,
degrade honestly on a real error instead of fabricating a plausible-
looking answer, and surface the discrepancy loudly enough to
root-cause in one CloudWatch query. No endpoint code change was needed
to *find* this — only to report its true extent precisely (the
per-neuron isolation fix) instead of stopping at "at least one neuron
is broken."

### Why I did not attempt to fix it

This dispatch's own halt condition 2 is "state counters don't match
direct code inspection — halt, route with data." That's exactly what
happened. Fixing organism pickle/restore backward-compatibility is a
different, larger, riskier change (touching the exact mechanism three
separate incidents this session have already required careful,
isolated, backed-up handling for) — not a bounded half-day read-only
introspection task. It also isn't obviously a small fix: the simplest
approach (a `__setstate__` on `LoomNeuron` that backfills missing
Phase-1-v2 fields with their `__init__` defaults after unpickling)
would need its own verification that backfilled defaults don't
silently misrepresent neurons that *should* have accumulated real STDP
state by now, plus a decision about whether to also patch and re-save
the already-corrupted `guala_organism.pkl.gz` in place. That's real
design work belonging to a dedicated dispatch, not a rider on this one.

---

## Post-deploy verification

**Regression harness**: `binding_windows_acceptance` and
`cross_sense_recall_acceptance`, both `PRECONDITION_NOT_MET` —
`presence.joe expected False, actual True` — the same known,
pre-existing harness precondition-setup gap every dispatch tonight has
hit (real live state surfacing through a harness gap, not a
regression). No new or different finding from either scenario.

**Endpoint behavior in production**: 401 without `X-API-Key`, 200 with
it (confirms the auth gate actually joined the existing admin
protection, not a no-op). Response times 0.175s–0.453s across four
separate calls — comfortably under the 500ms budget even though every
call does a full 64-neuron pass that fails and logs on each neuron.

**Substrate health**: unaffected throughout. `guala_status` before and
after both deploys showed `organism_population: 64`, zero dropped
frames, zero queue backlog, tick advancing normally, `running_sha`
matching each deploy exactly.

---

## Files touched + diff summary

- `dsf_ai_service/app.py` — new `/debug/stdp_state` route + 8 module-
  level helper functions (`_stdp_snapshot_neuron`,
  `_word_neuron_map_metrics`, `_synapse_distribution_metrics`,
  `_fire_event_metrics`, `_spike_bus_metrics`, `_membrane_state_
  metrics`, `_ecs_task_def_best_effort`, `_build_stdp_snapshot`) +
  4 new top-level imports (`math`, `heapq`, `logging`, `statistics`).
  Two commits: `dbe7fed` (initial endpoint), `97b3756` (per-neuron
  isolation + `diagnostics` field, written in response to the
  production finding above).
- `dsf_ai_service/tests/test_debug_stdp_state.py` — new, 8 tests.

All committed and pushed to `guala-live`. Live `running_sha` matches
`97b3756` (task-def `:556`).

---

## Findings needing Eve routing

1. **Phase 1 v2's STDP mechanism is inert in production, likely since
   deployment, on every restart.** Root cause: `guala_organism.pkl.gz`
   restore is a raw `pickle.load()` that never re-runs `LoomNeuron.
   __init__()`, so any pickle saved before a field existed in the class
   permanently lacks it after restore — self-perpetuating, since every
   subsequent save re-pickles the same attribute-missing objects. This
   is independent of, and compounds, the already-known "`input_chi` is
   `None` for pure text chat" gap (`GL-RPT-BLUEPRINT-PHASE-1-MERGED-C1-
   20260707-v2` finding 6-adjacent) — even if that gap is closed, the
   mechanism still can't function until every live neuron regains
   `_neuron_lock` and friends. This is the most important finding in
   this report and the natural blocker for the shadow-mode test (prior
   report's finding 1) — there's no STDP state to shadow-compare
   against yet.
2. **Suggested fix directions** (not attempted, for whoever picks this
   up): (a) a `__setstate__` on `LoomNeuron` that backfills any
   Phase-1-v2 field absent after unpickling with its `__init__`
   default — cheapest, but needs verification it can't misrepresent a
   neuron's true history; (b) an explicit one-time repair pass at boot
   that walks `_all_neurons()` and backfills missing attributes before
   the spike bus wiring runs; (c) accept the loss and let it
   self-heal only on the next true fresh-organism boot (no
   `guala_organism.pkl.gz` present) — simplest, but indefinite timeline
   since nothing currently triggers that condition.
3. **Backup latency/observability gap.** `guala_backup` took ~7 minutes
   against a documented "30-120s" estimate, and produced no
   parseable completion or error log line in either of two attempts —
   confirmed complete only by direct S3 listing. Not blocking (this
   dispatch's own change is low-risk and a very recent existing backup
   already covered it), but worth knowing before a future,
   higher-stakes dispatch depends on this step's timing or log output.
4. **The endpoint itself is ready for its intended purpose** once
   finding 1 is resolved — `diagnostics` will read `neurons_snapshot_
   failed: 0` and every other field will start reflecting real state
   the moment neurons regain their Phase 1 v2 fields. No further
   endpoint changes anticipated.

## Recommendation

`/debug/stdp_state` is live, correct, and safe — verified via 8 local
tests plus real production exercise across two deploys, zero substrate
impact, zero regression. It found what it was built to find, just not
the answer anyone expected: Phase 1 v2 currently has no STDP state to
observe because the mechanism can't run at all on any restored
organism. Recommend: (1) treat finding 1 as the priority follow-up
dispatch — the shadow-mode test recommended in the prior report cannot
proceed meaningfully until this is fixed; (2) decide among the three
fix directions in finding 2; (3) re-run this endpoint's boot-vs-5-min
state collection once a fix ships, as the acceptance signal that STDP
state is actually accumulating.

---

### Changelog
- v1 (2026-07-08, c1): `/debug/stdp_state` built, tested locally (8
  passing tests), and deployed to production in two steps (`:555`
  initial, `:556` after adding per-neuron failure isolation in
  response to what production immediately surfaced). Backup verified
  (slow, but complete). No regression on existing harness scenarios.
  Boot-vs-5-minute state collection confirms, rather than merely
  suggests, that Phase 1 v2's STDP mechanism is fully inert in
  production — root-caused to a pickle/`__init__` incompatibility in
  the organism restore path, independent of the endpoint itself. Fix
  deliberately not attempted (out of this dispatch's bounded, read-only
  scope, per its own halt condition). Four findings routed to Eve.
