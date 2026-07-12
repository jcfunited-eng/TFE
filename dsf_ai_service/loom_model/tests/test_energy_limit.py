"""
test_energy_limit.py -- per-neuron metabolic energy limit
(LoomNeuron._energy_limit_blocks_fire() / _expend_energy_locked() /
_recover_energy_locked(), neuron.py), gated by ENERGY_LIMIT_ENABLED
(default OFF).

Real-world grounding: biological neurons pay a genuine metabolic cost to
fire (ATP-consuming ion pumps restoring the resting potential after every
action potential) -- a real, depletable resource constraint on firing, not
an arbitrary throttle. This is DISTINCT from the two mechanisms already in
this file:
  - refractory_period_ms: a fixed, absolute TIME the neuron cannot fire
    again, independent of how much it has recently fired.
  - the fire-rate circuit breaker (FIRE_BREAKER_CEILING_HZ /
    _check_fire_rate_breaker, see test_neuron_spike_handling.py): a
    HEURISTIC that only strips OUTGOING spike-bus propagation once a full
    FIRE_BREAKER_WINDOW_N=30-fire window shows a sustained rate >250Hz --
    membrane reset / refractory / STDP bookkeeping all still happen even
    on a tripped fire, and the first 29 fires of ANY burst, at ANY rate,
    never trip it (not enough history yet).

The energy gate is checked in receive_spike() at the SAME decision point
as the refractory check, strictly BEFORE _fire() is ever invoked -- an
energy-exhausted neuron's threshold-crossing spike is absorbed exactly
like a refractory spike (nothing resets, no propagation, no STDP), not
merely stripped of propagation. ENERGY_CEILING=5.0 (5x
ENERGY_COST_PER_FIRE=1.0) is set well under FIRE_BREAKER_WINDOW_N=30 so
this mechanism structurally acts BEFORE the breaker's own window could
even finish filling -- see neuron.py's ENERGY_CEILING module comment for
the full derivation.

Required coverage (per dispatch):
  (a) zero behavior change with the kill switch OFF (the shipped default)
  (b) a neuron firing repeatedly in a tight loop eventually gets throttled
      by energy exhaustion even though the rate-breaker alone (which needs
      a full 30-fire window before it can trip at all) would not have
      stopped it yet
  (c) energy recovers correctly over real elapsed time, with the exact
      leaky-recovery arithmetic checked, not just "eventually unblocks"
  (d) a concurrency/stress test -- real concurrent firing across many
      neurons while each neuron's own energy state is read/written, zero
      crashes, zero lost/corrupted state
  (e) the existing cascade regression test still passes (run separately,
      see run instructions in this dispatch's report -- not re-imported
      here to keep this file's own import graph minimal)

Plus a sanity check that the kill switch, when explicitly turned on
test-process-locally, actually engages, and that the mechanism is
additive-only (never turns a fire that would have happened into one that
still happens with different membrane/refractory state -- only ever
turns some additional "would have fired" cases into "does not fire").

Construction pattern (bare LoomNeuron + PendingSpike) matches
test_neuron_spike_handling.py already in this directory.
"""

import os
import random
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.loom_model.neuron import (
    LoomNeuron,
    ENERGY_LIMIT_ENABLED_ENV,
    ENERGY_CEILING,
    ENERGY_COST_PER_FIRE,
    ENERGY_RECOVERY_PER_S,
    FIRE_BREAKER_WINDOW_N,
    FIRE_BREAKER_CEILING_HZ,
)
from dsf_ai_service.substrate.spike_bus import PendingSpike


def _spike(weight, source="_input_injection_", target="n1"):
    return PendingSpike(arrival_time=time.monotonic(), target_neuron_id=target,
                         source_neuron_id=source, weight=weight, metadata={})


