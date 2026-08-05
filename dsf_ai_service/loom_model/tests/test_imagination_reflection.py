"""
test_imagination_reflection.py — GL-RPT-BRAIN-IMAGINATION-REFLECTION-DESIGN-
C1-20260711-v1, built for real 2026-07-11.

Tests two real, organism-native mechanisms for the loom_model organism-brain
subsystem (Embryo/LoomBrain/BindingAtlas), built without depending on
Composition (LoomTapestry/LoomMosaic — confirmed still genuinely unwired) or
autonomous spike/STDP propagation (confirmed still shadow-only in
production):

  - "Imagination": BindingAtlas.latent_associations() + Embryo.imagine() —
    population-vote latent-geometric-association surfacing over a
    hemisphere's own already-learned bindings.
  - "Reflection": Embryo._reflect_snapshot()/Embryo.reflect() — bounded
    self-state-then-vs-now comparison over sf_sense() history.

Every test below either (a) hand-constructs bindings with KNOWN vectors/
ticks via BindingAtlas.record() (the same real, unmodified API production
uses) and asserts the mechanism's output is independently re-derivable from
those exact values — not merely "looks plausible" — or (b) drives a real
Embryo through real remember()/experience_word() calls and cross-checks the
mechanism's output against an independent recomputation over the SAME real
underlying bindings. No test asserts on fabricated/random content; several
assert the mechanism outputs [] / None when there is genuinely nothing real
to surface yet (the honest-empty case, not a bug).
"""

import os
import sys
import pickle
import tempfile
from collections import Counter

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from dsf_ai_service.loom_model.binding_atlas import BindingAtlas
from dsf_ai_service.loom_model.embryo import Embryo, OPERATIONS
from dsf_ai_service.loom_model.grandurun import grandurun_state, MODALITIES


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _delta(**kw):
    """grandurun_state() with unspecified modalities defaulting to 0.0."""
    return grandurun_state({m: float(kw.get(m, 0.0)) for m in MODALITIES})


def _signals(seed_offset, word):
    """Real, deterministic multi-modal signal dict — same shape production's
    _organism_signal/ExperiencePipeline produce, hand-built like
    test_cognition_path.py's test_t3_neuron_binding does, so these tests
    don't need the full sensory-transducer/catalog stack."""
    rng = np.random.default_rng(1000 + seed_offset)
    return {
        "language": word,
        "visual": rng.uniform(0, 1, 50).tolist(),
        "auditory": np.sin(np.arange(200) / 200.0 * 2 * np.pi * (5 + seed_offset)).tolist(),
        "tactile": rng.uniform(0, 1, 50).tolist(),
        "olfactory": rng.uniform(0, 1, 50).tolist(),
        "gustatory": rng.uniform(0, 1, 50).tolist(),
    }


# ---------------------------------------------------------------------------
# BindingAtlas.latent_associations() — unit level, fully known vectors
# ---------------------------------------------------------------------------

def test_latent_associations_empty_below_three_concepts():
    atlas = BindingAtlas()
    assert atlas.latent_associations() == []
    atlas.record("a", _delta(visual=1.0), tick=0)
    assert atlas.latent_associations() == []
    atlas.record("b", _delta(visual=1.0), tick=1)
    assert atlas.latent_associations() == []  # still <3 concepts
    print("\n== latent_associations: honest empty below 3 concepts == PASS")


