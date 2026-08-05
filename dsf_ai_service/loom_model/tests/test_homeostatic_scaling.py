"""
test_homeostatic_scaling.py — GL-CMD-LOOM-HOMEOSTATIC-SCALING.

Tests for the bounded, per-neuron homeostatic synaptic-scaling maintenance
pass (LoomNeuron.apply_homeostatic_scaling() / _homeostatic_scale_locked(),
neuron.py) and its trigger (Embryo._apply_homeostatic_scaling_pass(),
embryo.py, called from remember()'s existing REFLECTION_SNAPSHOT_INTERVAL
tick-modulo hook, gated by HOMEOSTATIC_SCALING_ENABLED, default OFF).

Required coverage (per dispatch):
  (a) never increases any weight, under any constructible scenario
  (b) correctly rescales an artificially over-saturated neuron back under
      the ceiling, proportions preserved
  (c) a concurrency/stress test analogous to the WaveAtlas v2/v3 tests --
      real concurrent writers hammering _incoming_synapse_weights while
      the scaling pass runs repeatedly, zero crashes, zero silently-lost
      legitimate weight updates (proven via ledger-replay, not eyeballed)
  (d) zero behavior change with the kill switch OFF (the shipped default),
      and zero lines touched in gualaloom_v5_engine.py

Plus a sanity check that the kill switch, when explicitly turned on
test-process-locally, actually engages -- proving it is a real gate, not
decorative.

Construction pattern (bare LoomNeuron for unit-level tests, real Embryo
for trigger-level tests) matches test_neuron.py / test_imagination_
reflection.py already in this directory. Direct `n._incoming_synapse_
weights[...] = ...` manipulation matches the existing, established
pattern in test_lateral_inhibition_cascade.py's
`_saturate_all_intra_hemisphere_synapses`.
"""

import os
import random
import subprocess
import sys
import threading
import time

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.loom_model.neuron import (
    LoomNeuron,
    HOMEOSTATIC_SCALING_CEILING,
    MAX_SYNAPSE_WEIGHT,
    MIN_SYNAPSE_WEIGHT,
    STDP_DEFAULT_SYNAPSE_WEIGHT,
)
from dsf_ai_service.loom_model.embryo import Embryo


def _signals(seed_offset, word):
    """Same hand-built real multi-modal signal shape test_imagination_
    reflection.py uses -- production's ExperiencePipeline shape, without
    needing the full sensory-transducer/catalog stack."""
    rng = np.random.default_rng(2000 + seed_offset)
    return {
        "language": word,
        "visual": rng.uniform(0, 1, 50).tolist(),
        "auditory": np.sin(np.arange(200) / 200.0 * 2 * np.pi * (5 + seed_offset)).tolist(),
        "tactile": rng.uniform(0, 1, 50).tolist(),
        "olfactory": rng.uniform(0, 1, 50).tolist(),
        "gustatory": rng.uniform(0, 1, 50).tolist(),
    }


def _make_bare_neuron(neuron_id):
    n = LoomNeuron(neuron_id)
    n._incoming_synapse_weights = {}
    return n


# ---------------------------------------------------------------------------
# (a) never increases any weight
# ---------------------------------------------------------------------------

def test_never_increases_any_weight_random_distributions():
    rng = random.Random(12345)
    scenarios_checked = 0
    for trial in range(200):
        n = _make_bare_neuron(f"a{trial}")
        n_synapses = rng.randint(0, 20)
        for i in range(n_synapses):
            n._incoming_synapse_weights[f"src{i}"] = rng.uniform(
                MIN_SYNAPSE_WEIGHT, MAX_SYNAPSE_WEIGHT)
        before = dict(n._incoming_synapse_weights)
        n.apply_homeostatic_scaling()
        after = n._incoming_synapse_weights
        assert set(after.keys()) == set(before.keys()), (
            "scaling must never add or remove keys"
        )
        for k in before:
            assert after[k] <= before[k] + 1e-12, (
                f"trial={trial} key={k} INCREASED: before={before[k]} after={after[k]}"
            )
        scenarios_checked += 1
    assert scenarios_checked == 200
    print(f"\n== never-increases: {scenarios_checked} random scenarios "
          f"(0-20 synapses each), zero increases == PASS")