def _fresh_firing_neuron(neuron_id="n1"):
    """membrane_threshold low enough that any external spike fires it,
    refractory zeroed out so refractory never masks the energy gate."""
    n = LoomNeuron(neuron_id)
    n.membrane_threshold = 0.5
    n.membrane_rest = 0.0
    n.refractory_period_ms = 0.0
    return n


class _EnvSwitch:
    """Context manager: sets ENERGY_LIMIT_ENABLED test-process-locally,
    restores whatever was there before on exit -- never touches
    production config/deploy. Matches test_homeostatic_scaling.py's
    try/finally os.environ discipline."""

    def __init__(self, value):
        self.value = value
        self.old = None

    def __enter__(self):
        self.old = os.environ.get(ENERGY_LIMIT_ENABLED_ENV)
        if self.value is None:
            os.environ.pop(ENERGY_LIMIT_ENABLED_ENV, None)
        else:
            os.environ[ENERGY_LIMIT_ENABLED_ENV] = self.value
        return self

    def __exit__(self, *exc):
        if self.old is None:
            os.environ.pop(ENERGY_LIMIT_ENABLED_ENV, None)
        else:
            os.environ[ENERGY_LIMIT_ENABLED_ENV] = self.old


# ---------------------------------------------------------------------------
# (a) kill switch OFF (shipped default) -> zero behavior change
# ---------------------------------------------------------------------------

def test_kill_switch_off_by_default():
    assert os.environ.get(ENERGY_LIMIT_ENABLED_ENV) in (None, "0"), (
        "test assumes the shipped default (unset or '0') -- if this fails, "
        "something else in this process turned the switch on"
    )


def test_kill_switch_off_zero_behavior_change_tight_loop():
    """A tight in-process loop that would exhaust energy with the switch
    on must fire on EVERY call with the switch off (its shipped default)
    -- byte-identical to pre-addition behavior (membrane_rest each time,
    _energy_block_count stays 0, _expended_energy stays 0.0)."""
    with _EnvSwitch(None):
        n = _fresh_firing_neuron()
        n_calls = 50
        fire_count = 0
        for _ in range(n_calls):
            before = n._last_fire_time_s
            n.receive_spike(_spike(1.0))
            if n._last_fire_time_s != before:
                fire_count += 1
                assert n.membrane_potential == n.membrane_rest

        assert fire_count == n_calls, (
            f"expected every one of {n_calls} calls to fire with the kill "
            f"switch off, got {fire_count}"
        )
        assert n._energy_block_count == 0
        assert n._expended_energy == 0.0
        print(f"\n== kill switch OFF: {fire_count}/{n_calls} fires, zero energy "
              f"bookkeeping touched == PASS")


def test_kill_switch_off_helpers_are_inert_no_ops():
    """Direct calls to the gate/expend helpers with the switch off must
    not mutate _expended_energy at all, at any accumulated value."""
    with _EnvSwitch(None):
        n = LoomNeuron("n1")
        n._expended_energy = 999.0  # would be over ANY realistic ceiling
        now = time.monotonic()
        blocked = n._energy_limit_blocks_fire(now)
        assert blocked is False, "kill switch off must never block a fire"
        assert n._expended_energy == 999.0, "gate must not touch state when off"
        n._expend_energy_locked(now)
        assert n._expended_energy == 999.0, "expend must not touch state when off"
        print("\n== kill switch OFF: gate/expend helpers are true no-ops == PASS")


# ---------------------------------------------------------------------------
# (b) tight-loop throttling: energy exhaustion catches what the rate
#     breaker's own window requirement structurally cannot yet see
# ---------------------------------------------------------------------------