def test_latent_associations_traces_to_known_vectors():
    """The core traceability proof: cat/dog/rabbit are built to be
    PERFECTLY cosine-similar (parallel vectors, cosine=1.0 exactly) by
    construction. cat/dog are adjacent in tick (taught back-to-back —
    the ordinary, unsurprising case); rabbit is taught much later. Four
    filler concepts are near-orthogonal to the cat/dog/rabbit direction
    and to each other, giving the population a real similarity spread to
    be self-relatively above-average against.

    Expected, and asserted by RE-DERIVING the exact same computation
    independently in this test (not a hardcoded magic number): the
    (cat, rabbit) pair — maximum real similarity AND maximum real
    temporal separation — outranks (cat, dog) — the SAME maximum real
    similarity but adjacent-tick (minimal separation) — even though both
    pairs have literally identical cosine similarity. This is the
    mechanism's whole point: surfacing geometric closeness that was NOT
    explained by co-occurrence, not just geometric closeness.
    """
    atlas = BindingAtlas()
    atlas.record("cat", _delta(visual=1, auditory=1, tactile=1, olfactory=1, gustatory=1, language=1), tick=0)
    atlas.record("dog", _delta(visual=2, auditory=2, tactile=2, olfactory=2, gustatory=2, language=2), tick=1)
    atlas.record("rabbit", _delta(visual=3, auditory=3, tactile=3, olfactory=3, gustatory=3, language=3), tick=20)
    atlas.record("f1", _delta(visual=1, auditory=-1), tick=5)
    atlas.record("f2", _delta(tactile=1, olfactory=-1), tick=10)
    atlas.record("f3", _delta(visual=-1, gustatory=1), tick=15)
    atlas.record("f4", _delta(auditory=1, gustatory=-1), tick=18)

    current_tick = 20
    results = atlas.latent_associations(top_k=10, current_tick=current_tick)
    assert results, "expected at least one surfaced pair from 3 exactly-parallel vectors"

    # --- Independent re-derivation over the SAME real bindings, using
    # only numpy — must match the method's own output bit-for-bit. ---
    concept_vecs = atlas._concept_vectors(max_concepts=200)
    concepts = list(concept_vecs.keys())
    pairs = []
    for i in range(len(concepts)):
        for j in range(i + 1, len(concepts)):
            ca, cb = concepts[i], concepts[j]
            va, ta = concept_vecs[ca]
            vb, tb = concept_vecs[cb]
            na, nb = np.linalg.norm(va), np.linalg.norm(vb)
            cos = float(np.dot(va, vb) / (na * nb))
            pairs.append((ca, cb, cos, abs(ta - tb)))
    sims = np.array([p[2] for p in pairs])
    mean_sim, std_sim = float(sims.mean()), float(sims.std())
    expected = {}
    for ca, cb, cos, gap in pairs:
        z = (cos - mean_sim) / std_sim if std_sim > 1e-9 else 0.0
        temporal_fraction = gap / current_tick
        novelty = max(0.0, z) * temporal_fraction
        if novelty > 0.0:
            expected[frozenset((ca, cb))] = {
                "cosine": cos, "tick_gap": gap, "temporal_fraction": temporal_fraction,
                "similarity_z": z, "novelty_score": novelty,
            }

    got = {frozenset((r["concept_a"], r["concept_b"])): r for r in results}
    assert set(got.keys()) == set(expected.keys()), (
        f"surfaced pair set diverged from independent recomputation: "
        f"got={got.keys()} expected={expected.keys()}"
    )
    for key, exp in expected.items():
        r = got[key]
        assert r["cosine"] == pytest.approx(exp["cosine"], abs=1e-9)
        assert r["tick_gap"] == exp["tick_gap"]
        assert r["temporal_fraction"] == pytest.approx(exp["temporal_fraction"], abs=1e-9)
        assert r["similarity_z"] == pytest.approx(exp["similarity_z"], abs=1e-9)
        assert r["novelty_score"] == pytest.approx(exp["novelty_score"], abs=1e-9)

    # The specific, designed-in outcome: (cat, rabbit) beats (cat, dog)
    # despite identical cosine similarity, purely because of real
    # temporal separation -- proves this is NOT just a similarity scan.
    cat_rabbit = got[frozenset(("cat", "rabbit"))]
    cat_dog = got[frozenset(("cat", "dog"))]
    assert cat_rabbit["cosine"] == pytest.approx(1.0, abs=1e-9)
    assert cat_dog["cosine"] == pytest.approx(1.0, abs=1e-9)
    assert cat_rabbit["novelty_score"] > cat_dog["novelty_score"], (
        "cat/rabbit (max similarity, max temporal separation) should "
        "outrank cat/dog (max similarity, MINIMAL temporal separation -- "
        "the ordinary co-taught case), but did not"
    )
    assert results[0]["novelty_score"] == max(r["novelty_score"] for r in results)
    print("\n== latent_associations: traces to known vectors == PASS")
    print(f"  top result: {results[0]['concept_a']}/{results[0]['concept_b']} "
          f"novelty={results[0]['novelty_score']:.4f}")


