"""Tests for GL-FIX-STAGED-SET-FLIP-20260718: all-or-nothing save sets.

Joe's chunked/packet-id design: files carry cycle stamps (existing),
and now the whole set flips in milliseconds at commit — a kill mid-save
can no longer produce the mixed sets that forced four generation
fallbacks in one night."""

import os

import pytest


@pytest.fixture()
def engine(tmp_path):
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala
    g = Guala()
    g.add_corpus("seed", "Seed", ["the sun rises in the morning"])
    g.load_full_state(str(tmp_path / "state"))
    yield g, str(tmp_path / "state")
    try:
        g.shutdown()
    except Exception:
        pass


def test_full_save_flips_complete_set_and_reloads(engine):
    g, state_dir = engine
    g.read_sentence("the cat sat on the mat", source="corpus")
    g.save_full_state(state_dir)
    assert not [f for f in os.listdir(state_dir) if f.endswith(".tmp")], \
        "no staged leftovers after a committed flip"
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala
    g2 = Guala()
    g2.load_full_state(state_dir)
    try:
        assert g2._load_successful, "flipped set must load clean"
    finally:
        try:
            g2.shutdown()
        except Exception:
            pass


def test_aborted_save_leaves_previous_set_untouched(engine):
    g, state_dir = engine
    g.read_sentence("the cat sat on the mat", source="corpus")
    g.save_full_state(state_dir)
    core_before = os.path.getmtime(os.path.join(state_dir, "guala_core.json"))

    g.read_sentence("the dog sat on the rug", source="corpus")
    boom = RuntimeError("simulated kill mid-save")
    original = g._save_full_state_locked

    def _explode(*a, **k):
        # Stage a few real writes, then die before the flip.
        g._atomic_write(os.path.join(state_dir, "guala_needs.json"),
                        {"partial": True})
        raise boom

    g._save_full_state_locked = _explode
    try:
        with pytest.raises(RuntimeError):
            g.save_full_state(state_dir)
    finally:
        g._save_full_state_locked = original

    assert not [f for f in os.listdir(state_dir) if f.endswith(".tmp")], \
        "aborted staged tmps must be removed"
    core_after = os.path.getmtime(os.path.join(state_dir, "guala_core.json"))
    assert core_after == core_before, "previous set untouched on abort"
    import json
    needs = json.load(open(os.path.join(state_dir, "guala_needs.json")))
    assert "partial" not in needs.get("data", needs), \
        "no staged partial file may reach the live set"