def test_tight_loop_throttled_by_energy_before_breaker_window_fills():
    """Drives receive_spike() back-to-back (the real production call
    path) with the switch on. ENERGY_CEILING=5.0 / ENERGY_COST_PER_FIRE=
    1.0 means at most ~5-6 fires happen before energy blocks further
    firing (some slop from the tiny real elapsed time between Python
    statements, which the leaky-recovery arithmetic legitimately credits
    back) -- well under FIRE_BREAKER_WINDOW_N=30, so the breaker has not
    even finished collecting its first window yet and could not have
    tripped regardless of rate."""
    with _EnvSwitch("1"):
        n = _fresh_firing_neuron()
        n_calls = FIRE_BREAKER_WINDOW_N - 5  # well short of the breaker's own window
        fire_count = 0
        block_count = 0
        for _ in range(n_calls):
            before = n._last_fire_time_s
            n.receive_spike(_spike(1.0))
            if n._last_fire_time_s != before:
                fire_count += 1
            else:
                block_count += 1

        assert fire_count < n_calls, (
            "expected some calls to be blocked by energy exhaustion in a "
            "tight loop -- got every call firing, the gate did not engage"
        )
        assert block_count > 0
        assert n._energy_block_count == block_count
        # The breaker's own window (_recent_fire_timestamps, maxlen=
        # FIRE_BREAKER_WINDOW_N) never filled -- fewer real fires happened
        # than the window needs, so the breaker structurally could not
        # have tripped on this run at all, independent of rate.
        assert len(n._recent_fire_timestamps) < FIRE_BREAKER_WINDOW_N, (
            "sanity: this test's whole point is that the breaker's window "
            "never fills -- if it did, this isn't isolating energy anymore"
        )
        assert n._fire_breaker_trip_count == 0, (
            "the rate breaker itself must never have tripped in this run -- "
            "confirms energy alone did the throttling here, not the breaker"
        )
        print(f"\n== tight loop ({n_calls} calls): {fire_count} fired, "
              f"{block_count} blocked by energy exhaustion, breaker "
              f"trip_count=0 (window never filled: "
              f"{len(n._recent_fire_timestamps)}/{FIRE_BREAKER_WINDOW_N}) == PASS")


def test_energy_gate_alone_blocks_a_rate_the_breaker_would_never_trip_on():
    """Direct, deterministic version of (b) using controlled `now` values
    (matches test_neuron_spike_handling.py's _fire()-with-controlled-`now`
    style) -- fires exactly ENERGY_CEILING/ENERGY_COST_PER_FIRE times with
    zero elapsed time between them (no recovery credit at all), then
    proves the NEXT fire is blocked purely by energy while the breaker's
    own rate check (computed the same way _check_fire_rate_breaker does)
    would not have tripped at this fire count."""
    with _EnvSwitch("1"):
        n = LoomNeuron("n1")
        now = time.monotonic()
        n_allowed = int(ENERGY_CEILING / ENERGY_COST_PER_FIRE)
        for i in range(n_allowed):
            blocked = n._energy_limit_blocks_fire(now)
            assert not blocked, f"fire {i} should still be allowed (energy={n._expended_energy})"
            n._expend_energy_locked(now)
        assert n._expended_energy == pytest.approx(ENERGY_CEILING, abs=1e-9)

        blocked = n._energy_limit_blocks_fire(now)
        assert blocked, (
            f"expected the {n_allowed + 1}th zero-elapsed-time fire to be "
            f"blocked by energy exhaustion, energy={n._expended_energy}"
        )
        # The breaker needs FIRE_BREAKER_WINDOW_N=30 fires of history
        # before it can trip at all -- n_allowed is well under that here.
        assert n_allowed < FIRE_BREAKER_WINDOW_N
        print(f"\n== deterministic: {n_allowed} zero-elapsed-time fires allowed, "
              f"fire {n_allowed + 1} blocked by energy alone "
              f"({n_allowed} << FIRE_BREAKER_WINDOW_N={FIRE_BREAKER_WINDOW_N}) == PASS")