def test_latent_associations_lane_dict_representation():
    """Same mechanism over the OTHER real production representation
    (resonant_spectral / per-lane dict bindings -- loom_voice.py and every
    Embryo() call site that doesn't override observable defaults to this).
    Uses _lane_match_score, the SAME masked lane-cosine this file's real
    recall path already uses -- not a new algorithm."""
    atlas = BindingAtlas()

    def lane(v_a, v_b):
        return {"visual": np.array([v_a, v_b], dtype=np.float64)}

    atlas.record("x", lane(1.0, 0.0), tick=0)
    atlas.record("y", lane(2.0, 0.0), tick=1)          # parallel to x, adjacent tick
    atlas.record("z", lane(3.0, 0.0), tick=50)          # parallel to x, distant tick
    atlas.record("w1", lane(0.0, 1.0), tick=10)
    atlas.record("w2", lane(-1.0, 0.0), tick=20)

    results = atlas.latent_associations(top_k=10, current_tick=50)
    assert results, "expected the lane-dict path to surface at least one real pair"
    top = results[0]
    assert {top["concept_a"], top["concept_b"]} == {"x", "z"}, (
        f"expected (x, z) — max similarity + max temporal separation — on "
        f"top, got {top['concept_a']}/{top['concept_b']}"
    )
    assert top["cosine"] == pytest.approx(1.0, abs=1e-9)
    print("\n== latent_associations: lane-dict (resonant_spectral) representation == PASS")


def test_latent_associations_max_concepts_caps_by_recency():
    atlas = BindingAtlas()
    for i in range(10):
        atlas.record(f"c{i}", _delta(visual=float(i + 1)), tick=i)

    capped = atlas._concept_vectors(max_concepts=4)
    assert len(capped) == 4
    kept_ticks = sorted(t for _, t in capped.values())
    assert kept_ticks == [6, 7, 8, 9], (
        f"recency cap should keep the 4 MOST RECENTLY bound concepts, got ticks {kept_ticks}"
    )
    print("\n== latent_associations: max_concepts caps by recency, deterministically == PASS")


def test_pair_cosine_mismatched_representation_is_none_not_zero():
    """A flat vector and a lane dict must never silently compare as similar
    (or dissimilar) — an honest 'not comparable', matching this file's own
    established 'None, not a fabricated 0.0' convention (_lane_match_score)."""
    flat = _delta(visual=1.0)
    lane = {"visual": np.array([1.0, 0.0])}
    assert BindingAtlas._pair_cosine(flat, lane) is None
    assert BindingAtlas._pair_cosine(lane, flat) is None
    print("\n== _pair_cosine: mismatched representations -> None == PASS")


# ---------------------------------------------------------------------------
# Embryo.imagine() — population vote over a real hemisphere
# ---------------------------------------------------------------------------

def test_imagine_empty_hemisphere_and_bad_op_tag():
    emb = Embryo(brain_seed=42, seed_size=4, observable="event_count")
    assert emb.imagine(op_tag="not_a_real_hemisphere") == []
    assert emb.imagine(op_tag="sc") == []  # nothing bound yet anywhere
    print("\n== imagine: honest empty (no hemisphere / no bindings) == PASS")