def test_never_increases_edge_cases():
    # empty dict -> no-op
    n = _make_bare_neuron("edge1")
    assert n.apply_homeostatic_scaling() is False
    assert n._incoming_synapse_weights == {}

    # single synapse well under ceiling -> untouched (identity, not just value)
    n2 = _make_bare_neuron("edge2")
    n2._incoming_synapse_weights["s0"] = STDP_DEFAULT_SYNAPSE_WEIGHT
    before2 = dict(n2._incoming_synapse_weights)
    assert n2.apply_homeostatic_scaling() is False
    assert n2._incoming_synapse_weights == before2

    # sum EXACTLY at ceiling -> boundary must be a no-op (condition is "> ceiling")
    n3 = _make_bare_neuron("edge3")
    n3._incoming_synapse_weights["s0"] = HOMEOSTATIC_SCALING_CEILING
    assert n3.apply_homeostatic_scaling() is False
    assert n3._incoming_synapse_weights["s0"] == HOMEOSTATIC_SCALING_CEILING

    # all-zero weights -> sum 0 <= ceiling -> no-op
    n4 = _make_bare_neuron("edge4")
    for i in range(5):
        n4._incoming_synapse_weights[f"s{i}"] = 0.0
    assert n4.apply_homeostatic_scaling() is False
    assert all(v == 0.0 for v in n4._incoming_synapse_weights.values())

    # worst case: every synapse individually AT its own MAX_SYNAPSE_WEIGHT
    # (the real per-synapse ceiling STDP already enforces) -- must rescale
    # down, never up, never past MIN_SYNAPSE_WEIGHT either.
    n5 = _make_bare_neuron("edge5")
    for i in range(16):
        n5._incoming_synapse_weights[f"s{i}"] = MAX_SYNAPSE_WEIGHT
    before5 = dict(n5._incoming_synapse_weights)
    assert n5.apply_homeostatic_scaling() is True
    for k, v in n5._incoming_synapse_weights.items():
        assert v < before5[k]
        assert v >= MIN_SYNAPSE_WEIGHT - 1e-12
    print("\n== never-increases: edge cases (empty / under-ceiling / exact-boundary "
          "/ all-zero / all-saturated) == PASS")


# ---------------------------------------------------------------------------
# (b) correctly rescales an over-saturated neuron back under the ceiling
# ---------------------------------------------------------------------------

def test_rescales_oversaturated_neuron_back_under_ceiling_preserving_proportions():
    n = _make_bare_neuron("b1")
    raw = {"s0": 5.0, "s1": 3.0, "s2": 2.0, "s3": 4.0}  # sum = 14.0, way over ceiling
    for k, v in raw.items():
        n._incoming_synapse_weights[k] = v
    total_before = sum(raw.values())
    assert total_before > HOMEOSTATIC_SCALING_CEILING

    changed = n.apply_homeostatic_scaling()
    assert changed is True

    after = n._incoming_synapse_weights
    total_after = sum(after.values())
    assert total_after == pytest.approx(HOMEOSTATIC_SCALING_CEILING, abs=1e-9), (
        f"expected sum to land exactly at the ceiling, got {total_after}"
    )
    expected_factor = HOMEOSTATIC_SCALING_CEILING / total_before
    for k, v in raw.items():
        assert after[k] == pytest.approx(v * expected_factor, abs=1e-12), (
            f"key={k}: expected proportional rescale to {v * expected_factor}, got {after[k]}"
        )
    # ALL touched by the SAME factor -- ratios between any two weights preserved.
    assert after["s0"] / after["s1"] == pytest.approx(raw["s0"] / raw["s1"], abs=1e-9)
    print(f"\n== rescale: 14.0 -> {total_after:.6f} (ceiling={HOMEOSTATIC_SCALING_CEILING}), "
          f"factor={expected_factor:.6f}, proportions preserved == PASS")