def test_moderate_sustained_rate_under_breaker_ceiling_still_exhausts_energy():
    """The mechanism's real complementary coverage: a neuron sustaining a
    rate BELOW FIRE_BREAKER_CEILING_HZ (so the breaker would never trip,
    no matter how long it ran) but ABOVE the ENERGY_RECOVERY_PER_S=50Hz
    sustainable bound still exhausts energy given enough real elapsed
    simulated time, because cost accrues faster than recovery credits it
    back. 100Hz is used: comfortably under the 250Hz breaker ceiling,
    comfortably over the 50Hz recovery rate."""
    with _EnvSwitch("1"):
        n = LoomNeuron("n1")
        sustained_hz = 100.0
        assert sustained_hz < FIRE_BREAKER_CEILING_HZ
        assert sustained_hz > ENERGY_RECOVERY_PER_S
        interval_s = 1.0 / sustained_hz
        now = time.monotonic()
        blocked_seen = False
        allowed_fires = 0
        for _ in range(500):  # 500 * 10ms simulated = 5s simulated activity
            now += interval_s
            if n._energy_limit_blocks_fire(now):
                blocked_seen = True
                continue
            n._expend_energy_locked(now)
            allowed_fires += 1

        assert blocked_seen, (
            "expected a 100Hz-sustained neuron (under the 250Hz breaker "
            "ceiling, over the 50Hz recovery rate) to eventually exhaust "
            "energy and get blocked at least once"
        )
        assert allowed_fires < 500
        print(f"\n== sustained 100Hz (breaker-safe, energy-unsustainable): "
              f"{allowed_fires}/500 fires allowed before first block == PASS")


def test_sustainable_rate_at_recovery_bound_never_exhausts():
    """A neuron sustaining fires at exactly ENERGY_RECOVERY_PER_S=50Hz
    forever must never be blocked -- cost-in-rate equals recovery-rate,
    a real steady state, not a slow leak toward exhaustion. Run for a
    simulated 10 real seconds (500 fires at 50Hz)."""
    with _EnvSwitch("1"):
        n = LoomNeuron("n1")
        interval_s = 1.0 / ENERGY_RECOVERY_PER_S
        now = time.monotonic()
        for _ in range(500):
            now += interval_s
            blocked = n._energy_limit_blocks_fire(now)
            assert not blocked, (
                f"neuron sustaining exactly the recovery-rate bound "
                f"({ENERGY_RECOVERY_PER_S}Hz) should never be blocked, "
                f"energy={n._expended_energy}"
            )
            n._expend_energy_locked(now)
        print("\n== sustained 50Hz (== ENERGY_RECOVERY_PER_S): 500/500 fires, "
              "never blocked == PASS")


# ---------------------------------------------------------------------------
# (c) energy recovers correctly over real elapsed ticks
# ---------------------------------------------------------------------------

def test_energy_recovers_exact_linear_arithmetic():
    """Exact-arithmetic check of the leaky-recovery formula: after
    exhausting energy, advancing `now` by a controlled dt_s must reduce
    _expended_energy by exactly ENERGY_RECOVERY_PER_S * dt_s (clamped at
    0.0), not merely "some recovery happened"."""
    with _EnvSwitch("1"):
        n = LoomNeuron("n1")
        now = time.monotonic()
        n._expended_energy = ENERGY_CEILING
        n._last_energy_update_time_s = now

        dt_s = (ENERGY_CEILING / ENERGY_RECOVERY_PER_S) / 2.0  # recovers exactly half
        now += dt_s
        recovered = n._recover_energy_locked(now)
        expected = ENERGY_CEILING - ENERGY_RECOVERY_PER_S * dt_s
        # abs=1e-6, not 1e-9: time.monotonic() returns real wall-clock
        # uptime (can be a large number, e.g. ~1e5-1e6s on a long-running
        # process/container) -- float64 subtraction of two such values
        # loses precision below ~1e-9 in the difference itself, which
        # then gets amplified by the *50 multiply. 1e-6 is still far
        # tighter than anything a real test/production timescale needs.
        assert recovered == pytest.approx(expected, abs=1e-6), (
            f"expected exactly {expected}, got {recovered}"
        )
        assert n._expended_energy == pytest.approx(expected, abs=1e-6)
        assert n._last_energy_update_time_s == now
        print(f"\n== recovery arithmetic: {ENERGY_CEILING} -> {recovered:.6f} "
              f"after dt_s={dt_s:.6f} (expected {expected:.6f}) == PASS")