def test_imagine_traces_to_real_population_vote():
    """Real Embryo, real 'sc' hemisphere (4 real neurons, real per-neuron
    DNA). Every neuron's BindingAtlas is given the IDENTICAL set of known
    bindings directly via the real record() API (bypassing the emergent
    krimelack encoding, which is a separate, already-tested concern —
    T1-T13 in test_cognition_path.py — not what this test is about), so
    the population-vote outcome is exactly predictable: all 4 neurons must
    independently surface the identical top pair, so n_neurons_agree must
    be exactly 4 and mean_novelty_score must equal any one neuron's own
    novelty_score exactly (they're all identical).

    This proves imagine()'s aggregation is a faithful vote over real
    per-neuron scans, not a fabricated summary."""
    emb = Embryo(brain_seed=42, seed_size=4, observable="event_count")
    sc_neurons = emb.hemi_by_op["sc"].cluster.neurons
    assert len(sc_neurons) == 4

    bindings = [
        ("cat", _delta(visual=1, auditory=1, tactile=1), 0),
        ("dog", _delta(visual=2, auditory=2, tactile=2), 1),
        ("rabbit", _delta(visual=3, auditory=3, tactile=3), 40),
        ("f1", _delta(olfactory=1, gustatory=-1), 5),
        ("f2", _delta(language=1, visual=-1), 15),
    ]
    for n in sc_neurons:
        for concept, vec, tick in bindings:
            n.binding_atlas.record(concept, vec, tick)
    emb.tick = 40

    got = emb.imagine(op_tag="sc", top_k=5)
    assert got, "expected a real surfaced pair from identical known bindings on every neuron"

    # Independent recomputation: since every neuron's atlas is identical,
    # one neuron's own latent_associations() output IS the expected
    # per-neuron result for all four.
    one_neuron_result = sc_neurons[0].binding_atlas.latent_associations(
        top_k=5, current_tick=emb.tick)
    assert one_neuron_result, "sanity: the single-neuron scan must itself be non-empty"
    expected_top_key = frozenset((one_neuron_result[0]["concept_a"], one_neuron_result[0]["concept_b"]))
    expected_novelty = one_neuron_result[0]["novelty_score"]

    top = got[0]
    assert {top["concept_a"], top["concept_b"]} == set(expected_top_key)
    assert top["n_neurons_agree"] == 4, f"all 4 identical neurons should agree, got {top['n_neurons_agree']}"
    assert top["n_neurons_scanned"] == 4
    assert top["mean_novelty_score"] == pytest.approx(expected_novelty, abs=1e-9)
    assert top["op_tag"] == "sc"
    print("\n== imagine: population vote traces to real per-neuron scans == PASS")
    print(f"  top: {top['concept_a']}/{top['concept_b']} agree={top['n_neurons_agree']}/4")


def test_imagine_end_to_end_real_embryo_experience():
    """No hand-injected vectors -- drives a real Embryo through real
    remember() calls with real (deterministic) multi-modal signals, the
    same call production's Embryo.experience_word()/remember() path
    actually uses. Only asserts the mechanism runs end-to-end without
    crashing and, when it does surface something, every returned field is
    self-consistent (agree count bounded by population, novelty > 0) --
    the emergent-encoding case is inherently non-hand-predictable (that's
    what T1-T13 already cover elsewhere), so this test's job is "doesn't
    crash and stays honest under real conditions," not "predicts the
    exact pair."""
    emb = Embryo(brain_seed=42, seed_size=4, observable="event_count")
    concepts = [f"concept_{i}" for i in range(12)]
    for rep in range(3):
        for i, c in enumerate(concepts):
            emb.remember(c, _signals(i, c))

    n_sc = len(emb.hemi_by_op["sc"].cluster.neurons)
    got = emb.imagine(op_tag="sc", top_k=5)
    for r in got:
        assert 1 <= r["n_neurons_agree"] <= r["n_neurons_scanned"] <= n_sc
        assert r["mean_novelty_score"] > 0.0
        assert r["concept_a"] != r["concept_b"]
        assert r["concept_a"] in concepts and r["concept_b"] in concepts
    print(f"\n== imagine: end-to-end real Embryo experience == PASS ({len(got)} pairs surfaced)")


# ---------------------------------------------------------------------------
# Embryo.reflect() / _reflect_snapshot() — self-state then-vs-now
# ---------------------------------------------------------------------------

def test_reflect_none_before_any_snapshot():
    emb = Embryo(brain_seed=42, seed_size=4, observable="event_count")
    assert emb.reflect() is None
    assert emb.reflect(against="latest") is None
    print("\n== reflect: honest None before any snapshot == PASS")


def test_reflect_snapshot_fires_on_interval_and_stays_bounded():
    emb = Embryo(brain_seed=42, seed_size=4, observable="event_count")
    n_words = emb.REFLECTION_SNAPSHOT_INTERVAL * (emb.REFLECTION_HISTORY_MAXLEN + 5)
    for i in range(n_words):
        emb.remember(f"w{i % 20}", _signals(i % 20, f"w{i % 20}"))

    assert len(emb._reflection_snapshots) == emb.REFLECTION_HISTORY_MAXLEN, (
        "bounded deque must cap at REFLECTION_HISTORY_MAXLEN, not grow unbounded"
    )
    ticks = [t for t, _ in emb._reflection_snapshots]
    assert ticks == sorted(ticks), "snapshot history must be chronological"
    assert all(t % emb.REFLECTION_SNAPSHOT_INTERVAL == 0 for t in ticks), (
        f"every snapshot tick must land exactly on the interval, got {ticks}"
    )
    print(f"\n== reflect: snapshots fire on interval, bounded at {emb.REFLECTION_HISTORY_MAXLEN} == PASS")


