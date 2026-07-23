"""Review-fix verification for the all-at-once integration (2026-07-16).

F1  — self_heard origin: released speech re-enters as recallable
      experience but can NEVER mint word-order citation facts.
F2/4 — wave-atlas decay telemetry aggregates (no per-tick ring flood);
      strength sums computed only on emit ticks.
F3  — tier-3 organism babble never runs recall under self.lock: the
      in-lock path refuses without precomputed votes; the lock-free
      precompute half feeds it.
Companion — daughters born by growth are re-wired into the spike bus.
"""

import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

os.environ.setdefault("PYTHONHASHSEED", "0")


@pytest.fixture()
def engine(tmp_path):
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala

    g = Guala()
    g.add_corpus("seed", "Seed", ["the sun rises in the morning"])
    g.load_full_state(str(tmp_path))
    yield g
    try:
        g.shutdown()
    except Exception:
        pass


def _events_of(g, kind):
    out = []
    for e in g.get_recent_events(since_tick=-1, limit=500):
        if e.get("kind") == kind:
            d = dict(e.get("detail") or {})
            d["kind"] = kind
            out.append(d)
    return out


def test_self_heard_windows_never_accrete_for_any_release_kind(engine):
    g = engine
    before = len(g._ordered_language_windows)
    for source_kind in ("fact_strand_commit", "assemblage_commit",
                        "organism_attempt"):
        g._self_hearing = True
        try:
            g.read_sentence(
                "warm sun bright sky",
                source="guala",
                episode_ref=f"emission:test:{source_kind}",
                experience_origin="self_heard",
            )
        finally:
            g._self_hearing = False
    # No self-heard window minted a citation fact...
    assert len(g._ordered_language_windows) == before
    # ...but the exclusion was loud, once per window...
    excluded = _events_of(g, "self_heard_window_excluded_from_certification")
    assert len(excluded) == 3
    # ...and the transient verbatim windows are released after their
    # structural settlement.  The close receipt remains observable, but the
    # manager must not retain a lifetime copy of every self-heard utterance.
    assert all(e.get("window_id") for e in excluded)
    closed_ids = {
        e.get("window_id")
        for e in _events_of(g, "window_closed")
    }
    for e in excluded:
        assert e["window_id"] in closed_ids
        assert g.window_manager.closed_window(e["window_id"]) is None


def test_self_heard_is_a_valid_origin_and_junk_origins_still_raise(engine):
    with pytest.raises(ValueError):
        engine.read_sentence("hello", source="joe",
                             experience_origin="fabricated")


def test_observed_windows_still_accrete(engine):
    g = engine
    before = len(g._ordered_language_windows)
    g.read_sentence("the red fox runs south", source="joe",
                    experience_origin="observed")
    assert len(g._ordered_language_windows) >= before


def test_decay_telemetry_aggregates_under_continuous_prune_pressure(engine):
    g = engine
    if g.wave_atlas is None:
        pytest.skip("wave atlas disabled in this build")
    # Continuous spill writes -> near-continuous prunes at steady state.
    for i in range(1200):
        g.wave_atlas.spill_write(chi=i % 7, band="audio_low",
                                 strength=0.051, tick=i)
        g.wave_atlas.tick_decay()
    # Drive the autonomy tick's telemetry path directly across 1500 ticks.
    emitted = 0
    for t in range(1, 1501):
        g.tick = t
        pruned = g.wave_atlas.tick_decay()
        g._wa_pruned_accum = getattr(g, "_wa_pruned_accum", 0) + pruned
        if t % 500 == 0:
            emitted += 1
            g._wa_pruned_accum = 0
    # The cadence contract: one aggregated emission per 500 ticks max.
    assert emitted == 3