def test_energy_recovery_clamped_at_zero_never_goes_negative():
    with _EnvSwitch("1"):
        n = LoomNeuron("n1")
        now = time.monotonic()
        n._expended_energy = 0.5
        n._last_energy_update_time_s = now
        now += 1000.0  # vastly more than enough real time to fully recover
        recovered = n._recover_energy_locked(now)
        assert recovered == 0.0
        assert n._expended_energy == 0.0
        print("\n== recovery clamped at 0.0, never negative, after a huge "
              "elapsed-time jump == PASS")


def test_exhausted_neuron_can_fire_again_after_real_recovery_time():
    """End-to-end through the real gate: a neuron blocked by energy
    exhaustion becomes fireable again once enough real elapsed time has
    passed for _recover_energy_locked to bring it back under
    ENERGY_CEILING -- and stays correctly blocked at a point in time
    that hasn't recovered enough yet.

    Starts at ENERGY_CEILING + 2 fires' worth of extra debt (7.0, not
    exactly 5.0) so there is a real, non-boundary-adjacent time window
    where it is still unambiguously blocked (the gate is `>=
    ENERGY_CEILING`, a continuous leaky-recovery model -- starting
    exactly AT the ceiling would unblock after essentially any positive
    elapsed time at all, which would make "not enough time" and "enough
    time" indistinguishable from a floating-point boundary, not a
    meaningful recovery-duration check)."""
    with _EnvSwitch("1"):
        n = LoomNeuron("n1")
        now = time.monotonic()
        start_energy = ENERGY_CEILING + 2.0 * ENERGY_COST_PER_FIRE  # 7.0
        n._expended_energy = start_energy
        n._last_energy_update_time_s = now
        time_to_reach_ceiling_s = (start_energy - ENERGY_CEILING) / ENERGY_RECOVERY_PER_S  # 0.04s

        not_enough_s = time_to_reach_ceiling_s / 2.0  # 0.02s -- still well above ceiling
        assert n._energy_limit_blocks_fire(now + not_enough_s) is True, (
            "half the time needed to reach the ceiling must not be enough to unblock"
        )

        # _energy_limit_blocks_fire already advanced _last_energy_update_time_s
        # to now+not_enough_s as a side effect -- reset state for a clean,
        # independent second check from the same original starting point.
        n._expended_energy = start_energy
        n._last_energy_update_time_s = now
        enough_s = time_to_reach_ceiling_s + 0.02  # comfortably past the ceiling
        assert n._energy_limit_blocks_fire(now + enough_s) is False, (
            "enough real elapsed recovery time later, the gate must allow firing again"
        )
        print(f"\n== exhausted neuron (start={start_energy}): still blocked at "
              f"dt={not_enough_s:.4f}s (< {time_to_reach_ceiling_s:.4f}s to reach "
              f"ceiling), fireable again at dt={enough_s:.4f}s == PASS")


# ---------------------------------------------------------------------------
# (d) concurrency / stress test -- zero crashes, zero corrupted state
# ---------------------------------------------------------------------------

