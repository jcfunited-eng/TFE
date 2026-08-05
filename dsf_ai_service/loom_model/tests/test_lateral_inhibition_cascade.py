"""
Reproduction + fix verification for the GL-RPT-PHASE-1-V2-REVIVE-C1-
20260708-v3 emergent cascade finding: with Phase 1 v2's dual-write
injection live under real traffic, spike_bus.injected_count climbed at
a sustained ~constant rate for 9 minutes while total_synapses_updated
stayed frozen at exactly 448 -- a fixed, already-potentiated subgraph
reverberating indefinitely, decoupled from further real input. 448 is
not arbitrary: it is exactly 8 hemispheres x 8 neurons x 7 intra-
hemisphere neighbors (SEED_SIZE_PER_HEMISPHERE=8, so k_neighbors=16
clamps to n_neurons-1=7 -- every hemisphere is internally a fully-
connected 8-neuron clique).

Fix under test: LoomNeuron._fire() now signs its outgoing spike weight
by self._polarity (embryo.py's existing, deterministic ~20%/80%
inhibitory/excitatory population split -- computed at seed for every
neuron from hemisphere+ring position, previously consulted only by
_organ_signature's population vote, never by the firing path). No new
heuristic constant: this connects an already-principled piece of the
substrate's own chemistry to the path that ignored it.

Verdict criterion is physical, not statistical: does the network ever
fire again after external input stops, checked in a window well past
one full round-trip delay so any legitimate in-flight echo has already
arrived -- a plain yes/no fact about the dynamical system, not a
growth-rate threshold. (An earlier version of this test compared
windowed growth rates against an arbitrary percentage -- that is a
statistics trick, not a measurement of whether the system is physically
stable, and was replaced.)

Scale matters here: an isolated single 8-neuron clique with perfectly
uniform preset weights and a perfectly uniform propagation delay hits
an exact numerical coincidence (round-trip time == refractory period)
that silences propagation regardless of polarity -- an artifact of
having no other concurrent activity on the spike bus. Real production
runs all 64 neurons across 8 hemispheres on one shared delivery thread
under real concurrent load, which breaks that exact tie. This test
therefore drives the real, full Guala() organism (real spike bus, real
concurrent multi-hemisphere activity), not an isolated clique, so any
timing coincidence has to survive real scheduling jitter to matter.
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

os.environ.setdefault("SUBSTRATE_MODE", "embedded")

from dsf_ai_service.loom_model.neuron import MAX_SYNAPSE_WEIGHT, EXTERNAL_SOURCE_PREFIX

# Physical settle time: worst case a legitimate in-flight echo could still
# be traveling. DEFAULT_DELAY_MS=1.0 dominates (chi_position unpopulated in
# Phase 1, confirmed in neuron.py), refractory_period_ms=2.0 -- a handful
# of hops is generously covered by 200ms, three orders of magnitude beyond
# any single real propagation delay.
SETTLE_AFTER_KICK_S = 0.3
QUIET_CHECK_WINDOW_S = 3.0


def _fresh_guala():
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala
    os.environ["EVENT_DRIVEN_SUBSTRATE"] = "1"
    return Guala()


def _saturate_all_intra_hemisphere_synapses(g):
    """Worst case a real loop reaches after sustained STDP potentiation,
    applied directly rather than waiting for slow organic buildup --
    every neuron's incoming weight from every OTHER neuron in its own
    hemisphere (the fully-connected intra-cluster topology) set to
    MAX_SYNAPSE_WEIGHT."""
    for hemi in g.organism.brain.hemispheres:
        ids = [n.neuron_id for n in hemi.cluster.neurons]
        for n in hemi.cluster.neurons:
            for other_id in ids:
                if other_id != n.neuron_id:
                    n._incoming_synapse_weights[other_id] = MAX_SYNAPSE_WEIGHT


def _run_kick_and_watch(force_all_excitatory: bool, disable_fire_rate_breaker: bool = False,
                         disable_energy_limit: bool = False):
    g = _fresh_guala()
    try:
        neurons = g._all_neurons()
        assert len(neurons) >= 32, "expected the real multi-hemisphere organism"

        if force_all_excitatory:
            for n in neurons:
                n._polarity = 1.0
        if disable_fire_rate_breaker:
            # 2026-07-10: FIRE_BREAKER_CEILING_HZ (neuron.py:990) shipped
            # the night after this test was written, as an independent,
            # unrelated defense-in-depth layer -- it now ALSO halts
            # runaway firing on its own, so forcing all-excitatory alone
            # no longer reproduces the original pre-fix condition this
            # test needs (confirmed directly: without this override,
            # fires_after_settle==0 even with force_all_excitatory=True,
            # because the breaker trips first). Neutralizing it here
            # isolates exactly what this test claims to measure --
            # whether polarity-based inhibition ALONE would have been
            # necessary -- without silently depending on a second,
            # unrelated mechanism to pass.
            for n in neurons:
                n._check_fire_rate_breaker = lambda now: (False, None)
        if disable_energy_limit:
            # 2026-07-12: ENERGY_LIMIT_ENABLED (eafcb95, neuron.py's
            # ENERGY_CEILING gate in receive_spike(), checked strictly
            # before _fire()) is a THIRD independent defense-in-depth
            # layer, same masking risk as FIRE_BREAKER_CEILING_HZ above --
            # confirmed directly (GL-RPT-INERT-FEATURES-GRADUATION-PLAN-
            # CODEX-20260712-v1): running this suite with
            # ENERGY_LIMIT_ENABLED=1 set makes fires_after_settle==0 even
            # with force_all_excitatory=True and the fire-rate breaker
            # already neutralized above -- ENERGY_CEILING=5.0 fires before
            # ENERGY_RECOVERY_PER_S=50.0 catches up is, by itself, now
            # enough to halt the saturated worst case. Left unneutralized,
            # this test would silently stop reproducing the bug it exists
            # to check for the moment ENERGY_LIMIT_ENABLED=1 is set
            # anywhere in the environment (e.g. a future graduation
            # deploy) -- the same false negative-control failure mode the
            # fire-rate-breaker neutralization above already documents.
            # Monkeypatching _energy_limit_blocks_fire() (not the
            # ENERGY_LIMIT_ENABLED env var itself) mirrors the exact
            # pattern used for the breaker: neutralize the mechanism's
            # decision, not the kill switch, so this stays correct
            # regardless of what the environment happens to have set.
            for n in neurons:
                n._energy_limit_blocks_fire = lambda now: False
        n_inhibitory = sum(1 for n in neurons if getattr(n, "_polarity", 1.0) < 0)

        _saturate_all_intra_hemisphere_synapses(g)

        bus = g.organism.brain._spike_bus
        assert bus is not None, "organism must be wired to a real SpikeBus"

        fire_times = []
        for n in neurons:
            orig = n._fire
            def make_wrapper(orig_fn):
                def wrapped(now, triggering_spike=None):
                    fire_times.append(now)
                    return orig_fn(now, triggering_spike=triggering_spike)
                return wrapped
            n._fire = make_wrapper(orig)

        kick_target = neurons[0].neuron_id
        t_kick = time.monotonic()
        bus.inject(target_id=kick_target, source_id=f"{EXTERNAL_SOURCE_PREFIX}kick",
                   weight=1.5, arrival_delay_ms=0.0)

        time.sleep(SETTLE_AFTER_KICK_S)
        t_settled = time.monotonic()
        fires_during_settle = sum(1 for t in fire_times if t <= t_settled)

        time.sleep(QUIET_CHECK_WINDOW_S)
        fires_after_settle = sum(1 for t in fire_times if t > t_settled)

        return {
            "n_neurons": len(neurons),
            "n_inhibitory": n_inhibitory,
            "fires_during_settle": fires_during_settle,
            "fires_after_settle": fires_after_settle,
            "total_fires": len(fire_times),
        }
    finally:
        g.shutdown()


def test_real_seeding_produces_an_inhibitory_population():
    g = _fresh_guala()
    try:
        neurons = g._all_neurons()
        n_inhibitory = sum(1 for n in neurons if getattr(n, "_polarity", 1.0) < 0)
        assert n_inhibitory > 0, (
            "expected some inhibitory neurons from embryo's deterministic "
            "~20% split -- got zero, the fix would be a no-op on this population"
        )
        print(f"test_real_seeding_produces_an_inhibitory_population: PASS "
              f"({n_inhibitory}/{len(neurons)} inhibitory)")
    finally:
        g.shutdown()


def test_forced_all_excitatory_reproduces_the_cascade():
    """Pre-fix condition: with every neuron's outgoing spike forced
    excitatory, a fully-potentiated organism kicked once should still be
    firing well after external input stopped -- literal fire events in
    the post-settle window, not a growth-rate comparison. If this
    doesn't reproduce ANY post-settle fires, the harness can't validate
    the fix either -- the next test's PASS would be meaningless.

    2026-07-10: also neutralizes the fire-rate circuit breaker (see
    disable_fire_rate_breaker's docstring above) -- that mechanism
    shipped independently, the night after this test, and now also
    halts runaway firing on its own. Left active, this test would no
    longer reproduce the bug it exists to check for (verified directly:
    it silently stopped reproducing the cascade once the breaker
    existed), which would make this a false negative-control -- looking
    like a real regression in every suite run rather than the accurate
    signal that a second, independent safety layer now also covers this
    case. Isolating polarity as the only variable is what actually tests
    whether the fix would have been necessary on its own.

    2026-07-12: also neutralizes the per-neuron metabolic energy limit
    (see disable_energy_limit's docstring above) -- same masking class as
    the fire-rate breaker, confirmed directly: with ENERGY_LIMIT_ENABLED=1
    set in the environment, this test previously failed
    (fires_after_settle==0) even with the breaker already neutralized,
    because ENERGY_CEILING alone is sufficient to halt the saturated
    all-excitatory worst case. That is not a regression in the polarity
    fix -- it is this negative control silently going blind, which would
    let a real future regression in the polarity fix through undetected
    as long as the energy-limit flag happened to be set. Neutralizing it
    here keeps this test's job -- proving the harness itself can still
    detect a real cascade -- independent of which other opt-in
    defense-in-depth layers happen to be enabled in the environment."""
    result = _run_kick_and_watch(force_all_excitatory=True, disable_fire_rate_breaker=True,
                                  disable_energy_limit=True)
    print(f"test_forced_all_excitatory_reproduces_the_cascade: {result}")
    assert result["fires_after_settle"] > 0, (
        f"expected the all-excitatory forced condition to still be firing "
        f"after external input stopped (the known pre-fix bug); result={result}"
    )
    print("test_forced_all_excitatory_reproduces_the_cascade: PASS (bug reproduced as expected)")


def test_real_polarity_fix_stops_the_cascade():
    """With the fix active and the real embryo-seeded polarity split
    (untouched) on the same fully-potentiated organism, the same single
    kick should NOT leave anything firing once external input stops --
    zero fire events in the post-settle window."""
    result = _run_kick_and_watch(force_all_excitatory=False)
    print(f"test_real_polarity_fix_stops_the_cascade: {result}")
    assert result["fires_after_settle"] == 0, (
        f"expected inhibition to stop all firing once external input "
        f"stopped, but the network was still firing in the post-settle "
        f"window; result={result} -- the fix did not stop the cascade, "
        f"needs redesign, do not deploy"
    )
    print("test_real_polarity_fix_stops_the_cascade: PASS (network stopped firing)")


if __name__ == "__main__":
    test_real_seeding_produces_an_inhibitory_population()
    test_forced_all_excitatory_reproduces_the_cascade()
    test_real_polarity_fix_stops_the_cascade()
    print("ALL PASS: test_lateral_inhibition_cascade")