def test_zero_or_negative_ceiling_is_a_safe_noop():
    """Defensive guard: an invalid ceiling (<=0) must never produce a
    ZeroDivisionError or flip weights negative -- it's simply a no-op.
    Unreachable via the one real (no-argument) production call site
    today, but the invariant should hold unconditionally."""
    n = _make_bare_neuron("edge_ceiling")
    n._incoming_synapse_weights = {"s0": 1.0, "s1": 2.0}
    before = dict(n._incoming_synapse_weights)
    assert n.apply_homeostatic_scaling(ceiling=0.0) is False
    assert n._incoming_synapse_weights == before
    assert n.apply_homeostatic_scaling(ceiling=-1.0) is False
    assert n._incoming_synapse_weights == before
    print("\n== rescale: ceiling <= 0 is a safe no-op (no ZeroDivisionError, no sign flip) == PASS")


def test_rescale_respects_custom_ceiling_argument():
    n = _make_bare_neuron("b2")
    n._incoming_synapse_weights = {"s0": 1.0, "s1": 1.0, "s2": 1.0}  # sum = 3.0
    assert n.apply_homeostatic_scaling(ceiling=1.5) is True
    assert sum(n._incoming_synapse_weights.values()) == pytest.approx(1.5, abs=1e-9)
    print("\n== rescale: respects an explicit non-default ceiling argument == PASS")


def test_repeated_calls_converge_and_stay_stable():
    """Calling the pass again immediately after a rescale (no new writes
    in between) must be a no-op -- proves it doesn't over-shrink or
    oscillate."""
    n = _make_bare_neuron("b3")
    n._incoming_synapse_weights = {"s0": 10.0, "s1": 10.0}
    assert n.apply_homeostatic_scaling() is True
    after_first = dict(n._incoming_synapse_weights)
    assert n.apply_homeostatic_scaling() is False, (
        "second call with no intervening writes must be a no-op"
    )
    assert n._incoming_synapse_weights == after_first
    print("\n== rescale: repeated calls converge to a stable fixed point == PASS")


# ---------------------------------------------------------------------------
# (c) concurrency / stress test -- zero crashes, zero silently-lost writes
# ---------------------------------------------------------------------------

def test_concurrency_stress_public_api_zero_crashes_and_bounded():
    """Real concurrent writers (STDP-shaped additive/subtractive updates,
    the exact clamp discipline _apply_stdp_potentiation /
    _receive_upstream_fire_notification use in production) hammering
    _incoming_synapse_weights through neuron._neuron_lock, while several
    threads repeatedly call the real public apply_homeostatic_scaling()
    entry point concurrently. Sanity pass over the ACTUAL production
    entry point: zero exceptions, every weight stays inside
    [MIN_SYNAPSE_WEIGHT, MAX_SYNAPSE_WEIGHT] throughout."""
    n = _make_bare_neuron("stress_public")
    n_keys = 6
    for i in range(n_keys):
        n._incoming_synapse_weights[f"src{i}"] = STDP_DEFAULT_SYNAPSE_WEIGHT

    errors = []
    stop = threading.Event()

    def writer(seed):
        rng = random.Random(seed)
        while not stop.is_set():
            key = f"src{rng.randrange(n_keys)}"
            delta = rng.uniform(0.001, 0.05)
            try:
                with n._neuron_lock:
                    current = n._incoming_synapse_weights.get(key, STDP_DEFAULT_SYNAPSE_WEIGHT)
                    if rng.random() < 0.5:
                        n._incoming_synapse_weights[key] = min(current + delta, MAX_SYNAPSE_WEIGHT)
                    else:
                        n._incoming_synapse_weights[key] = max(current - delta, MIN_SYNAPSE_WEIGHT)
            except Exception as e:
                errors.append(e)

    def scaler():
        while not stop.is_set():
            try:
                n.apply_homeostatic_scaling()
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(6)]
    threads += [threading.Thread(target=scaler) for _ in range(3)]
    for t in threads:
        t.start()
    time.sleep(2.0)
    stop.set()
    for t in threads:
        t.join(timeout=5.0)
        assert not t.is_alive(), "a stress thread did not finish -- possible deadlock"

    assert not errors, f"expected zero exceptions under concurrent load, got {len(errors)}: {errors[:3]}"
    for k, v in n._incoming_synapse_weights.items():
        assert MIN_SYNAPSE_WEIGHT - 1e-9 <= v <= MAX_SYNAPSE_WEIGHT + 1e-9, f"{k}={v} out of bounds"
    print(f"\n== concurrency stress (public API, 6 writers + 3 scalers, 2s): "
          f"0 errors, final weights={n._incoming_synapse_weights} == PASS")