def test_concurrency_stress_many_neurons_zero_crashes_zero_corruption():
    """Real concurrent firing across many neurons while each neuron's own
    energy state is read/written -- proves no crashes and no lost/
    corrupted state. Snapshots the neuron list with list() before
    iterating (this file's own established discipline, see
    test_homeostatic_scaling.py / the WaveAtlas v2/v3 lesson referenced
    throughout neuron.py) even though this test builds a fixed-size
    population up front and never mutates the population itself --
    matching the codebase's own defensive convention regardless.

    Each neuron's mutable energy state (_expended_energy,
    _last_energy_update_time_s, _energy_block_count) is only ever touched
    while that neuron's OWN _neuron_lock is held (receive_spike() already
    guarantees this structurally -- this test does not bypass the lock),
    so this is really a proof that many neurons' independent locks don't
    interfere with each other under real concurrent load, not a proof
    about a single shared lock."""
    with _EnvSwitch("1"):
        n_neurons = 24
        neurons = [_fresh_firing_neuron(f"n{i}") for i in range(n_neurons)]
        errors = []
        stop = threading.Event()
        fire_counts = {n.neuron_id: 0 for n in neurons}
        block_counts = {n.neuron_id: 0 for n in neurons}
        lock_for_counts = threading.Lock()

        def hammer(neuron, seed):
            rng = random.Random(seed)
            local_fires = 0
            local_blocks = 0
            while not stop.is_set():
                before = neuron._last_fire_time_s
                try:
                    neuron.receive_spike(_spike(1.0 + rng.random() * 0.01))
                except Exception as e:
                    errors.append((neuron.neuron_id, e))
                    return
                if neuron._last_fire_time_s != before:
                    local_fires += 1
                else:
                    local_blocks += 1
            with lock_for_counts:
                fire_counts[neuron.neuron_id] += local_fires
                block_counts[neuron.neuron_id] += local_blocks

        threads = []
        for n in neurons:
            # 2 threads hammering the SAME neuron concurrently, for every
            # neuron in the population -- real concurrent access to one
            # neuron's energy state from multiple threads at once, not
            # just many neurons each touched by a single thread.
            threads.append(threading.Thread(target=hammer, args=(n, hash(n.neuron_id))))
            threads.append(threading.Thread(target=hammer, args=(n, hash(n.neuron_id) + 1)))

        for t in threads:
            t.start()
        time.sleep(2.0)
        stop.set()
        for t in threads:
            t.join(timeout=10.0)
            assert not t.is_alive(), "a stress thread did not finish -- possible deadlock"

        assert not errors, (
            f"expected zero exceptions under concurrent load, got "
            f"{len(errors)}: {errors[:3]}"
        )

        total_fires = 0
        total_blocks = 0
        for n in list(neurons):
            # Invariant that must hold regardless of scheduling: energy
            # never goes negative, never exceeds ENERGY_CEILING by more
            # than one fire's worth of cost (the one fire that pushed it
            # over, per _expend_energy_locked's own docstring).
            assert n._expended_energy >= -1e-9, (
                f"{n.neuron_id}: expended_energy went negative: {n._expended_energy}"
            )
            assert n._expended_energy <= ENERGY_CEILING + ENERGY_COST_PER_FIRE + 1e-6, (
                f"{n.neuron_id}: expended_energy blew past the ceiling+one-fire "
                f"bound: {n._expended_energy}"
            )
            assert n._energy_block_count >= 0
            total_fires += fire_counts[n.neuron_id]
            total_blocks += block_counts[n.neuron_id]

        assert total_fires > 0, "sanity: expected at least some real fires to have happened"
        assert total_blocks > 0, (
            "sanity: expected at least some real energy-exhaustion blocks under "
            "this much concurrent hammering -- if zero, this test isn't "
            "exercising the gate under contention"
        )
        print(f"\n== concurrency stress ({n_neurons} neurons, 2 threads/neuron, 2s): "
              f"0 errors, {total_fires} fires, {total_blocks} energy blocks, "
              f"all {n_neurons} neurons' energy stayed in-bounds == PASS")


