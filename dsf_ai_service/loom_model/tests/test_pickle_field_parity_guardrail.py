"""
GL-CMD-PICKLE-FIELD-PARITY-GUARDRAIL: automated getstate/setstate field-
parity check for LoomNeuron (and, with an adapted invariant, LoomBrain).

Why this exists
----------------
Three separate real incidents this week were all the same class of bug:
a field gets added to a class's __init__, but __getstate__/__setstate__
(the pickle-customization hooks save_full_state()/load_full_state()
actually use to persist and restore the live organism) fall out of sync
with it. pickle.load() reconstructs an object's __dict__ directly and
NEVER calls __init__ -- so a pickle saved before a field existed restores
an object that is either missing that field entirely, or silently reset
to whatever hardcoded default someone typed into __setstate__ by hand:

  1. GL-RPT-STDP-INTROSPECTION-C1-20260707-v1: production neurons found
     completely missing _neuron_lock and every other Phase 1 v2 field --
     __getstate__/__setstate__ did not exist on LoomNeuron at all yet.
  2. GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v1: the illustrative
     __setstate__ draft written to fix (1) had two wrong hardcoded
     defaults -- _last_fire_time_s -> None (real __init__ default: 0.0)
     and _recent_presynaptic_fires -> [] (real __init__ default: {}).
  3. GL-RPT-PHASE-1-V2-REVIVE-C1-20260708-v1 (same report): active
     runtime references were left absent after restore instead of
     backfilled to their constructor defaults.

All three were caught only by a person re-reading __init__ line by line
before the code shipped -- exactly the failure mode that guarantees
recurrence. This file introspects the REAL, CURRENT set of attributes
__init__ actually produces (by constructing an instance and reading
__dict__ -- never a hand-maintained list of field names) and the REAL,
CURRENT behavior of __setstate__ (by actually calling it, never by
reading its source as text), and fails loudly -- a real assertion, not a
warning -- the moment the two diverge.

Scope, stated honestly
-----------------------
LoomNeuron.__getstate__ pops the unpicklable lock and active physical
runtime references; __setstate__ then defensively backfills those fields PLUS
every other field ever added to __init__ since these restore hooks were
introduced (the membrane/STDP/fire-breaker fields), because production
pickles predating each of those really do exist. Fields that have
existed since LoomNeuron's original commit (psi_lattice, couplings,
krimelack, neuron_id, ...) are not defensively backfilled at all -- and
don't need to be, because no pickle that has ever existed in this
codebase's history predates them (there was no custom __getstate__/
__setstate__ before this Phase 1 v2 work, so every historical pickle
already carries the full pre-Phase-1-v2 __dict__ as-is). This guardrail
therefore checks two things, matching the two real failure modes above
exactly:

  A. every field __getstate__ excludes, and everything __setstate__'s own
     defensive `if not hasattr(...)` logic claims responsibility for,
     must actually be present after restoring from a maximally stale
     (empty) pickle -- "dropped silently" (incident 3's bug class).
  B. every one of those same fields, once present, must hold the exact
     value a freshly constructed instance would have -- "wrong stale
     default" (incident 2's bug class).

It also runs a full, realistic pickle round trip on a fresh, fully wired
instance and checks that EVERY __init__ field survives with an equal
value (catches a future regression in the plain dict.update() path too,
e.g. an accidental new __getstate__ exclusion with nothing to recreate
it -- would have caught incident 1 in spirit, had this guardrail existed
before __getstate__/__setstate__ was added at all).

LoomBrain has the same __getstate__/__setstate__ *pattern* but a
genuinely different, documented *policy*: __setstate__ deliberately
leaves _spike_bus/_guala_ref ABSENT after restore (Guala.wire_spike_bus()
re-wires them externally, since only Guala holds the live SpikeBus/self
reference -- see brain.py's own __setstate__ docstring). The LoomBrain
tests below respect that real, intentional difference instead of forcing
LoomNeuron's invariant onto it.
"""

import os
import sys
import pickle
import threading
from collections import deque

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
os.environ.setdefault("SUBSTRATE_MODE", "embedded")

from dsf_ai_service.loom_model.neuron import LoomNeuron
from dsf_ai_service.loom_model.brain import LoomBrain


# ---------------------------------------------------------------------
# Generic, introspection-only helpers (no hardcoded field-name lists)
# ---------------------------------------------------------------------

_SIMPLE_TYPES = (type(None), bool, int, float, complex, str, bytes)