def test_concurrency_stress_zero_lost_writes_ledger_replay():
    """Rigorous proof of 'zero silently-lost legitimate weight updates'
    under real concurrent contention -- mirrors the WaveAtlas v2/v3
    stress-test methodology (attempted-vs-found write counting,
    GL-RPT-WAVE-ATLAS-DECAY-BUILD-C1-20260707-v2/v3), adapted for a
    multiplicative operation via ledger replay instead of a simple count.

    Both writer threads and the scaling pass append a description of
    what they did to a shared ledger from INSIDE the exact same critical
    section (the SAME n._neuron_lock) that performs the real mutation --
    so the ledger's append order is GUARANTEED to match the real
    mutation order exactly (both are serialized by the one lock; a plain
    list.append() is itself GIL-atomic, and happens before the lock is
    released). Replaying the ledger against a fresh simulated dict, in
    that order, must reproduce the real final dict exactly, key for key.
    If it doesn't, some operation's effect was lost, reordered, or
    corrupted relative to what actually happened -- a real concurrency
    bug, not a matter of interpretation.

    Also exercises dict GROWTH concurrent with the scaling pass's own
    iteration (a fraction of writer ops target brand-new keys never seen
    before) -- the literal WaveAtlas v2 crash scenario ("dictionary
    changed size during iteration"). Structurally, this should be
    impossible here (the scaling pass holds the lock for its entire
    snapshot-then-mutate critical section, so no writer can insert a key
    while it's iterating) -- this test is what turns that "should be"
    into a measured "is, under real contention."
    """
    n = _make_bare_neuron("stress_ledger")
    n_keys = 5
    for i in range(n_keys):
        n._incoming_synapse_weights[f"src{i}"] = STDP_DEFAULT_SYNAPSE_WEIGHT

    ledger = []  # [('add', key, delta) | ('sub', key, delta) | ('scale', factor), ...]
    errors = []
    N_OPS_PER_WRITER = 400
    CEILING = 0.3  # low relative to n_keys*MAX_SYNAPSE_WEIGHT so scaling triggers often

    def writer(seed):
        rng = random.Random(seed)
        for op_i in range(N_OPS_PER_WRITER):
            if rng.random() < 0.10:
                key = f"new_{seed}_{op_i}"  # brand-new key -> grows the dict
            else:
                key = f"src{rng.randrange(n_keys)}"
            delta = rng.uniform(0.001, 0.05)
            is_add = rng.random() < 0.5
            try:
                with n._neuron_lock:
                    current = n._incoming_synapse_weights.get(key, STDP_DEFAULT_SYNAPSE_WEIGHT)
                    if is_add:
                        n._incoming_synapse_weights[key] = min(current + delta, MAX_SYNAPSE_WEIGHT)
                        ledger.append(('add', key, delta))
                    else:
                        n._incoming_synapse_weights[key] = max(current - delta, MIN_SYNAPSE_WEIGHT)
                        ledger.append(('sub', key, delta))
            except Exception as e:
                errors.append(e)

    stop = threading.Event()

    def scaler():
        # Runs continuously for the FULL duration of the writer phase
        # (stop is only set after every writer has finished), rather than
        # a fixed call count -- a fixed count can race ahead and exhaust
        # itself early, understating real contention. Cheap per-call, so
        # this just spins tightly the whole time, maximizing interleaving
        # with the writers for the strongest possible contention proof.
        while not stop.is_set():
            try:
                with n._neuron_lock:
                    factor = n._homeostatic_scale_locked(CEILING)
                    if factor is not None:
                        ledger.append(('scale', factor))
            except Exception as e:
                errors.append(e)

    writer_threads = [threading.Thread(target=writer, args=(i,)) for i in range(8)]
    scaler_threads = [threading.Thread(target=scaler) for _ in range(4)]
    for t in scaler_threads:
        t.start()
    for t in writer_threads:
        t.start()
    for t in writer_threads:
        t.join(timeout=60.0)
        assert not t.is_alive(), "a writer thread did not finish -- possible deadlock"
    stop.set()
    for t in scaler_threads:
        t.join(timeout=10.0)
        assert not t.is_alive(), "a scaler thread did not finish -- possible deadlock"

    assert not errors, f"expected zero exceptions, got {len(errors)}: {errors[:3]}"

    # Replay the ledger, in recorded order, against a fresh simulated dict
    # that starts in the exact same state the real neuron did.
    sim = {f"src{i}": STDP_DEFAULT_SYNAPSE_WEIGHT for i in range(n_keys)}
    for op in ledger:
        if op[0] == 'add':
            _, key, delta = op
            current = sim.get(key, STDP_DEFAULT_SYNAPSE_WEIGHT)
            sim[key] = min(current + delta, MAX_SYNAPSE_WEIGHT)
        elif op[0] == 'sub':
            _, key, delta = op
            current = sim.get(key, STDP_DEFAULT_SYNAPSE_WEIGHT)
            sim[key] = max(current - delta, MIN_SYNAPSE_WEIGHT)
        elif op[0] == 'scale':
            _, factor = op
            for k in list(sim.keys()):
                sim[k] = sim[k] * factor

    real_final = dict(n._incoming_synapse_weights)
    assert set(sim.keys()) == set(real_final.keys()), (
        f"key sets diverged between ledger replay and real state -- "
        f"sim_only={set(sim.keys()) - set(real_final.keys())}, "
        f"real_only={set(real_final.keys()) - set(sim.keys())}"
    )
    n_mismatches = 0
    for k in real_final:
        if sim[k] != pytest.approx(real_final[k], abs=1e-9):
            n_mismatches += 1
    assert n_mismatches == 0, (
        f"{n_mismatches} key(s) diverged between ledger replay and real final "
        f"state -- a write was lost, reordered, or corrupted under concurrent load"
    )

    n_scales = sum(1 for op in ledger if op[0] == 'scale')
    n_writes = len(ledger) - n_scales
    assert n_scales > 0, (
        "sanity: expected at least one real rescale to have triggered under "
        "this ceiling/contention -- if zero, this test isn't exercising the "
        "interaction it claims to"
    )
    print(f"\n== concurrency stress (ledger replay): {n_writes} writes + "
          f"{n_scales} real rescales = {len(ledger)} total ops, "
          f"0 lost/reordered/corrupted writes, 0 errors, "
          f"{len(real_final)} final keys == PASS")


