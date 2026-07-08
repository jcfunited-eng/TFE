# GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v2

**doc_id:** GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v2
**From:** c1
**Executing:** GL-CMD-PHASE-1-V2-REVIVE-EVE-20260708-v2
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)

**HALTED again, before writing any fix code, per this dispatch's own
halt condition 8 ("scope violation... requires changes beyond items
1-5"). No production changes made — no backup taken, nothing deployed.
v2's design for bugs A/B/C/D is sound and I found no errors in it
(confirmed `LoomBrain.__init__`'s field list matches Eve's draft
exactly: only `_spike_bus`/`_guala_ref`). But before writing any of it,
I verified whether the dispatch's own acceptance criteria — "non-zero
deltas... after 5 minutes of **production traffic**" — is even
reachable, and found it is not: `LoomBrain.step()`, the only method
that calls `_inject_input_as_spikes`, is not called from anywhere in
the real production request path. Confirmed exhaustively, not by
spot-check. Fixing bugs A-D perfectly would still produce zero
injected spikes from real traffic, because nothing in production ever
calls the function whose gate this dispatch removes.**

---

## What I verified matches v2's design (no problems found)

- **`LoomBrain.__init__`** read directly (`brain.py:61-123`): the only
  Phase 1 v2 fields are `self._spike_bus = None` (line 122) and
  `self._guala_ref = None` (line 123). Matches v2's draft exactly —
  no third field, no correction needed here.
- **`SpikeBus._neuron_registry`** (`spike_bus.py:60`) is a plain
  instance attribute (`self._neuron_registry = neuron_registry`), not
  captured in a closure or otherwise fixed at construction. `wire_spike_
  bus()`'s planned `self._spike_bus._neuron_registry = neuron_registry`
  reassignment (halt condition 2's concern) is safe as designed — no
  SpikeBus reconstruction needed.
- **`load_full_state()` has more call sites than the dispatch assumed**
  (halt condition 3 anticipated this and asked me to check): beyond
  `app.py:1271` (`_gl_init`'s main path), there's also `app.py:1296`
  and `:1338` (the identity-mismatch fallback paths from the
  `EXPECTED_IDENTITY` incident), plus `substrate_runner.py:583` and
  `:643` (a separate, likely-remote-mode-only boot path — per an
  existing code comment elsewhere calling `substrate_runner.py`'s
  status handler "a dead, remote-mode-only twin" in the current
  `SUBSTRATE_MODE=embedded` production config, but not independently
  re-verified here). `wire_spike_bus()` would need calling after each
  reachable one. Listing this for whoever picks up the next iteration;
  not the reason for this halt.

## Why I halted anyway: `LoomBrain.step()` is unreachable from production

Before implementing anything, I traced the dispatch's own acceptance
signal backward: "5 minutes of real production traffic" causing a
nonzero delta requires *something* in the real request path to call
`_inject_input_as_spikes`. That method has exactly one caller:

```
dsf_ai_service/loom_model/brain.py:180:  self._inject_input_as_spikes(input_signal, input_chi, modality)
```

— inside `LoomBrain.step()`. Searched every call site of `.brain.step(`
or `.step(` that could resolve to it, exhaustively:

```
dsf_ai_service/loom_model/experience.py:90,98,100,102:  self.brain.step(...)
```

All four are inside `ExperiencePipeline` (`experience.py`), whose only
instantiation in the entire codebase is:

```
dsf_ai_service/loom_model/embryo.py:807:  pipe = ExperiencePipeline(emb.brain, SensoryTransducer(NullAtlasReader()))
```

— inside `seed_organism()`, a standalone demo function in a file gated
by `if __name__ == "__main__":` (`embryo.py:825`). Not imported or
called by `app.py`, `gualaloom_v5_engine.py`, or any production request
handler.

Meanwhile, the actual production paths that process real input both
bypass `LoomBrain.step()` entirely:

- **Text (the "word" branch of the organism worker thread,
  `gualaloom_v5_engine.py:3186-3210`)**: calls
  `self.organism.experience_word(word, signal)`
  → `Embryo.remember()` (`embryo.py:538-554`)
  → `n.experience_moment(concept, signals, self.tick, precomputed_lanes)`
  **directly on every neuron in every hemisphere** — no `brain.step()`
  call anywhere in this chain.
- **Sensory (the "sensory" branch, same worker thread,
  `gualaloom_v5_engine.py:3164-3178`)**: calls
  `hemi.step(input_signal, sensory_tick, input_chi)` directly
  (`LoomHemisphere.step`, `hemisphere.py:67`) → `self.cluster.step(...)`
  (`LoomCluster.step`) — also never reaches `LoomBrain.step()`.

This isn't a surprise buried somewhere obscure — it's already written
down, in `brain.py`'s own `step()` docstring, dated to the *original*
Phase 1 v2 dispatch:

> "Confirmed via grep that `LoomBrain.step()` itself is not on the
> current production call path at all (production calls
> `hemi.step()`/`cluster.step()` directly) — this dual-write only
> matters for callers that DO reach `step()` (`ExperiencePipeline`,
> tests, probes) plus any future production call site that starts
> calling it."

Phase 1 v2 was built, correctly, as infrastructure for a *future*
cutover — the comment says so explicitly. What's missing from *this*
dispatch (v2 revive) is any step that makes production actually reach
it. Bugs A-D are all real and all still worth fixing (they're
prerequisites — `wire_spike_bus()` and the pickle round-trip have to
work regardless of what calls `step()`), but fixing them alone cannot
produce the dispatch's own acceptance signal, because the production
request path this dispatch's 5-minute traffic check depends on never
calls the method being repaired.

## What this means concretely

Even a flawless deploy of everything in this dispatch's items 1-5
would, 5 minutes later, show:

- `total_spikes_injected_since_boot: 0` (unchanged from today)
- `word_neuron_map_size: 0` (unchanged)
- `synapses_strengthened: 0` (unchanged)

— identical to the STDP-introspection endpoint's original finding,
because the gate removal in `LoomBrain.step()` never executes; nothing
calls that function. The fix would be silently correct and silently
inert at the same time — the worst outcome to discover *after*
deploying, not before.

I confirmed the mechanism itself is sound when directly invoked — my
own local test from the STDP-introspection dispatch
(`test_snapshot_reflects_real_word_injection_and_stdp`) calls
`g.organism.brain.step('dog', tick=i, input_chi=42, modality='language')`
explicitly and gets real fires/spikes/synapse updates. The gap isn't in
the injection mechanism — it's that nothing in production's real
request flow ever calls the entry point that triggers it.

## Why I didn't extend scope to fix this myself

Making production traffic actually reach the injection mechanism means
adding a spike-bus call inside `Embryo.remember()` and/or
`LoomHemisphere.step()`/`LoomCluster.step()` — the *actual* hot path
for every word and every sensory frame the substrate processes. That's
a fundamentally larger, higher-stakes change than removing a gate in a
method nothing calls: it touches code that runs on every single
production request, not an isolated, currently-dead code path. It's
exactly the "any Phase 2+ mechanism" and "requires changes beyond
items 1-5" language of halt condition 8. Deciding *where* the call
belongs (inside `remember()` itself? A wrapper around it? Only on the
sensory path, since text's `input_chi` is usually `None` anyway per the
original Phase 1 v2 report's finding 6?) is a design decision, not a
mechanical extension — Eve's call, not mine to make unilaterally.

## What was and wasn't touched

- **No files modified.** No `__getstate__`/`__setstate__`/
  `wire_spike_bus` code was written — the call-path check came before
  any implementation, once I started verifying the dispatch's
  assumptions the same way the v1 halt report recommended (check
  against real code/state before trusting a draft).
- **No backup taken, nothing deployed, no production interaction at
  all this session** beyond read-only greps and file reads.

## Findings needing Eve routing

1. **Bug E (new): no production code path reaches `LoomBrain.step()`.**
   Confirmed exhaustively (every call site of `.step(` that could
   resolve to it, every instantiation of `ExperiencePipeline`). This is
   the reason v2's acceptance criteria can't be met by items 1-5 alone.
   The original Phase 1 v2 dispatch already knew and documented this
   (`brain.py`'s own docstring) — it was scoped as future-cutover
   infrastructure at the time, and that framing didn't carry forward
   into this dispatch's "production traffic" acceptance signal.
2. **Bugs A-D (this dispatch's items 1-5) are still real and still
   worth building** — they're prerequisites for whatever eventually
   does call `step()`, and the round-trip test design (download real
   pickle, restore, wire, save, reload, verify) is exactly right
   regardless of how Bug E gets resolved. Recommend keeping this
   design intact in a v3, just adding the call-path piece.
3. **`load_full_state()` has 5 call sites**, not the 1-2 the dispatch
   implicitly assumed (`app.py:1271,1296,1338`; `substrate_runner.py:
   583,643`) — `wire_spike_bus()` needs calling after each one that's
   actually reachable in the current `SUBSTRATE_MODE=embedded`
   production config. Worth confirming which of the 5 are live vs.
   dead code before wiring all of them.
4. **Suggested design question for v3, not a recommendation**: should
   the injection call go inside `Embryo.remember()` (text path),
   `LoomHemisphere.step()`/`LoomCluster.step()` (sensory path), both,
   or should the acceptance criteria itself change to "verified via
   direct probe call" (like the round-trip test's own
   `_inject_input_as_spikes` call) rather than "observed from real
   traffic" until a deliberate decision is made about which real path
   should carry it? That's a scope and risk-tolerance call for Eve,
   not something to infer from the dispatch's silence on it.

## Recommendation

Don't deploy v2 as scoped — it's correct on everything it touches but
cannot reach its own acceptance criteria. Recommend a v3 that either
(a) adds one deliberately-chosen production call site alongside items
1-5, evaluated with the same care as everything else in this dispatch
(a real hot-path change deserves its own halt conditions and rollback
plan), or (b) redefines the acceptance signal to a direct probe call
(already partially designed in v2's own round-trip test) and
explicitly defers "observable from real traffic" to a later, separate
dispatch once a call site is chosen. Either is a legitimate path;
which one is Eve's call. The pickle/wiring work in v2's items 1-5
remains ready to execute as specified the moment that decision is
made — nothing about today's finding invalidates it.

---

### Changelog
- v2 (2026-07-08, c1): Halted again, before any code change or
  deploy. Confirmed v2's `LoomBrain`/`SpikeBus` design details are
  correct and found no field-list errors this time. Found a new,
  dispatch-invalidating gap: `LoomBrain.step()` — the only caller of
  `_inject_input_as_spikes` — has no production call path at all
  (confirmed exhaustively; only reachable from demo-only
  `ExperiencePipeline`). Production's real text and sensory paths both
  bypass it entirely, a fact already documented in the original Phase
  1 v2 dispatch's own code comments but not carried into this
  dispatch's "5 minutes of real production traffic" acceptance
  criteria. Also flagged 5 `load_full_state()` call sites (only 1-2
  assumed) for whoever scopes the call-site wiring next. Four findings
  routed to Eve for a v3 design.
