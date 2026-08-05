# GL-RPT-NEURON-AUTONOMY-INHIBITION-DESIGN-C1-20260710-v1

**doc_id:** GL-RPT-NEURON-AUTONOMY-INHIBITION-DESIGN-C1-20260710-v1
**From:** c1
**Context:** Not a formal GL-CMD dispatch. Joe made an architectural point —
a real brain coordinates via local state + async message-passing (spikes),
not mutual-exclusion locks on shared global state — and asked for a
read-only research/design assessment of this project's own spike-bus/
neuron-autonomy effort against that point: precisely why the last real
deploy attempt (`GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v3`) reverberated,
what the minimal real-neuroscience fix would be, and whether finishing it
would actually let `self.lock` go away. Read-only research and design.
No production code touched.
**To:** Eve (routing per standing practice — architecture design question)

---

## Verdict

**The specific thing this task asked for — diagnose the v3 cascade
precisely and propose a minimal, testable damping mechanism — turned out
to already be built, deployed, and holding in production.** Commit
`712578f` (2026-07-08) added Dale's-law-style polarity-signed inhibition
to `LoomNeuron._fire()`; commit `432d9c5` (2026-07-09) added an
independent per-neuron fire-rate circuit breaker; commit `56453a3`
(2026-07-09) fixed a separate STDP bootstrap deadlock. All three are
ancestors of the code currently running live (`guala_status` confirms
`running_sha=4bfaa87`, task-def revision 586, `EVENT_DRIVEN_SUBSTRATE=1`
in the live task definition, checked directly against AWS — not inferred
from a doc). I re-ran the project's own repro test for the exact v3
failure mode locally, today, against this real code: the pre-fix
condition (all-excitatory, fully-potentiated ring) still reverberates
(8,110 fires after external input stops); the real, currently-live
condition (real ~19%-inhibitory population) does not (0 fires after
settle). This is not a claim from a doc — it is a test I executed myself
in this session (`dsf_ai_service/loom_model/tests/
test_lateral_inhibition_cascade.py`, 3/3 passing, output captured below).
The remaining honest work is narrower than the task assumed: one real gap
(no homeostatic synaptic scaling — confirmed absent by direct grep, not
inferred) and one important scope correction (this fix does **not**
let `self.lock` shrink, and structurally can't yet, for a precise,
traceable reason in §4). No new blocker found beyond those two.

---

## 1. Root cause of the v3 cascade, confirmed from code, not from the doc's summary