# ---------------------------------------------------------------------------
# (d) kill switch OFF (shipped default) -> zero behavior change;
#     zero lines touched in gualaloom_v5_engine.py
# ---------------------------------------------------------------------------

def test_kill_switch_off_by_default_zero_behavior_change():
    """HOMEOSTATIC_SCALING_ENABLED unset (or '0') is the current, shipped
    default. Given a REAL Embryo, with every neuron in one hemisphere
    artificially over-saturated first, weights must be byte-identical
    before and after driving remember() past several
    REFLECTION_SNAPSHOT_INTERVAL boundaries with the switch off."""
    assert os.environ.get("HOMEOSTATIC_SCALING_ENABLED") in (None, "0"), (
        "test assumes the shipped default (unset or '0') -- if this "
        "fails, something else in this process turned the switch on"
    )
    emb = Embryo(brain_seed=42, seed_size=4, observable="event_count")
    target_neurons = emb.hemi_by_op["sc"].cluster.neurons
    for n in target_neurons:
        for j in range(5):
            n._incoming_synapse_weights[f"fake_src{j}"] = MAX_SYNAPSE_WEIGHT
    before = {n.neuron_id: dict(n._incoming_synapse_weights) for n in target_neurons}

    n_words = emb.REFLECTION_SNAPSHOT_INTERVAL * 3 + 1
    for i in range(n_words):
        emb.remember(f"w{i}", _signals(i, f"w{i}"))

    after = {n.neuron_id: dict(n._incoming_synapse_weights) for n in target_neurons}
    assert after == before, (
        "weights changed with HOMEOSTATIC_SCALING_ENABLED off -- the kill "
        "switch is not actually inert"
    )
    print(f"\n== kill switch OFF (shipped default): zero behavior change across "
          f"{n_words} real remember() calls, 3 interval boundaries crossed == PASS")