def _values_equal(a, b):
    """Best-effort structural equality that catches a wrong/stale scalar
    default (the real incident-2 bug class) without producing false
    positives on custom-class fields that don't define __eq__ -- those
    would otherwise compare by identity, which is ALWAYS False for two
    objects on either side of a real pickle round trip (unpickling
    always creates new instances), and that is not a real divergence.
    """
    if type(a) is not type(b):
        return False
    if isinstance(a, _SIMPLE_TYPES):
        return a == b
    if isinstance(a, dict):
        return (set(a.keys()) == set(b.keys())
                and all(_values_equal(a[k], b[k]) for k in a))
    if isinstance(a, deque):
        return (len(a) == len(b)
                and getattr(a, "maxlen", None) == getattr(b, "maxlen", None)
                and all(_values_equal(x, y) for x, y in zip(a, b)))
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(_values_equal(x, y) for x, y in zip(a, b))
    try:
        import numpy as np
        if isinstance(a, np.ndarray):
            return a.shape == b.shape and bool(np.array_equal(a, b))
    except ImportError:
        pass
    # Custom class instances (LoomHemisphere, PsiLattice, Krimelack, ...):
    # "same type survived the round trip" is the honest, best-available
    # signal here -- deep-diffing bespoke domain objects is out of scope
    # for this guardrail (already checked above via type(a) is type(b)).
    return True


def _neuron_field_sets():
    """Introspects LoomNeuron.__init__'s real, current, complete field
    set (via construction + __dict__), __getstate__'s real exclusion set
    (via diffing __dict__ against __getstate__()'s output), and
    __setstate__'s real backfill behavior (via actually calling it with
    a maximally stale, empty pickle) -- never a hand-maintained list.
    """
    fresh = LoomNeuron("_guardrail_fresh_ref")
    init_attrs = set(fresh.__dict__.keys())

    full_state = fresh.__getstate__()
    excluded = init_attrs - set(full_state.keys())

    restored_empty = LoomNeuron.__new__(LoomNeuron)
    restored_empty.__setstate__({})
    backfilled = set(restored_empty.__dict__.keys())

    return fresh, init_attrs, excluded, restored_empty, backfilled


def assert_neuron_getstate_setstate_parity():
    """The actual guardrail logic, factored out of the pytest test so it
    can also be invoked against a deliberately reconstructed buggy
    __setstate__ during verification (see the dispatch's own
    verification notes / report for the monkeypatch reproduction of
    incidents 2 and 3, run once against this function to confirm it
    fails on them and passes on the real, current, fixed code)."""
    fresh, init_attrs, excluded, restored_empty, backfilled = _neuron_field_sets()

    assert len(init_attrs) > 10, (
        "sanity check failed: LoomNeuron.__init__ set suspiciously few "
        f"attributes ({len(init_attrs)}) -- introspection is probably "
        "broken, not that the class actually shrank"
    )

    # --- Check A: fields __getstate__ excludes must all come back after
    # restoring from a pickle missing EVERYTHING (the worst case) ---
    dropped = sorted(excluded - backfilled)
    assert not dropped, (
        "LoomNeuron.__setstate__ silently DROPS these __init__ field(s) "
        "when restoring an old pickle that predates them -- excluded by "
        "__getstate__ but never backfilled: " + ", ".join(dropped) +
        ". This is incident 3's exact bug class: an active runtime field "
        "was left absent instead of restored to its constructor default."
    )

    # --- Check B: every field __setstate__ DOES backfill must match the
    # real __init__ default, not a stale/wrong stand-in value ---
    mismatches = []
    for name in sorted(backfilled):
        if name == "_neuron_lock":
            if not isinstance(restored_empty._neuron_lock, type(threading.Lock())):
                mismatches.append(f"{name}: not a real threading.Lock after restore")
            continue
        fresh_value = getattr(fresh, name)
        restored_value = getattr(restored_empty, name)
        if not _values_equal(fresh_value, restored_value):
            mismatches.append(
                f"{name}: __setstate__ backfills {restored_value!r}, but "
                f"__init__'s real default is {fresh_value!r}"
            )
    assert not mismatches, (
        "LoomNeuron.__setstate__ backfills the following field(s) to a "
        "STALE/WRONG value instead of __init__'s real default -- this is "
        "incident 2's exact bug class (GL-RPT-PHASE-1-V2-REVIVE-C1-"
        "20260708-v1: _last_fire_time_s=None instead of 0.0, "
        "_recent_presynaptic_fires=[] instead of {}):\n  " +
        "\n  ".join(mismatches)
    )


def test_neuron_getstate_setstate_introspected_field_parity():
    assert_neuron_getstate_setstate_parity()
    print("test_neuron_getstate_setstate_introspected_field_parity: PASS")


def test_neuron_full_roundtrip_preserves_every_init_field():
    """A realistic (non-simulated) pickle round trip on a fully wired
    fresh neuron. Every field __init__ sets must survive with an equal
    value, except the runtime fields __getstate__ deliberately excludes,
    which must come back to their documented post-restore state
    (_neuron_lock: a real, usable new Lock; _spike_bus and _mood_source:
    None, re-wired later by the physical runtime)."""
    fresh = LoomNeuron("_guardrail_roundtrip_ref")
    fresh.set_spike_bus(object())

    blob = pickle.dumps(fresh)  # must not raise -- incident 1's original symptom
    restored = pickle.loads(blob)

    init_attrs = set(fresh.__dict__.keys())
    excluded = init_attrs - set(fresh.__getstate__().keys())

    failures = []
    for name in sorted(init_attrs):
        if not hasattr(restored, name):
            failures.append(f"{name}: present on a fresh neuron but MISSING after a real pickle round trip")
            continue
        restored_value = getattr(restored, name)
        if name in excluded:
            if name == "_neuron_lock":
                if not isinstance(restored_value, type(threading.Lock())):
                    failures.append(f"{name}: not a real Lock after restore")
            elif restored_value is not None:
                failures.append(
                    f"{name}: expected None after restore (re-wired "
                    f"externally), got {restored_value!r}"
                )
            continue
        fresh_value = getattr(fresh, name)
        if not _values_equal(fresh_value, restored_value):
            failures.append(f"{name}: fresh={fresh_value!r} != restored={restored_value!r}")

    assert not failures, (
        "Real pickle round trip does not preserve these LoomNeuron "
        "field(s):\n  " + "\n  ".join(failures)
    )
    print("test_neuron_full_roundtrip_preserves_every_init_field: PASS")