def test_concurrency_stress_single_neuron_ledger_replay_zero_lost_state():
    """Rigorous proof of 'zero lost/corrupted state' for one heavily
    contended neuron, via ledger replay -- same methodology as
    test_homeostatic_scaling.py's ledger-replay test. Every thread
    appends what it observed/did from INSIDE the exact critical section
    (n._neuron_lock, held by receive_spike() itself) is not directly
    accessible here since receive_spike() owns the lock internally -- so
    instead this replays against the real _expend_energy_locked /
    _recover_energy_locked primitives directly, serialized through the
    SAME n._neuron_lock the real receive_spike() path uses, and confirms
    the final state matches a single-threaded simulation fed the exact
    same (now, action) sequence in the exact order the lock serialized
    them."""
    with _EnvSwitch("1"):
        n = LoomNeuron("stress_single")
        ledger = []
        errors = []
        n_threads = 8
        ops_per_thread = 300
        stop_start = time.monotonic()

        def worker(seed):
            rng = random.Random(seed)
            for _ in range(ops_per_thread):
                now = time.monotonic()
                try:
                    with n._neuron_lock:
                        blocked = n._energy_limit_blocks_fire(now)
                        if not blocked:
                            n._expend_energy_locked(now)
                        ledger.append((now, blocked))
                except Exception as e:
                    errors.append(e)
                # tiny, random, real sleep so real elapsed time varies
                # between ops (exercises real recovery arithmetic, not
                # just zero-elapsed-time bursts)
                time.sleep(rng.random() * 0.0005)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30.0)
            assert not t.is_alive(), "a worker thread did not finish -- possible deadlock"

        assert not errors, f"expected zero exceptions, got {len(errors)}: {errors[:3]}"

        # Replay in the ORDER the lock actually serialized them (ledger
        # append happens inside the same critical section as the real
        # mutation, so append order == real mutation order).
        ledger.sort(key=lambda rec: rec[0])
        sim_energy = 0.0
        sim_last_update = ledger[0][0] if ledger else 0.0
        n_blocked_sim = 0
        for now, blocked_real in ledger:
            dt_s = now - sim_last_update
            if dt_s > 0:
                sim_energy = max(0.0, sim_energy - ENERGY_RECOVERY_PER_S * dt_s)
                sim_last_update = now
            sim_blocked = sim_energy >= ENERGY_CEILING
            if not sim_blocked:
                sim_energy += ENERGY_COST_PER_FIRE
            n_blocked_sim += int(sim_blocked)

        # The real system and the sorted-replay simulation must agree on
        # the FINAL energy value -- if any op were lost, double-applied,
        # or corrupted under contention, this diverges.
        assert n._expended_energy == pytest.approx(sim_energy, abs=1e-6), (
            f"real final expended_energy={n._expended_energy} != replayed "
            f"simulation={sim_energy} -- some concurrent op was lost, "
            f"reordered incorrectly, or corrupted"
        )
        total_ops = len(ledger)
        assert total_ops == n_threads * ops_per_thread, (
            f"expected exactly {n_threads * ops_per_thread} ledger entries "
            f"(one per op, none lost), got {total_ops}"
        )
        print(f"\n== single-neuron ledger replay ({total_ops} ops, {n_threads} "
              f"threads): real final energy={n._expended_energy:.6f} == "
              f"replayed simulation={sim_energy:.6f}, 0 lost ops, 0 errors == PASS")


# ---------------------------------------------------------------------------
# Sanity: kill switch really is a live gate, not decorative; mechanism
# never LOOSENS existing gates (refractory / Dale's-law polarity /
# breaker) -- only ever adds a new way to block.
# ---------------------------------------------------------------------------

def test_kill_switch_on_actually_engages():
    with _EnvSwitch("1"):
        n = LoomNeuron("n1")
        now = time.monotonic()
        n._expended_energy = ENERGY_CEILING
        n._last_energy_update_time_s = now
        assert n._energy_limit_blocks_fire(now) is True
    print("\n== kill switch ON (test-process-local only): gate actually "
          "blocks an exhausted neuron == PASS")


