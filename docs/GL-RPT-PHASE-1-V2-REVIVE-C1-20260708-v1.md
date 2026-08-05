# GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v1

**doc_id:** GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v1
**From:** c1
**Executing:** GL-CMD-PHASE-1-V2-REVIVE-EVE-20260708-v1
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)

**HALTED before writing or deploying any fix code, per this dispatch's
own halt condition 5 ("scope violation... any Phase 2+ mechanism to
work"). No production changes were made — no backup was taken because
none was needed. Local, read-only investigation against the actual
current production state (downloaded, tested, deleted — never
modified) found that the two bugs this dispatch describes are real,
but fixing only them, exactly as specified, would not achieve the
stated acceptance criteria. A third, previously-unknown gap makes the
fix incomplete: `LoomBrain` loses its own Phase 1 v2 fields
(`_spike_bus`, `_guala_ref`) through the identical pickle/`__init__`
mechanism as Bug A, and nothing anywhere in the codebase re-wires them
after `load_full_state()` replaces `self.organism`. Routing with full
data, as instructed.**

---

## What I confirmed matches the dispatch

Read `LoomNeuron.__init__` directly (not the dispatch's illustrative
draft) to build an accurate field list, per the dispatch's own
instruction ("If any field name here doesn't match what's actually in
`__init__`, use `__init__`'s name and default. Do not guess."). Found
two real discrepancies in the dispatch's illustrative `__setstate__`
draft that would have shipped live bugs if copied verbatim:

- `_last_fire_time_s` — draft defaults it to `None`; the real
  `__init__` default is `0.0` (`neuron.py:592`). Backfilling `None`
  would reintroduce a crash: `neuron.py`'s own
  `_receive_upstream_fire_notification` does `if self._last_fire_time_s
  <= 0: return`, and my own `_stdp_snapshot_neuron` does
  `now_s - s["last_fire_time_s"]` — both raise `TypeError` against
  `None`. This would have shipped the *exact same class* of bug this
  dispatch exists to fix.
- `_recent_presynaptic_fires` — draft defaults it to `[]` (a list); the
  real `__init__` default is `{}` (a dict, `Dict[str, List[Tuple[float,
  float]]]`, `neuron.py:582`). `receive_spike` calls `.setdefault(...)`
  on it — a list has no `.setdefault`; the first spike delivered to a
  backfilled neuron would crash immediately with `AttributeError`.

Both would only have surfaced on the *next* restart after a fix
believed to be verified — exactly the kind of gap this session's
practice of testing against real state, not synthetic assumptions, is
meant to catch. Not deployed; caught before any code was written.

Bug B (the `input_chi` gate) matches the dispatch's description exactly
— confirmed via direct read of `brain.py`'s injection call site.

## What doesn't match: Bug C (new, not in the dispatch)

### Reproduction

Downloaded the actual current production state
(`s3://dsf-ai-site-backups/guala/2026-07-08_02-35-49/`, the full
directory, not just the organism file) to a local scratchpad,
constructed a fresh `Guala()`, and called `load_full_state()` against
it — the exact same call `_gl_init()` makes in production. Deleted the
downloaded state immediately after the test; nothing was retained or
modified.

```
BEFORE restore:
  g._spike_bus is g.organism.brain._spike_bus: True
  g.organism.brain._guala_ref is g: True

[[GualaLoom] Organism restored: identity=0b4c244a-... tick=215502 pop=64 ...]

AFTER restore (real production organism):
  organism_population: 64
Traceback (most recent call last):
  File ".../probe_real_restore.py", line 23, in <module>
    print(..., g._spike_bus is g.organism.brain._spike_bus)
AttributeError: 'LoomBrain' object has no attribute '_spike_bus'.
Did you mean: 'set_spike_bus'?
```

`organism.brain._spike_bus` doesn't evaluate to `None` after restore —
the attribute **does not exist at all**, because the restored
`LoomBrain` instance was unpickled from a pre-Phase-1-v2 pickle, and
`__init__` (which sets `self._spike_bus = None` per `brain.py:115-123`)
never ran. Identical failure class to Bug A, one level up the object
graph.

Grepped the entire codebase for every `set_spike_bus`/`_guala_ref =`
call site:

```
dsf_ai_service/v4/gualaloom_v5_engine.py:1787:  _neuron.set_spike_bus(self._spike_bus)
dsf_ai_service/v4/gualaloom_v5_engine.py:1798:  self.organism.brain.set_spike_bus(self._spike_bus)
dsf_ai_service/v4/gualaloom_v5_engine.py:1799:  self.organism.brain._guala_ref = self
```

All three live inside `Guala.__init__`, which runs once, *before*
`_gl_init()` separately calls `g.load_full_state(STATE_DIR)`
(`app.py:1260,1271`). `load_full_state()` replaces `self.organism`
wholesale (`gualaloom_v5_engine.py:9031`) — including
`self.organism.brain` — and nothing re-runs the wiring afterward.
There is no second call site anywhere.

### Consequence for this dispatch's fix, specifically

Even with a perfectly correct `LoomNeuron.__setstate__` (Bug A fixed)
and the `input_chi` gate removed (Bug B fixed), `LoomBrain.step`'s own
injection gate —

```python
if getattr(self, '_spike_bus', None) is not None:
    self._inject_input_as_spikes(input_signal, input_chi, modality)
```

— reads `self._spike_bus` where `self` is `organism.brain`. Post-restore,
that's missing (`getattr` returns the `None` default safely, no crash,
but the condition is always false). Injection would still never fire
on a restored organism — which is every production boot that isn't a
true first boot. The fix as specified would pass local, single-process
tests (which never call `load_full_state()`) and then demonstrably fail
the dispatch's own acceptance criteria in production: `/debug/
stdp_state` would still show `total_spikes_injected_since_boot: 0`
after 5 minutes, for a reason invisible from `LoomNeuron` alone.

## A second, related risk found during the same investigation: Bug D

Separately, while constructing a **fresh** (non-restored) `Guala()` to
set up the Bug C reproduction, save failed on its own:

```
[GualaLoom] save failed for guala_organism.pkl.gz: cannot pickle '_thread.lock' object
[GualaLoom] save failed for guala_tapestry.pkl.gz: cannot pickle '_thread.lock' object
```

Confirmed in isolation: `threading.Lock` is not picklable in CPython
(`pickle.dumps` on a bare object holding one raises the same
`TypeError`). This is not a new bug introduced by anything in this
dispatch — **it already exists today**, for any fully-`__init__`'d
organism. Production's *current* `guala_organism.pkl.gz` saves
successfully today for exactly the reason this whole investigation
started: production's live neurons are missing `_neuron_lock`, so
there's no lock object for `pickle.dump` to choke on. Bug A and this
save-failure are two sides of the same coin — the substrate currently
"works" (in the sense that saves succeed) *because* it's broken (in the
sense that Phase 1 v2 doesn't run).

Implication: `LoomNeuron.__setstate__` alone (Bug A's literal fix, as
specified) would fix the *read/restore* side but, the moment a
restored neuron's backfilled `_neuron_lock` is a real `threading.Lock`,
the *next* `save_full_state()` call would start failing — for every
neuron, on every save, indefinitely — silently caught by the existing
try/except at the call site (`gualaloom_v5_engine.py:8749-8752`). That
save carries the *entire* organism object graph, not just Phase 1 v2
fields — including `neuron.binding_atlas`, the structure legacy
`recall_fast` actually reads. A save-path failure introduced here would
not touch legacy *read* behavior (nothing currently reads back a
mid-session, unsaved state), but it would mean any binding_atlas
learning accumulated after this fix deploys is unrecoverable at the
next restart, silently, unless something also excludes the
unpicklable fields from serialization (a `__getstate__` companion to
`__setstate__`) or the save path is otherwise made resilient. This is
squarely within the "save path" and "any Phase 2+ mechanism" language
of halt condition 5 as well.

## Why I halted instead of extending scope myself

The dispatch draws its guardrails explicitly and specifically: no
changes to `__init__`, the save path, `_select_entry_neurons`, or "any
Phase 2+ mechanism ... to work" (halt condition 5). What I found is not
a matter of taste or an opportunity for improvement — it's that the
dispatch's literal scope cannot reach its own stated acceptance
criteria, for a reason (`LoomBrain`'s independent loss of `_spike_bus`/
`_guala_ref`, plus the latent save-path interaction) that only a
`__setstate__` on a *second* class, plus an explicit re-wire call
placed somewhere in the restore sequence, plus a decision about
`__getstate__`/save-path resilience, could close. That's three
non-trivial design decisions (where does the re-wire call belong —
inside `load_full_state()`, or in `_gl_init()` right after it returns?
Does `__getstate__` exclude `_spike_bus`/`_word_firing_callback` too,
since a bound method back to `Guala` would otherwise try to pickle the
entire object graph from within one neuron's state? Are there other
Phase-1-v2-bearing classes I haven't found?) — not a bounded extension
of a half-day dispatch, and exactly what halt condition 5 anticipates.

I did not implement any of the three candidate designs unilaterally.

## What was and wasn't touched

- **No files modified.** `git status` is clean relative to `947d821`
  (this dispatch's own filed text).
- **No backup taken.** Not needed — no production-affecting action was
  attempted.
- **No local test files added** — the reproduction scripts live only in
  the session scratchpad, not the repo, since they were throwaway
  investigation, not deliverables.
- **Downloaded production state** (the full `2026-07-08_02-35-49/`
  backup directory, ~137MB) to a local scratchpad for the Bug C
  reproduction — read-only, never modified, deleted immediately after
  the test completed. Confirmed via `rm -rf` in this session.

## Findings needing Eve routing

1. **Bug C (new): `LoomBrain` needs the same `__setstate__` treatment
   as `LoomNeuron`, plus an explicit re-wire step.** A `LoomBrain.
   __setstate__` can backfill `_spike_bus`/`_guala_ref` to `None`
   (matching `__init__`), but only `Guala` has the actual `SpikeBus`
   instance and `self` reference to wire them to — that re-wire call
   has to live somewhere in the restore sequence itself (candidate:
   right after `self.organism = type(self.organism).load_full_state(...)`
   at `gualaloom_v5_engine.py:9031`, mirroring `__init__`'s own wiring
   loop). This is a design decision, not a mechanical one — routing
   for Eve's call on placement.
2. **Bug D (new): the organism save path cannot currently survive a
   fully-populated Phase 1 v2 neuron.** `threading.Lock` is provably
   unpicklable; fixing Bug A's restore side without also addressing the
   save side would convert today's "saves succeed because the substrate
   is broken" into "saves silently fail once the substrate is fixed" —
   for the *whole* organism pickle, not just Phase 1 v2 fields. Needs a
   `LoomNeuron.__getstate__` (and possibly `LoomBrain.__getstate__`,
   if `_guala_ref` — a reference back to the entire `Guala` object —
   is also in that class's pickled state) that excludes exactly the
   unpicklable/inappropriate-to-persist fields (`_neuron_lock`,
   `_spike_bus`, `_word_firing_callback`, `_guala_ref`), with
   `__setstate__` recreating or re-wiring them appropriately. This
   needs its own verification (a real save round-trip test, not just
   restore) before being trusted.
3. **Verification recommendation for the next attempt**: whatever the
   next dispatch specifies, verify it against the *actual* current
   production `guala_organism.pkl.gz` locally before deploying (the
   method used in this report — download, test, delete) rather than
   against a freshly-constructed local `Guala()` alone. A fresh-boot
   test never exercises `load_full_state()` and would have missed both
   Bug C and Bug D entirely; that's exactly how they stayed hidden
   through the original Phase 1 v2 dispatch and the STDP-introspection
   dispatch that found Bug A.
4. **The two draft `__setstate__` field-default corrections above**
   (`_last_fire_time_s` → `0.0` not `None`; `_recent_presynaptic_fires`
   → `{}` not `[]`) are worth carrying into whatever `__setstate__`
   design Eve produces next, regardless of how Bug C/D get resolved.

## Recommendation

Do not deploy `__setstate__`-only + gate-removal as literally specified
— it's verified, empirically, against real production state, not to
work. Recommend a v2 of this dispatch that scopes in: `LoomBrain.
__setstate__`, the re-wire call's placement, and a `__getstate__`
decision for both classes, evaluated together as one coherent
save/restore round-trip fix rather than three separate patches. Happy
to execute once Eve has made the placement/exclusion-scope decisions
above — the empirical groundwork (exact field lists, exact failure
reproductions, exact call sites) is already done and doesn't need
repeating.

---

### Changelog
- v1 (2026-07-08, c1): Halted before any code change or deploy.
  Confirmed the dispatch's two named bugs are real and its illustrative
  `__setstate__` draft has two field-default errors that would have
  shipped new crashes. Found a third bug (`LoomBrain` loses `_spike_bus`/
  `_guala_ref` the same way, with no re-wire path anywhere in the
  codebase) that makes the dispatch's literal scope insufficient to
  reach its own acceptance criteria, confirmed by loading the actual
  current production organism pickle locally. Found a fourth, related
  risk (`threading.Lock` is unpicklable; fixing Bug A alone would break
  organism saves for the whole object graph, not just Phase 1 v2
  fields, the moment restored neurons regain a working lock). No
  production changes made. Four findings routed to Eve for a v2
  dispatch design.