def test_kill_switch_on_actually_engages():
    """Sanity check that the switch is a REAL gate, not decorative --
    with it explicitly turned on (test-process-local env var only, never
    touches production config/deploy), the same over-saturated setup
    DOES get rescaled once an interval boundary is crossed."""
    old = os.environ.get("HOMEOSTATIC_SCALING_ENABLED")
    os.environ["HOMEOSTATIC_SCALING_ENABLED"] = "1"
    try:
        emb = Embryo(brain_seed=43, seed_size=4, observable="event_count")
        target_neurons = emb.hemi_by_op["sc"].cluster.neurons
        for n in target_neurons:
            for j in range(5):
                n._incoming_synapse_weights[f"fake_src{j}"] = MAX_SYNAPSE_WEIGHT
        for i in range(emb.REFLECTION_SNAPSHOT_INTERVAL):
            emb.remember(f"w{i}", _signals(i, f"w{i}"))
        assert emb.tick == emb.REFLECTION_SNAPSHOT_INTERVAL  # exactly one boundary crossed

        for n in target_neurons:
            total = sum(n._incoming_synapse_weights.values())
            assert total <= HOMEOSTATIC_SCALING_CEILING + 1e-6, (
                f"{n.neuron_id}: total={total} still over ceiling after switch-on pass"
            )
    finally:
        if old is None:
            os.environ.pop("HOMEOSTATIC_SCALING_ENABLED", None)
        else:
            os.environ["HOMEOSTATIC_SCALING_ENABLED"] = old
    print("\n== kill switch ON (test-process-local only): over-saturated neurons "
          "rescaled at the interval boundary == PASS")


if __name__ == "__main__":
    test_never_increases_any_weight_random_distributions()
    test_never_increases_edge_cases()
    test_rescales_oversaturated_neuron_back_under_ceiling_preserving_proportions()
    test_zero_or_negative_ceiling_is_a_safe_noop()
    test_rescale_respects_custom_ceiling_argument()
    test_repeated_calls_converge_and_stay_stable()
    test_concurrency_stress_public_api_zero_crashes_and_bounded()
    test_concurrency_stress_zero_lost_writes_ledger_replay()
    test_kill_switch_off_by_default_zero_behavior_change()
    test_kill_switch_on_actually_engages()
    print("\nALL PASS: test_homeostatic_scaling")