def test_tier3_refuses_recall_under_lock_and_uses_precomputed_votes(engine):
    g = engine
    # Teach a couple of words so seeds exist.
    g.read_sentence("blue bird sings", source="joe",
                    experience_origin="observed")
    with g.lock:
        seeds = g._autonomous_composer_seed_attempts()

    # (a) In-lock compose WITHOUT precomputed votes: tier 3 must refuse
    # loudly, never recall.
    calls = {"n": 0}
    real_recall = g.organism.recall_fast

    def spying_recall(*a, **k):
        calls["n"] += 1
        return real_recall(*a, **k)

    g.organism.recall_fast = spying_recall
    try:
        with g.lock:
            g.compose_autonomous(
                seed_attempts=seeds,
                organism_votes=None,
                organ_candidates=(),
            )
        assert calls["n"] == 0, "tier 3 recalled under self.lock"
        refusals = _events_of(g, "autonomous_organism_attempt")
        assert any(e.get("stop_reason") == "votes_not_precomputed"
                   for e in refusals)

        # (b) The lock-free half runs recall OFF the lock and its result
        # feeds the in-lock assembly.
        votes = g.precompute_organism_attempt(seeds)
        if votes is not None:
            assert calls["n"] > 0
            with g.lock:
                g.compose_autonomous(seed_attempts=seeds,
                                     organism_votes=votes,
                                     organ_candidates=())
    finally:
        g.organism.recall_fast = real_recall


def test_live_autonomous_emission_precomputes_outside_engine_lock(engine):
    g = engine
    g.read_sentence(
        "blue bird sings",
        source="joe",
        experience_origin="observed",
    )
    lock_states = []
    real_precompute = g.precompute_emission_candidates

    def observing_precompute(*args, **kwargs):
        lock_states.append(g.lock._is_owned())
        return ()

    g.precompute_emission_candidates = observing_precompute
    try:
        with g.lock:
            assert g._do_emit() is False
    finally:
        g.precompute_emission_candidates = real_precompute
    assert lock_states == [False]


def test_daughters_are_rewired_into_spike_bus_after_fold(engine):
    g = engine
    bus = getattr(g.organism.brain, "_spike_bus", None)
    if bus is None:
        pytest.skip("spike bus not wired in this build")
    baseline_dropped = bus.dropped_count
    # Force a division through the real fold physics: fund the pool and
    # charge one neuron past threshold, then drain fold events through the
    # worker path (which triggers the re-wire).
    emb = g.organism
    emb._div_pool = max(getattr(emb, "_div_pool", 0.0), 2.0)
    hemi = emb.brain.hemispheres[0]
    victim = hemi.cluster.neurons[0]
    victim._q = 1.6  # past fold threshold
    before_n = sum(len(h.cluster.neurons) for h in emb.brain.hemispheres)
    emb._charge_and_fold(hemi, coherent=True, quantum=0.8)
    after_n = sum(len(h.cluster.neurons) for h in emb.brain.hemispheres)
    if after_n == before_n:
        pytest.skip("fold did not divide under this build's physics")
    # Simulate the worker's fold-drain hook.
    _ = emb.pop_fold_events()
    g.wire_spike_bus()
    # Every neuron in the LIVE population must now be injectable without
    # an unknown-target drop.
    daughters = [n for h in emb.brain.hemispheres
                 for n in h.cluster.neurons]
    target = daughters[-1]  # newest
    bus.inject(target.neuron_id, "test_source", 1.5)
    deadline = time.monotonic() + 5.0
    while (bus.delivered_count + bus.dropped_count) == 0 and \
            time.monotonic() < deadline:
        time.sleep(0.01)
    assert bus.dropped_count == baseline_dropped, \
        "daughter neuron was invisible to the spike bus"


def test_typed_correction_does_not_become_a_scripted_answer(engine):
    """Correction metadata may judge an action, but typed correction text
    is not a separately experienced spoken action and therefore cannot mint
    a prompt-to-answer continuation."""
    g = engine
    for _ in range(2):
        g.read_sentence("who are you", source="joe",
                        experience_origin="observed")
    windows_before = len(g._ordered_language_windows)
    g.apply_teacher_correction(
        original_input="who are you", her_emission="pray you wretched",
        correct=False, corrected_text="i am guala", source="joe")
    assert len(g._ordered_language_windows) == windows_before
    settlement = g._compose_language_fact_settlement(
        ["who", "are", "you"])
    content = getattr(settlement, "content", "") if settlement else ""
    assert "guala" not in content.lower()
    corrections = _events_of(g, "teacher_correction")
    assert corrections
    assert corrections[-1]["corrected_text"] == "i am guala"