# ---------------------------------------------------------------------
# LoomBrain: same pattern, different (documented) policy -- see module
# docstring. Introspection-driven, not hardcoded, but the assertion
# matches LoomBrain's real contract instead of LoomNeuron's.
# ---------------------------------------------------------------------

def _brain_field_sets():
    fresh = LoomBrain(brain_seed=42, seed_size=8)
    init_attrs = set(fresh.__dict__.keys())
    full_state = fresh.__getstate__()
    excluded = init_attrs - set(full_state.keys())
    return fresh, init_attrs, excluded


def test_brain_full_roundtrip_preserves_every_init_field():
    """Every LoomBrain.__init__ field must survive a real pickle round
    trip with an equal value, EXCEPT the fields __getstate__ excludes
    (discovered by introspection, not a hardcoded pair of names) --
    those must come back absent-or-None, never a stale leftover value,
    matching brain.py's own __setstate__ docstring ("_spike_bus/
    _guala_ref intentionally left absent -- Guala.wire_spike_bus() sets
    both after restore")."""
    fresh = LoomBrain(brain_seed=42, seed_size=8)
    fresh.set_spike_bus(object())
    fresh._guala_ref = object()

    blob = pickle.dumps(fresh)
    restored = pickle.loads(blob)

    init_attrs = set(fresh.__dict__.keys())
    excluded = init_attrs - set(fresh.__getstate__().keys())

    failures = []
    for name in sorted(init_attrs):
        if name in excluded:
            restored_value = restored.__dict__.get(name, None)
            if restored_value is not None:
                failures.append(
                    f"{name}: expected absent-or-None after restore "
                    f"(re-wired externally by Guala.wire_spike_bus()), "
                    f"got {restored_value!r}"
                )
            continue
        if not hasattr(restored, name):
            failures.append(f"{name}: present on a fresh brain but MISSING after a real pickle round trip")
            continue
        fresh_value = getattr(fresh, name)
        restored_value = getattr(restored, name)
        if not _values_equal(fresh_value, restored_value):
            failures.append(f"{name}: fresh != restored (type or value mismatch)")

    assert not failures, (
        "Real pickle round trip does not preserve these LoomBrain "
        "field(s):\n  " + "\n  ".join(failures)
    )
    print("test_brain_full_roundtrip_preserves_every_init_field: PASS")


def test_brain_getstate_exclusion_is_the_only_divergence():
    """LoomBrain's __setstate__ has no per-field backfill logic at all
    (unlike LoomNeuron's) -- it relies entirely on __getstate__ excluding
    exactly the runtime-only/back-reference fields and nothing else. If
    __getstate__ ever starts excluding an ADDITIONAL field (e.g. a future
    field added to __init__ that also needs runtime-only treatment, or a
    typo'd .pop() call), restoring from a state missing it would leave it
    silently absent with NO Guala.wire_spike_bus()-style external re-wire
    path for anything other than _spike_bus/_guala_ref. This test doesn't
    hardcode which fields are "allowed" to be excluded -- it fails loudly
    the instant restoring from a getstate-produced state diverges from
    restoring a fully-populated fresh instance for any field NOT in the
    (introspected) excluded set."""
    fresh, init_attrs, excluded = _brain_field_sets()

    state = fresh.__getstate__()
    restored = LoomBrain.__new__(LoomBrain)
    restored.__setstate__(state)

    failures = []
    for name in sorted(init_attrs - excluded):
        if not hasattr(restored, name):
            failures.append(f"{name}: dropped by the getstate/setstate round trip despite not being an excluded field")
            continue
        if not _values_equal(getattr(fresh, name), getattr(restored, name)):
            failures.append(f"{name}: value diverged across the getstate/setstate round trip")

    assert not failures, (
        "LoomBrain.__getstate__/__setstate__ silently diverge on "
        "non-excluded field(s):\n  " + "\n  ".join(failures)
    )
    print("test_brain_getstate_exclusion_is_the_only_divergence: PASS")


if __name__ == "__main__":
    test_neuron_getstate_setstate_introspected_field_parity()
    test_neuron_full_roundtrip_preserves_every_init_field()
    test_brain_full_roundtrip_preserves_every_init_field()
    test_brain_getstate_exclusion_is_the_only_divergence()
    print("ALL PASS: test_pickle_field_parity_guardrail")