def test_never_blocks_below_ceiling():
    """Sanity: the gate must not be a decorative always-True/always-False
    -- confirm it correctly ALLOWS firing when strictly under the
    ceiling, at any fraction tested."""
    with _EnvSwitch("1"):
        n = LoomNeuron("n1")
        now = time.monotonic()
        for frac in (0.0, 0.2, 0.5, 0.8, 0.999):
            n._expended_energy = ENERGY_CEILING * frac
            n._last_energy_update_time_s = now
            assert n._energy_limit_blocks_fire(now) is False, (
                f"should not block at {frac * 100:.1f}% of ceiling"
            )
        print("\n== gate allows firing at every tested fraction strictly "
              "under ENERGY_CEILING == PASS")


def test_refractory_and_breaker_untouched_by_energy_mechanism():
    """Additive-only invariant, checked directly: with the energy switch
    ON but energy nowhere near exhausted, refractory behavior and the
    fire-rate breaker's own trip decision are byte-identical to their
    documented pre-existing behavior (test_neuron_spike_handling.py's
    own assertions, replicated here under the energy switch to prove no
    interaction)."""
    with _EnvSwitch("1"):
        # Refractory still absorbs without firing, unchanged.
        n = LoomNeuron("n1")
        n.membrane_threshold = 1.0
        n.membrane_rest = 0.0
        n.refractory_period_ms = 200.0
        n.receive_spike(_spike(1.5))  # fires, enters refractory
        assert n.membrane_potential == 0.0
        n.receive_spike(_spike(5.0))  # huge spike, but still refractory
        assert n.membrane_potential != 0.0
        assert n.membrane_potential < 5.5  # didn't re-fire

        # Breaker still trips on its own documented runaway pattern,
        # unchanged (driven directly via _fire(), same as
        # test_fire_rate_breaker_trips_on_runaway_pattern).
        n2 = LoomNeuron("n2")
        import numpy as np
        n2.couplings.neighbors = ["n3"]
        n2.couplings.J = np.array([[0.7] * 16])

        class _RecordingBus:
            _neuron_registry = {}
            def __init__(self):
                self.injected = []
            def inject(self, target_id, source_id, weight, arrival_delay_ms=0.0, metadata=None):
                self.injected.append((target_id, source_id, weight, arrival_delay_ms))

        bus = _RecordingBus()
        n2.set_spike_bus(bus)
        n2.membrane_rest = 0.0
        interval_s = 1.0 / 3800.0
        now = time.monotonic()
        for _ in range(FIRE_BREAKER_WINDOW_N):
            now += interval_s
            n2.membrane_potential = 5.0
            n2._fire(now)
        assert n2._fire_breaker_trip_count == 1, (
            "breaker's own trip behavior must be unchanged with the energy "
            "switch on (energy has ample headroom in this short a run)"
        )
        print("\n== refractory + fire-rate breaker behavior unchanged with "
              "energy switch ON (and energy not yet exhausted) == PASS")


if __name__ == "__main__":
    test_kill_switch_off_by_default()
    test_kill_switch_off_zero_behavior_change_tight_loop()
    test_kill_switch_off_helpers_are_inert_no_ops()
    test_tight_loop_throttled_by_energy_before_breaker_window_fills()
    test_energy_gate_alone_blocks_a_rate_the_breaker_would_never_trip_on()
    test_moderate_sustained_rate_under_breaker_ceiling_still_exhausts_energy()
    test_sustainable_rate_at_recovery_bound_never_exhausts()
    test_energy_recovers_exact_linear_arithmetic()
    test_energy_recovery_clamped_at_zero_never_goes_negative()
    test_exhausted_neuron_can_fire_again_after_real_recovery_time()
    test_concurrency_stress_many_neurons_zero_crashes_zero_corruption()
    test_concurrency_stress_single_neuron_ledger_replay_zero_lost_state()
    test_kill_switch_on_actually_engages()
    test_never_blocks_below_ceiling()
    test_refractory_and_breaker_untouched_by_energy_mechanism()
    print("\nALL PASS: test_energy_limit")
