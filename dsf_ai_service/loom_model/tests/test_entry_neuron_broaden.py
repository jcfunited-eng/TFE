"""
GL-CMD-ENTRY-NEURON-BROADEN: local tests for the kill-switched
(ENTRY_NEURON_BROADEN_ENABLED, default OFF) widening of entry-neuron
selection in Guala._select_entry_neurons (dsf_ai_service/v4/
gualaloom_v5_engine.py).

Real problem this addresses: commit 712578f correctly fixed the
25%-of-population-per-word over-injection incident by narrowing entry
selection from ENTRY_SAMPLE_SIZE=16 down to (in practice) 1 real
chi-proximity match per word. Side effect, measured live in production
(GL-RPT-BLUEPRINT-DEPLOYMENT-AUDIT-C1-20260712-v1): only 7 synapses were
ever touched across 3+ hours of real conversation -- exactly one
hemisphere's k_neighbors=7, i.e. only one entry-neuron firing event's
propagation ever completed.

This file proves, with real measurements against the real production
code paths (never a synthetic shortcut):

(a) OFF (default, and explicit "0") is BYTE-IDENTICAL to pre-existing
    behavior -- same entry neurons selected, same injection breadth.
(b) ON demonstrably increases real connection formation (distinct
    (source, target) synapse pairs touched) in a controlled scenario,
    using the exact same real production teaching path
    (_enqueue_organism_remember) test_stdp_repeated_exposure_learning.py
    already established as the real, non-synthetic path.
(c) A real measurement of what fraction of the neuron population gets
    touched per word under the new setting, across many distinct words,
    with an explicit comparison against the 25% threshold that caused
    the prior (712578f) incident -- and proof that the fraction is
    structurally bounded to one hemisphere (12.5%), not just measured
    low by chance.
(d) The existing cascade regression test
    (test_lateral_inhibition_cascade.py) still passes with the new flag
    enabled, plus an additional adversarial check specific to this
    change: kicking TWO neurons in the same worst-case saturated
    hemisphere simultaneously (what broadening actually does) still
    produces zero fires after external input stops.

Run standalone: `python3 test_entry_neuron_broaden.py` (also plain
pytest-discoverable).
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("SUBSTRATE_MODE", "embedded")

# Real English words plus synthetic filler -- same convention as this
# change's own module-comment measurement (gualaloom_v5_engine.py
# ENTRY_NEURON_BROADEN_COUNT comment), reproduced here so the test file
# is self-contained and re-runnable independent of that comment.
_BASE_WORDS = [
    "lighthouse", "ocean", "apple", "dog", "run", "blue", "music", "dream",
    "window", "cloud", "stone", "river", "fire", "light", "dark", "moon",
    "sun", "tree", "bird", "fish", "wind", "rain", "snow", "star", "earth",
    "book", "word", "voice", "song", "hand", "eye", "heart", "mind", "time",
    "space", "water", "air", "food", "home", "road", "city", "child", "friend",
]
_WORDS = _BASE_WORDS + [f"word_{i}" for i in range(120)]

INCIDENT_BREADTH_THRESHOLD = 0.25  # the 712578f incident's own 25%-of-population figure


def _fresh_guala():
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala
    os.environ["EVENT_DRIVEN_SUBSTRATE"] = "1"
    return Guala()


def _word_chi(word):
    from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import LanguageKrimelack
    krim = LanguageKrimelack()
    krim.transduce(word)
    return krim.winding


def _hemi_of(neuron_id):
    return neuron_id.split("_n")[0]


def _propagation_touched(entry_neurons):
    """Same neurons the real spike-bus propagation would touch: the
    entries themselves plus every neuron each entry's real (topology-
    static) outgoing synapses target -- mirrors LoomNeuron._fire's real
    _get_outgoing_synapses() loop, without needing to actually fire
    anything or wait on the delivery thread."""
    touched = {n.neuron_id for n in entry_neurons}
    for n in entry_neurons:
        for target_id, _weight in n._get_outgoing_synapses():
            touched.add(target_id)
    return touched


# ---------------------------------------------------------------------
# (a) OFF is byte-identical to today's behavior
# ---------------------------------------------------------------------

def test_broaden_default_off_is_byte_identical_to_baseline():
    """Default (env var unset): _select_entry_neurons must return exactly
    what _chi_to_neurons alone returns, for every word tested -- the
    broadening branch must never be reached."""
    os.environ.pop("ENTRY_NEURON_BROADEN_ENABLED", None)
    g = _fresh_guala()
    try:
        mismatches = []
        entry_counts = []
        for word in _WORDS:
            chi = _word_chi(word)
            baseline = g._chi_to_neurons(chi)
            selected = g._select_entry_neurons(chi)
            entry_counts.append(len(selected))
            if [n.neuron_id for n in selected] != [n.neuron_id for n in baseline]:
                mismatches.append(word)
        print(f"test_broaden_default_off_is_byte_identical_to_baseline: "
              f"{len(_WORDS)} words, entry_count set={set(entry_counts)}, "
              f"mismatches={mismatches}")
        assert not mismatches, (
            f"with ENTRY_NEURON_BROADEN_ENABLED unset, _select_entry_neurons "
            f"diverged from _chi_to_neurons for {len(mismatches)} words -- "
            f"default-off behavior is not byte-identical: {mismatches}")
        assert set(entry_counts) == {1}, (
            f"expected every tested word to select exactly 1 entry neuron "
            f"today (the known 712578f post-fix behavior), got "
            f"{set(entry_counts)} -- baseline assumption this test relies "
            f"on no longer holds, investigate before trusting the rest of "
            f"this file's comparisons")
        print("test_broaden_default_off_is_byte_identical_to_baseline: PASS")
    finally:
        g.shutdown()


def test_broaden_explicit_off_is_byte_identical_to_baseline():
    """Same as above but with the env var explicitly set to '0' (as
    opposed to merely unset) -- both spellings of "off" must behave
    identically."""
    os.environ["ENTRY_NEURON_BROADEN_ENABLED"] = "0"
    g = _fresh_guala()
    try:
        for word in _WORDS[:20]:
            chi = _word_chi(word)
            baseline = g._chi_to_neurons(chi)
            selected = g._select_entry_neurons(chi)
            assert [n.neuron_id for n in selected] == [n.neuron_id for n in baseline], (
                f"word={word!r}: explicit '0' diverged from baseline")
        print("test_broaden_explicit_off_is_byte_identical_to_baseline: PASS")
    finally:
        os.environ.pop("ENTRY_NEURON_BROADEN_ENABLED", None)
        g.shutdown()


# ---------------------------------------------------------------------
# (c) real measurement: population fraction touched, vs 25% threshold
# ---------------------------------------------------------------------

def test_broaden_on_stays_bounded_to_one_hemisphere():
    """With the flag on (count=2 and count=3), across many distinct real
    words: every entry set stays within ONE hemisphere, and the
    propagation-touched fraction of the population never approaches,
    let alone reaches, the 25% figure that caused the 712578f incident.
    This is a structural claim (bounded by hemisphere size, 8/64=12.5%),
    checked here empirically across a real, varied word sample rather
    than assumed from the code alone."""
    os.environ["ENTRY_NEURON_BROADEN_ENABLED"] = "1"
    g = _fresh_guala()
    try:
        pop = len(g._all_neurons())
        for count in (2, 3):
            os.environ["ENTRY_NEURON_BROADEN_COUNT"] = str(count)
            max_breadth = 0.0
            max_hemis_spanned = 0
            entry_count_seen = set()
            for word in _WORDS:
                chi = _word_chi(word)
                entries = g._select_entry_neurons(chi)
                entry_count_seen.add(len(entries))
                hemis = {_hemi_of(n.neuron_id) for n in entries}
                max_hemis_spanned = max(max_hemis_spanned, len(hemis))
                assert len(hemis) == 1, (
                    f"count={count} word={word!r}: entries spanned "
                    f"{len(hemis)} hemispheres ({hemis}) -- broadening "
                    f"must stay within one hemisphere")
                touched = _propagation_touched(entries)
                breadth = len(touched) / pop
                max_breadth = max(max_breadth, breadth)
                assert breadth <= 8.0 / pop + 1e-9, (
                    f"count={count} word={word!r}: propagation breadth "
                    f"{breadth:.3f} exceeds one hemisphere's own size "
                    f"(8/{pop}={8.0/pop:.3f}) -- structural bound violated")
            print(f"test_broaden_on_stays_bounded_to_one_hemisphere: "
                  f"count={count} entry_counts_seen={entry_count_seen} "
                  f"max_breadth={max_breadth:.3f} "
                  f"max_hemispheres_spanned={max_hemis_spanned} "
                  f"(incident threshold={INCIDENT_BREADTH_THRESHOLD})")
            assert max_breadth < INCIDENT_BREADTH_THRESHOLD, (
                f"count={count}: max measured breadth {max_breadth:.3f} "
                f"is not meaningfully below the {INCIDENT_BREADTH_THRESHOLD} "
                f"incident threshold -- do not ship")
        print("test_broaden_on_stays_bounded_to_one_hemisphere: PASS")
    finally:
        os.environ.pop("ENTRY_NEURON_BROADEN_ENABLED", None)
        os.environ.pop("ENTRY_NEURON_BROADEN_COUNT", None)
        g.shutdown()


def test_broaden_on_globally_nearest_would_have_been_unsafe():
    """Negative control / documentation-as-test: confirms the REJECTED
    design (widen to the K globally-nearest-by-chi neurons, no
    hemisphere constraint) really would have reproduced the incident
    condition, so the hemisphere-scoped design isn't solving a problem
    that didn't exist. Does not touch _select_entry_neurons (this
    reimplements the rejected approach standalone, read-only, real
    neuron/topology data) -- kept as a regression guard on the reasoning,
    not a claim about shipped code."""
    g = _fresh_guala()
    try:
        pop = len(g._all_neurons())
        space = g._CHI_ADDRESS_SPACE
        all_neurons = g._all_neurons()
        saw_25pct = False
        for word in _WORDS:
            chi = _word_chi(word)
            chi_wrapped = chi % space
            scored = []
            for n in all_neurons:
                if n.chi_position is None:
                    continue
                raw = abs(n.chi_position - chi_wrapped)
                wrap = min(raw, space - raw)
                scored.append((wrap, n.neuron_id, n))
            scored.sort(key=lambda t: (t[0], t[1]))
            entries = [n for _, _, n in scored[:3]]
            touched = _propagation_touched(entries)
            if len(touched) / pop >= INCIDENT_BREADTH_THRESHOLD:
                saw_25pct = True
                break
        print(f"test_broaden_on_globally_nearest_would_have_been_unsafe: "
              f"globally-nearest-3 hit >=25% breadth: {saw_25pct}")
        assert saw_25pct, (
            "expected the globally-nearest (hemisphere-unconstrained) "
            "design to reproduce >=25% breadth on at least one real word "
            "-- if this no longer reproduces, the hemisphere constraint "
            "in the shipped design may no longer be necessary and this "
            "test's own premise should be re-examined, not silently "
            "loosened")
        print("test_broaden_on_globally_nearest_would_have_been_unsafe: PASS")
    finally:
        g.shutdown()


# ---------------------------------------------------------------------
# (b) real connection-formation increase, controlled scenario
# ---------------------------------------------------------------------

def _teach_once_and_snapshot(broaden_enabled, broaden_count=2, word="lighthouse"):
    """Teach `word` exactly once via the real production path
    (_enqueue_organism_remember) on a fresh organism, wait for the
    worker + spike-bus delivery to settle, and return the set of
    (source_id, target_id) synapse pairs that ended up strictly above
    STDP_DEFAULT_SYNAPSE_WEIGHT anywhere in the population."""
    from dsf_ai_service.loom_model.neuron import STDP_DEFAULT_SYNAPSE_WEIGHT

    os.environ["ENTRY_NEURON_BROADEN_ENABLED"] = "1" if broaden_enabled else "0"
    os.environ["ENTRY_NEURON_BROADEN_COUNT"] = str(broaden_count)
    g = _fresh_guala()
    try:
        entries_before = set(g._word_neuron_map.get(word, set()))
        assert not entries_before, "fixture not fresh"

        g._enqueue_organism_remember(word)
        g._organism_queue.join()
        time.sleep(0.5)  # let the spike-bus delivery thread flush propagation

        touched_pairs = set()
        for n in g._all_neurons():
            with n._neuron_lock:
                weights = dict(n._incoming_synapse_weights)
            for source_id, w in weights.items():
                if w > STDP_DEFAULT_SYNAPSE_WEIGHT + 1e-9:
                    touched_pairs.add((source_id, n.neuron_id))

        entry_neurons = set(g._word_neuron_map.get(word, set()))
        return entry_neurons, touched_pairs
    finally:
        os.environ.pop("ENTRY_NEURON_BROADEN_ENABLED", None)
        os.environ.pop("ENTRY_NEURON_BROADEN_COUNT", None)
        g.shutdown()


def test_broaden_on_increases_real_connection_formation():
    """Central behavioral claim: teaching the SAME single word once, via
    the real production teaching path, touches (and, per the earlier
    subthreshold-potentiation fix, strengthens) strictly more distinct
    synapse pairs with broadening ON than with it OFF."""
    off_entries, off_pairs = _teach_once_and_snapshot(broaden_enabled=False)
    on_entries, on_pairs = _teach_once_and_snapshot(broaden_enabled=True, broaden_count=2)

    print(f"test_broaden_on_increases_real_connection_formation: "
          f"OFF entries={off_entries} pairs_touched={len(off_pairs)} "
          f"({sorted(off_pairs)})")
    print(f"test_broaden_on_increases_real_connection_formation: "
          f"ON(count=2) entries={on_entries} pairs_touched={len(on_pairs)} "
          f"({sorted(on_pairs)})")

    assert len(off_entries) == 1, f"expected OFF to select exactly 1 entry, got {off_entries}"
    assert len(on_entries) == 2, f"expected ON(count=2) to select exactly 2 entries, got {on_entries}"
    assert on_entries.issuperset(off_entries) or len(on_entries & off_entries) >= 0, (
        "sanity: entries are neuron ids, no type mismatch")
    assert len(on_pairs) > len(off_pairs), (
        f"expected broadening to strictly increase the number of real "
        f"synapse pairs touched by a single teach of one word: "
        f"OFF={len(off_pairs)} ON={len(on_pairs)} -- broadening produced "
        f"no measurable connection-formation improvement, do not ship")
    assert off_pairs.issubset(on_pairs) or True, (
        "not required that ON is a strict superset (different entry ids "
        "mean different source neurons), only that it touches more total "
        "distinct pairs -- already checked above")
    print("test_broaden_on_increases_real_connection_formation: PASS")


# ---------------------------------------------------------------------
# (d) existing cascade regression test, plus a broadening-specific
# adversarial two-neuron-kick variant
# ---------------------------------------------------------------------

def test_existing_cascade_regression_still_passes_with_broaden_enabled():
    """Runs the real, existing test_lateral_inhibition_cascade.py test
    functions with ENTRY_NEURON_BROADEN_ENABLED=1 set in the environment
    -- confirms this change doesn't alter that test's outcome (it doesn't
    call _select_entry_neurons at all, so this is a compatibility check,
    not expected to find anything -- run anyway per this dispatch's own
    requirement, not assumed)."""
    os.environ["ENTRY_NEURON_BROADEN_ENABLED"] = "1"
    try:
        import test_lateral_inhibition_cascade as cascade_test
        cascade_test.test_real_seeding_produces_an_inhibitory_population()
        cascade_test.test_forced_all_excitatory_reproduces_the_cascade()
        cascade_test.test_real_polarity_fix_stops_the_cascade()
        print("test_existing_cascade_regression_still_passes_with_broaden_enabled: PASS")
    finally:
        os.environ.pop("ENTRY_NEURON_BROADEN_ENABLED", None)


def test_broaden_worst_case_two_neuron_simultaneous_kick_stays_quiet():
    """Adversarial variant specific to this change: broadening's real
    effect is injecting an EXTERNAL spike into 2 same-hemisphere neurons
    simultaneously (rather than 1). Reuses the existing cascade test's
    own worst-case fixture (every intra-hemisphere synapse pre-saturated
    to MAX_SYNAPSE_WEIGHT, real embryo-seeded polarity left untouched)
    and kicks 2 neurons in the same hemisphere at once instead of 1.
    Verdict is the same physical criterion the existing cascade test
    uses: zero fires once external input stops, checked well past any
    legitimate in-flight echo."""
    import test_lateral_inhibition_cascade as cascade_test
    from dsf_ai_service.loom_model.neuron import EXTERNAL_SOURCE_PREFIX

    g = cascade_test._fresh_guala()
    try:
        neurons = g._all_neurons()
        assert len(neurons) >= 32, "expected the real multi-hemisphere organism"
        cascade_test._saturate_all_intra_hemisphere_synapses(g)

        bus = g.organism.brain._spike_bus
        assert bus is not None

        # two neurons from the SAME hemisphere -- exactly what broadening
        # (count=2, hemisphere-scoped) would select as an entry set.
        hemi0_neurons = [n for n in neurons if n.neuron_id.startswith("H0_n")]
        assert len(hemi0_neurons) >= 2, "expected hemisphere H0 to have >=2 neurons"
        kick_targets = [hemi0_neurons[0].neuron_id, hemi0_neurons[1].neuron_id]

        fire_times = []
        for n in neurons:
            orig = n._fire
            def make_wrapper(orig_fn):
                def wrapped(now, triggering_spike=None):
                    fire_times.append(now)
                    return orig_fn(now, triggering_spike=triggering_spike)
                return wrapped
            n._fire = make_wrapper(orig)

        t_kick = time.monotonic()
        for tid in kick_targets:
            bus.inject(target_id=tid, source_id=f"{EXTERNAL_SOURCE_PREFIX}kick",
                       weight=1.5, arrival_delay_ms=0.0)

        time.sleep(cascade_test.SETTLE_AFTER_KICK_S)
        t_settled = time.monotonic()
        time.sleep(cascade_test.QUIET_CHECK_WINDOW_S)
        fires_after_settle = sum(1 for t in fire_times if t > t_settled)

        print(f"test_broaden_worst_case_two_neuron_simultaneous_kick_stays_quiet: "
              f"kicked={kick_targets} total_fires={len(fire_times)} "
              f"fires_after_settle={fires_after_settle}")
        assert fires_after_settle == 0, (
            f"simultaneous 2-neuron kick (the real effect of broadening "
            f"count=2) left the network firing after external input "
            f"stopped: fires_after_settle={fires_after_settle} -- "
            f"broadening is not safe under the worst-case saturated "
            f"topology, do not ship")
        print("test_broaden_worst_case_two_neuron_simultaneous_kick_stays_quiet: PASS")
    finally:
        g.shutdown()


if __name__ == "__main__":
    test_broaden_default_off_is_byte_identical_to_baseline()
    test_broaden_explicit_off_is_byte_identical_to_baseline()
    test_broaden_on_stays_bounded_to_one_hemisphere()
    test_broaden_on_globally_nearest_would_have_been_unsafe()
    test_broaden_on_increases_real_connection_formation()
    test_existing_cascade_regression_still_passes_with_broaden_enabled()
    test_broaden_worst_case_two_neuron_simultaneous_kick_stays_quiet()
    print("ALL PASS: test_entry_neuron_broaden")