def test_reflect_diff_traces_to_real_sf_sense_change():
    """Drives REAL arousal/strength movement via experience_word() (unlike
    plain remember(), this is the call that actually touches
    _experience_core -> arousal/strength) so 'then' and 'now' are
    genuinely different, real values -- then proves reflect()'s output is
    exactly recomputable from independently-captured sf_sense() readings,
    not approximated or fabricated."""
    emb = Embryo(brain_seed=42, seed_size=4, observable="event_count")

    # Drive to the first snapshot boundary with real experience.
    i = 0
    while emb.tick < emb.REFLECTION_SNAPSHOT_INTERVAL:
        emb.experience_word(f"w{i}", _signals(i, f"w{i}"))
        i += 1
    assert len(emb._reflection_snapshots) == 1
    then_tick_recorded, then_vec_recorded = emb._reflection_snapshots[0]

    # Drive further real experience so 'now' genuinely differs from 'then'.
    for _ in range(80):
        emb.experience_word(f"w{i}", _signals(i, f"w{i}"), theta=0.0)
        i += 1

    now_vec_independent = emb.sf_sense()   # captured independently, same call reflect() makes

    result = emb.reflect(against="oldest")
    assert result is not None
    assert result["tick_then"] == then_tick_recorded
    assert result["tick_now"] == emb.tick
    assert result["ticks_elapsed"] == emb.tick - then_tick_recorded

    field_names = ["arousal", "pop_mean", "pop_max"] + [t for t, _ in OPERATIONS]
    expected_delta = now_vec_independent - then_vec_recorded
    for idx, name in enumerate(field_names):
        pf = result["per_field"][name]
        assert pf["then"] == pytest.approx(float(then_vec_recorded[idx]), abs=1e-12)
        assert pf["now"] == pytest.approx(float(now_vec_independent[idx]), abs=1e-12)
        assert pf["delta"] == pytest.approx(float(expected_delta[idx]), abs=1e-12)
    assert result["delta_norm"] == pytest.approx(float(np.linalg.norm(expected_delta)), abs=1e-9)

    # This is a real, non-trivial run (100+ real experiences) — the
    # organism's own arousal/strength axis should genuinely have moved,
    # not sat frozen at the snapshot's values.
    assert result["delta_norm"] > 0.0, (
        "expected real self-state movement across 80 real experiences; "
        "delta_norm == 0 would mean this test is not actually exercising "
        "real dynamics"
    )
    print(f"\n== reflect: diff traces to real sf_sense() change == PASS (delta_norm={result['delta_norm']:.4f})")


def test_reflect_latest_vs_oldest_are_real_distinct_snapshots():
    emb = Embryo(brain_seed=42, seed_size=4, observable="event_count")
    i = 0
    while len(emb._reflection_snapshots) < 3:
        emb.experience_word(f"w{i}", _signals(i, f"w{i}"), theta=0.0)
        i += 1

    oldest_tick = emb._reflection_snapshots[0][0]
    latest_tick = emb._reflection_snapshots[-1][0]
    assert oldest_tick < latest_tick

    r_oldest = emb.reflect(against="oldest")
    r_latest = emb.reflect(against="latest")
    assert r_oldest["tick_then"] == oldest_tick
    assert r_latest["tick_then"] == latest_tick
    assert r_oldest["ticks_elapsed"] >= r_latest["ticks_elapsed"]
    print("\n== reflect: 'oldest' and 'latest' resolve to real, distinct snapshots == PASS")