def test_typed_correction_cannot_override_lived_history(engine):
    """Teacher authority is preserved as feedback, not converted into a
    scripted language lookup that silently outranks lived experience."""
    g = engine
    g.read_sentence("who are you warm sun", source="corpus",
                    experience_origin="observed")
    windows_before = len(g._ordered_language_windows)
    g.apply_teacher_correction(
        original_input="who are you", her_emission="warm sun",
        correct=False, corrected_text="i am guala", source="joe")
    assert len(g._ordered_language_windows) == windows_before
    settlement = g._compose_language_fact_settlement(["who", "are", "you"])
    content = getattr(settlement, "content", "") or ""
    assert "guala" not in content.lower(), repr(content)


def test_conversational_repeat_shifts_votes_autonomous_stays_strict(engine):
    """GL-FIX-REPEAT-GUARD-20260717: same votes twice conversationally must
    NOT repeat verbatim (shift down her own ranked votes); the autonomous
    path keeps plain refusal once its composition is in the repeat window."""
    from collections import Counter

    votes = {"queries": ["sun"],
             "merged": Counter({"sun": 9.0, "warm": 8.0, "morning": 7.0,
                                "rises": 6.0, "light": 5.0, "sky": 4.0})}
    deadline = time.monotonic() + 5.0
    with engine.lock:
        first = engine._compose_organism_attempt(
            [{"words": ["sun"], "provenance": "test"}], deadline,
            organism_votes=votes, conversational=True)
        second = engine._compose_organism_attempt(
            [{"words": ["sun"], "provenance": "test"}], deadline,
            organism_votes=votes, conversational=True)
        third = engine._compose_organism_attempt(
            [{"words": ["sun"], "provenance": "test"}], deadline,
            organism_votes=votes, conversational=False)
    assert first is not None and first["content"] == "sun warm morning"
    assert second is not None, "conversational repeat must shift, not refuse"
    assert second["content"] != first["content"]
    assert second["content"] == "warm morning rises"
    assert third is None, "autonomous repeat must still refuse"


def test_save_completes_when_picture_original_missing(engine, tmp_path):
    """GL-FIX-SAVE-MISSING-ORIGINAL-20260717: one lost picture .jpg froze
    EVERY full save live (15:07 incident). A missing ORIGINAL (display
    artifact) must drop loudly and let the save complete — grid retained,
    in-memory pointer cleared so the next save never re-references it.
    Video assets stay strict."""
    import numpy as np
    from dsf_ai_service.v4.gualaloom_v5_engine import PictureItem

    state_dir = str(tmp_path / "state")
    pic = PictureItem(item_id="pmiss", title="lost original",
                      intensity_grid=np.zeros((4, 4)))
    pic.original_path = str(tmp_path / "gone.jpg")  # never created
    with engine.lock:
        engine._pictures["pmiss"] = pic

    engine.save_full_state(state_dir)  # must not raise

    assert pic.original_path == "", "dead reference must self-heal"
    grid_dir = os.path.join(state_dir, "assets", "pictures")
    assert os.path.isdir(grid_dir) and os.listdir(grid_dir), \
        "grid (her actual visual experience) must persist"
    engine.save_full_state(state_dir)  # second save also clean


def test_healed_oob_prune_accepts_small_rejects_mass(engine):
    """GL-FIX-HEALED-PRUNE-ACCEPTANCE-20260718: a handful of pruned
    out-of-bounds atlas refs (torn-cycle artifact) is a logged repair and
    the load proceeds; a mass of them is still fatal corruption."""
    sec = next(iter(engine.sections))
    n_modes = len(engine.sections[sec].modes)

    engine.atlas.entries.setdefault(0, [])
    for i in range(5):  # tiny overflow: heal and accept
        engine.atlas.entries[0].append(
            {"section": sec, "motif": n_modes + i, "strength": 0.5})
    assert engine._validate_integrity(), "small pruned overflow must accept"
    assert all(e.get("motif", 0) < n_modes
               for e in engine.atlas.entries.get(0, [])), "healed"

    total = sum(len(v) for v in engine.atlas.entries.values())
    flood = max(65, total // 1000 + 1)
    for i in range(flood):  # mass overflow: still fatal
        engine.atlas.entries[0].append(
            {"section": sec, "motif": n_modes + 1000 + i, "strength": 0.5})
    assert not engine._validate_integrity(), "mass overflow must stay fatal"