The v3 halt report (`GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v3`) named,
at the time, "no lateral inhibition, cyclic topology, STDP positive
feedback" as the cause. I traced each claim against the actual code
(not the report's prose) and against what a *later* commit
(`712578f`) subsequently re-diagnosed. Both are correct, about
different parts of the same incident:

- **Topology is genuinely cyclic — confirmed.** `LoomCluster.
  _build_ring_topology()` (`dsf_ai_service/loom_model/cluster.py:116-145`)
  wires each neuron's K=16 neighbors as "the K/2 neurons on each side of
  i, wrapping around" via `(i + d) % N` — a literal ring. `k_neighbors`
  is clamped to `n_neurons - 1` per hemisphere (`cluster.py:74`), and each
  hemisphere seeds 8 neurons, so `min(16, 7) = 7`: every 8-neuron
  hemisphere is a fully-connected clique (this is where the v3 report's
  "448 = 8 hemispheres × 8 neurons × 7 intra-hemisphere neighbors" number
  comes from — I confirmed the arithmetic independently). Plus
  `LoomBrain._wire_cross_hemi()` (`brain.py:151`) adds cross-hemisphere
  edges between projection neurons. A fully-connected 8-clique plus
  cross-hemi edges has cycles of every length ≥ 2 — a fired neuron's
  signal can return to itself along more than one path. Genuinely
  cyclic, not close to a tree.
- **STDP genuinely has no depressive/homeostatic *ceiling* mechanism,
  only a depressive *rule*.** `_apply_stdp_potentiation` (`neuron.py:
  932-946`, pre-before-post) and `_receive_upstream_fire_notification`
  (`neuron.py:948-965`, post-before-pre depression) are both real and
  both exist — so STDP is not purely one-directional. But both write
  through `min(current + delta, MAX_SYNAPSE_WEIGHT)` /
  `max(current - delta, MIN_SYNAPSE_WEIGHT)` — a **per-synapse hard
  clip** (`MAX_SYNAPSE_WEIGHT=5.0`, `MIN_SYNAPSE_WEIGHT=0.0`,
  `neuron.py:101-102`), not a network-level rebalancing rule. I grepped
  the entire firing/plasticity path for any synaptic-scaling or weight-
  normalization mechanism (`homeostat`, `synaptic_sc`, `normalize.*
  weight`) — zero hits outside unrelated Coordinator/needs-oscillation
  code. **Confirmed: no homeostatic plasticity exists anywhere in this
  codebase today.** This is real, and is the one gap from the classic
  three mechanisms that is genuinely still open (§2, §3).
- **Refractory period exists and is real (2.0ms, `neuron.py:671`,
  checked in `receive_spike` before the threshold check,
  `neuron.py:913-914`) — but the v3-era design could not rely on it
  as the actual brake.** `test_lateral_inhibition_cascade.py`'s own
  docstring (lines ~30-40) states this precisely and I confirmed the
  reasoning: an isolated, perfectly uniform single-clique case can hit
  an *accidental* numerical coincidence where round-trip propagation
  delay equals the refractory window, silencing propagation regardless
  of polarity — a timing coincidence, not a designed damping mechanism,
  and one that a real, non-uniform, concurrently-loaded 64-neuron
  organism (real production shape) breaks by construction. Refractory
  period alone was never a reliable brake against this topology; it was
  correctly not credited as the fix.
- **What actually stopped the cascade, verified by re-running the
  fix's own test today**: `712578f` signs each neuron's *outgoing*
  spike weight by its own transmitter polarity — `getattr(self,
  '_polarity', 1.0)` (`neuron.py:1086`), where `_polarity` is embryo's
  pre-existing, deterministic ~20%/80% inhibitory/excitatory seeding
  split (previously computed but only ever read by an unrelated
  population vote, `embryo.py`'s `_seed_dna_diversity`). This is Dale's
  principle / a GABAergic-interneuron-style population split, applied at
  the point where it changes dynamics: `weight * polarity` at
  `neuron.py:1092`, so an inhibitory neuron's contribution now pulls a
  downstream neuron's membrane potential *away* from threshold. I ran
  the project's own three-test suite for this locally in this session:

  ```
  test_real_seeding_produces_an_inhibitory_population: PASS (12/64 inhibitory)
  test_forced_all_excitatory_reproduces_the_cascade:
      {'n_neurons': 64, 'n_inhibitory': 0, 'fires_during_settle': 818,
       'fires_after_settle': 8110, 'total_fires': 8928}
      PASS (bug reproduced as expected)
  test_real_polarity_fix_stops_the_cascade:
      {'n_neurons': 64, 'n_inhibitory': 12, 'fires_during_settle': 44,
       'fires_after_settle': 0, 'total_fires': 44}
      PASS (network stopped firing)
  3 passed in 12.81s
  ```

  With every synapse pre-saturated to `MAX_SYNAPSE_WEIGHT` (the
  "worst-case fully-potentiated" state the real incident reached) and
  all-excitatory forced (the pre-fix condition), a single kick produces
  8,110 fires with no further external input — the cascade, reproduced,
  today, on demand. With the real, unmodified ~19%-inhibitory population
  (matching embryo's ~20% design target), the identical saturated-weight,
  single-kick setup produces **zero** fires once external input stops.
  This is the "repro that now shows it no longer runs away" the task
  asked for — it already existed; I verified it rather than trusting the
  commit message.
- **A second, independent, non-biological safety net also exists and
  is live**: `_check_fire_rate_breaker` (`neuron.py:990-1018`), a
  per-neuron sliding-window fire-rate cap (`FIRE_BREAKER_CEILING_HZ=
  250.0`, derived arithmetically from `refractory_period_ms`/`tau_m_ms`,
  not tuned — reasoning documented in `neuron.py:140-212`). `_fire()`
  checks it (`neuron.py:1041`) and skips *only* the outgoing spike-bus
  re-injection when tripped (`neuron.py:1085`, `if not
  breaker_tripped:`) — membrane reset, refractory, and STDP bookkeeping
  still happen unconditionally. I ran its 6-test suite locally too, all
  pass. This targets a different incident (a single neuron in a runaway
  firing loop, ~3,800Hz, caught separately) and is defense-in-depth, not
  the mechanism that stopped the v3 cascade — but it is real and live
  alongside it.
- **The `712578f` commit message's own framing ("root cause was NOT a
  runaway propagation cascade... 99.4% of firing traced to direct
  external injection") is about a *different* bug than the one the
  polarity fix addresses, and both are real, in the same commit.** The
  99.4%-external finding is about `_select_entry_neurons` falling
  through to a 16-neuron random fallback on every single word (a
  `chi_position`/wraparound bug, now fixed) — it explains why so much
  of the *original* v3 firing volume was direct injection rather than
  propagation, not why propagation, once triggered, failed to stop. The
  commit's own code comment at `neuron.py:1079-1081` explicitly credits
  the polarity signing with fixing "the missing brake on recurrent
  excitation that let a fixed loop of synapses reverberate
  indefinitely (GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v3 cascade
  finding)" — i.e. the same commit closed two separate, real bugs, and
  the reverberation-specific one is the polarity fix, confirmed by the
  isolated test above which holds the entry-selection question fixed
  (irrelevant to a single, deliberate, direct kick) and varies only
  polarity.

## 2. Which classic mechanism fits this codebase, assessed against what's real here

Of the three classic answers (refractory period, lateral/feedback
inhibition, homeostatic plasticity):

- **Refractory period**: already present, already correct as a hard
  per-neuron limit (500Hz absolute ceiling), but — as shown above —
  not a reliable brake against *this* topology's cyclic reverberation
  on its own; the specific numeric coincidence that stops it in an
  isolated case doesn't generalize. Necessary, not sufficient. No
  further change needed here; it does its actual job (bounding a
  single neuron's own max rate) correctly.
- **Lateral/feedback inhibition**: this is what actually fixed the v3
  incident, in the form real cortex uses it — Dale's principle, a
  minority (~20%) inhibitory population whose *output sign* opposes
  the majority excitatory population, rather than a separate "each
  neuron inhibits its literal ring neighbors" circuit. This is the
  *minimal* correct version for this codebase specifically: it reused
  a field (`_polarity`) that already existed, deterministically, for
  every neuron, changed one line's arithmetic (`weight * polarity`),
  and required no new topology, no new pickled state, no new tunable
  constant. It is provably minimal by construction — there is no
  smaller change that touches the actual propagation-sign problem.
- **Homeostatic plasticity (synaptic scaling)**: genuinely absent
  (§1). This is the piece still worth building, but for a different
  reason than stopping the acute v3-style cascade (that's handled). Its
  job is the *slow*, long-horizon risk: STDP's per-synapse clip means
  a population of synapses can each independently drift toward
  `MAX_SYNAPSE_WEIGHT` over a long real production lifetime (the
  cascade test's own `_saturate_all_intra_hemisphere_synapses` helper
  explicitly models this as "the worst case a real loop reaches after
  sustained STDP potentiation" and confirms the *current* fix survives
  it) — but nothing today notices or corrects an individual neuron's
  *total* incoming drive climbing toward the sum of many near-saturated
  synapses, the way real cortical synaptic scaling
  (Turrigiano-style, multiplicative rescaling of a neuron's whole
  synapse set to hold its own average firing rate near a set point)
  does. Today's system is provably safe against a *single* saturated
  case (tested); it is not provably safe against every synapse
  drifting toward saturation *simultaneously* over the production
  substrate's actual multi-week lifetime, because nothing bounds that
  except each synapse's own independent clip. This is the real,
  still-open gap — lower urgency than the acute cascade (which is
  fixed), but the correct next piece, not a redundant one.

## 3. Concrete minimal next step

Given the acute damping mechanism is already built, tested, and live,
the honest "minimal next step" is not a new firing-path change (that
would be re-touching the exact hot zone that caused three real
incidents this week) — it's two small, isolated, low-risk pieces:

**3a. A bounded per-neuron homeostatic scaling pass, off the hot path.**
Add a function (not called from `_fire()` or `receive_spike()` — called
from the existing sleep/dream consolidation cycle, which already runs
periodically and already does bookkeeping-only work outside the
request-latency path) that, for each neuron, computes
`total_incoming = sum(_incoming_synapse_weights.values())` and, only if
that total exceeds a bound (e.g. `HOMEOSTATIC_CEILING = K_neighbors *
STDP_DEFAULT_SYNAPSE_WEIGHT * some small multiple`, derived
arithmetically from existing constants the way `FIRE_BREAKER_CEILING_HZ`
was, not invented), multiplicatively rescales every entry in
`_incoming_synapse_weights` down by `HOMEOSTATIC_CEILING /
total_incoming`. No new pickled field (reuses `_incoming_synapse_
weights`, already round-trips correctly per `56453a3`'s own note). No
firing-path change, no propagation-timing change, no risk of a fourth
firing-path incident, because it never runs on the same code path that
caused the first three.
**Test in isolation exactly like the cascade fix was**: drive a single
neuron's `_incoming_synapse_weights` toward saturation via repeated
real STDP exposure (the same harness `test_stdp_repeated_exposure_
learning.py` already uses), assert `total_incoming` stays bounded
after the scaling pass runs, and — the actual acceptance criterion —
re-run `test_lateral_inhibition_cascade.py`'s exact scenario with
scaling active to confirm it doesn't reintroduce the cascade (it
shouldn't; it only ever *reduces* weights, working in the same
direction as inhibition, never against it — the same argument
`_receive_upstream_fire_notification`'s comment already makes about
STDP depression at `neuron.py:1098-1099`).

**3b. Extend the live verification window, not the code.** The v3
incident was caught at ~9 minutes of live runtime with no-real-traffic
firing as the signature. The current fix has now run in production for
about a day (per today's `GL-RPT-OVERNIGHT-BLUEPRINT-PROGRESS-C1-
20260710-v1`), but the specific "boot vs. N-minutes-of-zero-real-
traffic" protocol the STDP-introspection endpoint was built for
(`GL-CMD-STDP-INTROSPECTION-EVE-20260707-v1`) has not been re-run
against *this* fix over a genuinely quiet window the way it was for the
original incident. Recommend one read-only pass: hit `/debug/
stdp_state`'s `total_fire_events_since_boot` delta across a real window
with confirmed-zero `organism_experience_bound`/`sensory_organism_
processed` events (the same cross-check that caught v3), purely to
convert "holding for a day under mixed real traffic" into an explicit
"confirmed quiet when input is quiet" data point. Zero code risk — it's
reading an endpoint that already exists.

Neither piece touches `_fire()`, `receive_spike()`, propagation timing,
or the firing threshold — the parameters this file's own comments
identify as "the parameters that govern cascade risk" (`neuron.py:
120-122`) and the ones three real incidents this week already taught
this project to be most careful with.

## 4. The lock question, traced precisely — not assumed

**No — finishing this mechanism would not, by itself, let `self.lock`
shrink, and it structurally can't yet, for a reason visible directly in
the code, not a guess:**

- The spike-bus/firing path is **already fully lock-free with respect
  to `self.lock`** — this part of Joe's architectural point is already
  realized, not aspirational. `SpikeBus` (`dsf_ai_service/substrate/
  spike_bus.py`) never references `self.lock` or any `Guala`-level
  attribute at all — it only calls `target.receive_spike(spike)`
  (`spike_bus.py:123`). `LoomNeuron.receive_spike`/`_fire` use only
  `self._neuron_lock`, a **per-neuron** lock (`neuron.py:883`,
  `with self._neuron_lock:`) — never `self.lock`. Both production call
  sites that trigger injection — the word branch
  (`gualaloom_v5_engine.py:3985-4009`) and the sensory branch
  (`gualaloom_v5_engine.py:3940-3953`) — call `_inject_input_as_spikes`
  **before** and **outside** any acquisition of `self.lock` or even
  `self._organism_lock` (the sensory branch's `hemi.step()` call
  *does* use `self._organism_lock`, at `gualaloom_v5_engine.py:3954`,
  but that's the pre-existing legacy step path, not the injection this
  task is about). This mirrors a precedent already set and named in the
  code itself — the word branch's own comment at
  `gualaloom_v5_engine.py:4009-4012` cites "Joe's no-locks ruling":
  "writes are lock-free spill_write into per-neuron wave cells now...
  the lock was never needed for that, only for excluding readers, and
  readers no longer need excluding." The spike-bus mechanism is a
  second, independent instance of that same already-ratified pattern,
  not a new idea needing re-litigation.
- **But `self.lock` (`gualaloom_v5_engine.py:1958`,
  `threading.RLock()`) protects a large, mostly disjoint domain the
  spike-bus mechanism doesn't touch and doesn't produce data for**:
  `self.sections[*].modes`, `self.window_manager`, `self.tick`,
  emission-candidate selection, `open_response_windows`, and —
  critically — the **legacy** `chi_atlas`/`binding_atlas` write path
  via `self.organism.experience_word()` → `experience_moment()`, which
  is what real recall and real emission actually read today
  (`RECALL_BACKEND=legacy` is the confirmed live default — checked
  directly against the running task definition, not assumed). The
  spike/STDP path writes `_incoming_synapse_weights`/`membrane_
  potential` — real, live, growing state — but per `432d9c5`'s own
  commit message, that state currently only feeds a **shadow** emission
  candidate path built "for observation only, logging a real word-level
  agreement comparison," with "default remains 'legacy', zero behavior
  change." Nothing that reads through `self.lock` today consumes
  spike/STDP state as its source of truth.
- **Conclusion, precisely**: the spike-bus mechanism is real,
  independent proof that local-state, per-component message-passing can
  coexist with `self.lock` in this codebase without deadlocking or
  needing to join it — a genuine, working existence proof for Joe's
  architectural point, not a demo. But it *sits alongside* `self.lock`'s
  domain today; it has not replaced any of the state `self.lock`
  protects, because emission/recall haven't been cut over to read
  spike/STDP state instead of legacy `chi_atlas`/`binding_atlas`. That
  cutover — not the inhibition mechanism this task was about — is the
  actual prerequisite for `self.lock` shrinking, and it is a
  materially larger, separately-scoped, currently-unattempted change
  (shadow-only wiring exists; nothing switches the default). Reporting
  this precisely rather than either overclaiming ("spikes replace the
  lock") or underclaiming ("spikes are irrelevant to the lock") is the
  honest answer: it's necessary infrastructure for that future cutover,
  proven safe to run alongside the lock, and not yet a substitute for
  any part of it.

## 5. Skepticism check — any new real blocker?

Applying the same standard this effort's own history holds itself to
(five real halts before this): I looked for a reason this apparent
success is not what it looks like, specifically checking the failure
classes that caused the *previous* four halts (pickle/restore gaps,
missing call-site wiring, scope-creep, and the cascade itself).

- **Not a stale-pickle repeat**: `guala_status`'s `running_sha` is
  `4bfaa87`, a direct descendant of `712578f`/`432d9c5`/`56453a3`, and
  `persistence_health.load_successful_at_boot: true` with a recent save
  (`2026-07-10T21:32:08Z`) — this is the actual running/saving code,
  not a doc claim about code that was later reverted.
  `56453a3`'s own commit message notes it "touches neither
  membrane_threshold nor any propagation/firing dynamic... no new
  pickled state (reuses `_incoming_synapse_weights`, which already
  round-trips correctly)" — consistent with the earlier
  `__getstate__`/`__setstate__` fix from `GL-RPT-PHASE-1-V2-REVIVE-
  C1-20260708-v3` still holding.
- **Not an unreachable-call-site repeat**: word-branch injection is
  live and unconditional on `EVENT_DRIVEN_SUBSTRATE` (confirmed `=1` in
  the running task definition directly via `aws ecs
  describe-task-definition`, not inferred). Sensory-branch injection is
  correctly still gated **off** (`SENSORY_SPIKE_INJECTION_ENABLED`
  absent from the live env, defaults to `"0"` per `neuron.py`/engine
  code) — this is a deliberate, currently-correct scope limit tied to a
  *different*, separate incident (wave-atlas cells never decaying to
  zero, a continuously-kicked entry neuron), not a leftover gap in this
  task's scope.
- **One real, honestly-scoped gap remains**: homeostatic synaptic
  scaling (§2, §3a) — confirmed absent, not yet built, not yet
  deployed. This is not a blocker to anything currently live; it's the
  correctly-identified next piece for long-horizon safety, explicitly
  scoped small and off the hot path in §3a specifically so it does not
  become incident #4.
- **One scope correction, not a blocker**: the lock question (§4) —
  the honest answer is narrower than "yes, this replaces the lock" and
  narrower than what a shallow read of "spike-bus is live now" might
  imply. Flagged precisely rather than left ambiguous.

No new blocker of the kind that caused the five prior halts was found.

---

## Recommendation

Treat the inhibition-design question this task posed as answered by
work already on `guala-live`, empirically re-verified in this session
rather than taken on faith: Dale's-law polarity-signed inhibition
(`712578f`) is the mechanism that stopped the v3 cascade, a per-neuron
fire-rate breaker (`432d9c5`) is a real independent second layer, and
both are live and holding (`running_sha=4bfaa87`, task-def 586). The
one genuine remaining piece from the classic three mechanisms —
homeostatic synaptic scaling — is real, currently absent, and scoped
in §3a as a small, hot-path-free, independently-testable addition
that does not touch `_fire()`/`receive_spike()`/propagation timing.
The lock question has a precise, code-traced answer in §4: the
mechanism proves lock-free message-passing works in this codebase
(a real second instance of "Joe's no-locks ruling," already
established elsewhere) but does not yet replace anything `self.lock`
protects, because recall/emission have not been cut over off the
legacy `chi_atlas`/`binding_atlas` path — that cutover, not this task's
inhibition question, is the actual next prerequisite for narrowing
`self.lock`, and it is a separate, larger, currently-unscoped piece of
work.

---

### Changelog
- v1 (2026-07-10, c1): Read-only research/design assessment. Confirmed
  from code (not doc summaries) that the v3 reverberating cascade's
  cyclic-topology-plus-STDP diagnosis was correct, that refractory
  period alone was never a reliable brake against it, and that Dale's-
  law polarity-signed inhibition (`712578f`) is the mechanism that
  actually fixed it — re-verified empirically in this session by
  re-running the project's own repro/fix test locally (3/3 passing,
  output captured). Confirmed a real, independent second safety layer
  (per-neuron fire-rate circuit breaker, `432d9c5`) is also live.
  Confirmed via direct AWS/live-endpoint checks (not doc inference)
  that both are running in production today (`running_sha=4bfaa87`,
  task-def 586, `EVENT_DRIVEN_SUBSTRATE=1`). Identified the one real
  remaining gap (homeostatic synaptic scaling, absent, confirmed by
  grep) and scoped a minimal, hot-path-free, independently-testable
  addition for it. Traced the lock question precisely from code: the
  spike-bus path is already fully lock-free relative to `self.lock`
  (proof the message-passing pattern works here), but does not yet
  replace any state `self.lock` protects, because recall/emission
  remain on the legacy `chi_atlas`/`binding_atlas` path
  (`RECALL_BACKEND=legacy`, confirmed live) — that cutover is a
  separate, larger, unscoped prerequisite. No new blocker of the class
  that caused this effort's five prior halts was found.