def test_reflect_self_heals_on_pre_dispatch_pickle_shape():
    """Simulates a real production organism pickled BEFORE this dispatch
    (no _reflection_snapshots attribute at all -- pickle.load() sets
    __dict__ directly and never re-runs __init__, exactly like every other
    schema-evolution incident this project has hit: -198's
    _fold_events_buffer/_total_divisions, -207/-208's BindingAtlas
    migration). Must self-heal, not crash."""
    emb = Embryo(brain_seed=42, seed_size=4, observable="event_count")
    del emb._reflection_snapshots
    assert not hasattr(emb, "_reflection_snapshots")

    assert emb.reflect() is None   # must not raise AttributeError

    for i in range(emb.REFLECTION_SNAPSHOT_INTERVAL + 1):
        emb.remember(f"w{i}", _signals(i, f"w{i}"))   # must not raise

    assert hasattr(emb, "_reflection_snapshots")
    assert len(emb._reflection_snapshots) == 1
    assert emb.reflect() is not None
    print("\n== reflect: self-heals a pre-dispatch (missing-attribute) organism == PASS")


def test_full_pickle_roundtrip_preserves_reflection_and_imagination_data():
    """The project's single most-repeated real bug class is pickle/restore
    losing state (STDP fields, spike_bus wiring, BindingAtlas shape, ...).
    Embryo has no custom __getstate__/__setstate__ -- it round-trips its
    full __dict__ -- so this proves the NEW state (_reflection_snapshots)
    and the bindings imagine() reads both survive a REAL save_full_state/
    load_full_state cycle (the actual production persistence path, not a
    bare pickle.dumps stand-in) with byte-identical values, and that
    reflect()/imagine() on the restored organism produce IDENTICAL output
    to the pre-save organism."""
    emb = Embryo(brain_seed=42, seed_size=4, observable="event_count")
    i = 0
    while len(emb._reflection_snapshots) < 2:
        emb.experience_word(f"w{i}", _signals(i, f"w{i}"), theta=0.0)
        i += 1

    for n in emb.hemi_by_op["sc"].cluster.neurons:
        n.binding_atlas.record("known_a", _delta(visual=1, auditory=1), emb.tick - 30)
        n.binding_atlas.record("known_b", _delta(visual=2, auditory=2), emb.tick)
        n.binding_atlas.record("known_c", _delta(tactile=1, gustatory=-1), emb.tick - 15)

    before_reflect = emb.reflect(against="oldest")
    before_imagine = emb.imagine(op_tag="sc", top_k=5)
    assert before_reflect is not None
    assert before_imagine

    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "embryo_state.pkl.gz")
        emb.save_full_state(path)
        restored = Embryo.load_full_state(path)

    assert len(restored._reflection_snapshots) == len(emb._reflection_snapshots)
    for (t0, v0), (t1, v1) in zip(emb._reflection_snapshots, restored._reflection_snapshots):
        assert t0 == t1
        assert np.array_equal(v0, v1)

    after_reflect = restored.reflect(against="oldest")
    after_imagine = restored.imagine(op_tag="sc", top_k=5)

    assert after_reflect == before_reflect, (
        "reflect() output diverged across a real save_full_state/"
        "load_full_state round trip"
    )
    assert after_imagine == before_imagine, (
        "imagine() output diverged across a real save_full_state/"
        "load_full_state round trip"
    )
    print("\n== full pickle round trip (save_full_state/load_full_state) preserves "
          "reflection + imagination-relevant data == PASS")


if __name__ == "__main__":
    test_latent_associations_empty_below_three_concepts()
    test_latent_associations_traces_to_known_vectors()
    test_latent_associations_lane_dict_representation()
    test_latent_associations_max_concepts_caps_by_recency()
    test_pair_cosine_mismatched_representation_is_none_not_zero()
    test_imagine_empty_hemisphere_and_bad_op_tag()
    test_imagine_traces_to_real_population_vote()
    test_imagine_end_to_end_real_embryo_experience()
    test_reflect_none_before_any_snapshot()
    test_reflect_snapshot_fires_on_interval_and_stays_bounded()
    test_reflect_diff_traces_to_real_sf_sense_change()
    test_reflect_latest_vs_oldest_are_real_distinct_snapshots()
    test_reflect_self_heals_on_pre_dispatch_pickle_shape()
    test_full_pickle_roundtrip_preserves_reflection_and_imagination_data()
    print("\nALL PASS: test_imagination_reflection")
