"""GL world-actions-in-process (C1, 2026-07-22): visible autonomy on her
virtual room, ported from the retired :8090 sidecar into the ONE process.

Covers the five ordered proofs:
(a) a DOING verb really applies (shared world_state.json changes on disk)
    and logs a real world_action substrate event;
(b) selection is deterministic from drive state — comfort actions win a
    stability deficit, untouched objects win on freshness, and repeated
    selection with identical state picks identically (no randomness);
(c) the consequence is experienced honestly — the NEW state's
    ambient_words go through read_sentence(source="world"), landing in
    vocab/source_history, never a fabricated sense;
(d) the three dead sidecar pollers are gone (no :8090 / _ob_url /
    ORGAN_BRAIN_URL references left in the live modules);
(e) the organ_brain_status route no longer fabricates
    {"warming": true, "neurons": 0} — it answers honestly gone (410).

Single-threaded functional tests, same shape as
tests/test_engine_play_world_v0.py.
"""

import ast
import json
import os
import sys
import time
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsf_ai_service.v4.gualaloom_v5_engine import (  # noqa: E402
    ACTIVITY_TICK_BUDGETS,
    Activity,
    Guala,
    WORLD_ACTION_COOLDOWN_TICKS,
)

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def guala(monkeypatch, tmp_path):
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("STATE_DIR", str(tmp_path))
    engine = Guala()
    try:
        yield engine
    finally:
        engine.shutdown()


def _events(g, kind):
    return [e for e in g._substrate_events if e.kind == kind]


def _wait_for_saved_state(tmp_dir, timeout=5.0):
    """WorldState._save runs on a background thread — wait for the atomic
    replace to land."""
    path = os.path.join(str(tmp_dir), "world_state.json")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        time.sleep(0.05)
    raise AssertionError("world_state.json was never written")


# ─────────────────────────────────────────────────────────────────────────
# (a) DOING applies the verb to the shared world state and logs it
# ─────────────────────────────────────────────────────────────────────────

def test_doing_verb_applies_and_logs(guala, tmp_path):
    a = Activity(kind="DOING", target="drapes:open",
                 started_tick=guala.tick,
                 expected_end_tick=guala.tick + ACTIVITY_TICK_BUDGETS["DOING"])
    guala._atick_doing(a)

    # Real state change, persisted to the SAME world_state.json every
    # existing world read (/room, _current_situation) uses.
    saved = _wait_for_saved_state(tmp_path)
    assert saved["objects"]["drapes"]["state"] == "open"

    # Real world_action substrate event with verb + resulting state.
    evs = _events(guala, "world_action")
    assert len(evs) == 1
    ev = evs[0].detail
    assert ev["object"] == "drapes"
    assert ev["verb"] == "open"
    assert ev["next_state"] == "open"
    assert ev["trigger"] == "autonomy"
    assert ev["ambient_words"], "resulting ambient state must be recorded"

    # Habituation record + cooldown tick really advanced.
    assert guala._world_actions["drapes:open"]["times_done"] == 1
    assert guala._last_world_action_tick >= a.started_tick


def test_atick_doing_executes_exactly_once_per_activity(guala):
    a = Activity(kind="DOING", target="bell:ring",
                 started_tick=guala.tick,
                 expected_end_tick=guala.tick + ACTIVITY_TICK_BUDGETS["DOING"])
    guala._atick_doing(a)
    guala._atick_doing(a)  # second tick of the same activity
    assert guala._world_actions["bell:ring"]["times_done"] == 1
    assert len(_events(guala, "world_action")) == 1


def test_invalid_verb_is_logged_honestly_and_changes_nothing(guala):
    out = guala.perform_world_action("drapes", "levitate")
    assert out["ok"] is False
    assert not _events(guala, "world_action")
    assert _events(guala, "world_action_invalid")
    assert "drapes:levitate" not in guala._world_actions


# ─────────────────────────────────────────────────────────────────────────
# (b) deterministic, drive-state selection — no randomness, no scripts
# ─────────────────────────────────────────────────────────────────────────

def test_stability_deficit_prefers_comfort_action(guala):
    # Unmet stability, saturated novelty: the drive field itself must
    # steer toward comfort. "lie under" the blanket carries warm/soft/
    # safe/cozy (full comfort overlap); "ring" the bell carries none.
    guala.needs.stability = 0.2
    guala.needs.novelty = 1.0
    comfort = guala._action_salience("DOING", "blanket:lie under")
    sharp = guala._action_salience("DOING", "bell:ring")
    assert comfort > sharp


def test_novelty_prefers_untouched_object(guala):
    # Same object class, same drive state — the heavily-done action must
    # score below the untouched one purely through habituation freshness.
    guala.tick = 10_000
    guala._world_actions["drapes:open"] = {
        "times_done": 50, "last_done_tick": guala.tick}
    done = guala._action_salience("DOING", "drapes:open")
    untouched = guala._action_salience("DOING", "toy_chest:open")
    assert untouched > done


def test_selection_is_deterministic_given_identical_state(guala):
    first = guala._select_next_activity()
    second = guala._select_next_activity()
    assert (first.kind, first.target) == (second.kind, second.target)


def test_doing_candidates_enter_the_shared_selection_field(guala):
    kinds = {k for k, _ in guala._candidate_activities()}
    assert "DOING" in kinds


def test_closed_toy_chest_gates_its_contents(guala):
    targets = guala._world_action_candidates()
    # Chest starts closed: its contents are not reachable.
    assert guala._world_state().get("toy_chest").get("state") == "closed"
    assert not any(t.startswith(("music_box:", "bell:")) for t in targets)
    # Open it for real; the contents become real candidates.
    guala._world_state().apply_verb("toy_chest", "open")
    targets = guala._world_action_candidates()
    assert "music_box:open" in targets
    assert "bell:ring" in targets


def test_cooldown_bounds_action_frequency(guala):
    guala.perform_world_action("drapes", "open")
    assert not guala._world_actions_available()
    assert not any(k == "DOING" for k, _ in guala._candidate_activities())
    guala.tick += WORLD_ACTION_COOLDOWN_TICKS + 1
    assert guala._world_actions_available()


def test_quiet_block_suppresses_new_world_actions(guala, monkeypatch):
    fake_runner = types.SimpleNamespace(_current_block=lambda: "quiet")
    monkeypatch.setitem(sys.modules,
                        "dsf_ai_service.substrate_runner", fake_runner)
    assert not guala._world_actions_available()
    fake_runner._current_block = lambda: "play"
    assert guala._world_actions_available()


# ─────────────────────────────────────────────────────────────────────────
# (c) the consequence is a REAL experience through the real read path
# ─────────────────────────────────────────────────────────────────────────

def test_consequence_read_as_real_world_experience(guala):
    out = guala.perform_world_action("drapes", "open")
    assert out["ok"] is True
    # The words fed were the NEW state's ambient_words — logged in the
    # event and traceable in the substrate as source="world" intake.
    ev = _events(guala, "world_action")[0].detail
    assert ev["ambient_words"] == out["ambient_words"]
    # Opening the drapes (clear weather, any time of day) always yields
    # "fresh" in the room's ambient field.
    assert "fresh" in ev["ambient_words"]
    assert guala.source_history.get("world", 0) >= 1, (
        "consequence must enter through read_sentence(source='world')")
    assert "fresh" in guala.vocab


# ─────────────────────────────────────────────────────────────────────────
# (d) the three dead sidecar pollers are really gone
# ─────────────────────────────────────────────────────────────────────────

def test_no_dead_sidecar_poller_references_remain():
    runner_src = open(os.path.join(
        _REPO, "dsf_ai_service", "substrate_runner.py")).read()
    app_src = open(os.path.join(_REPO, "dsf_ai_service", "app.py")).read()
    assert "ORGAN_BRAIN_URL" not in runner_src
    assert "localhost:8090" not in runner_src
    assert "localhost:8090" not in app_src
    assert "_ob_url" not in app_src
    assert "def _start_organ_surface_poll" not in runner_src
    assert "_start_organ_surface_poll()" not in app_src


# ─────────────────────────────────────────────────────────────────────────
# (e) honest status route — real-or-gone, never fabricated warming
# ─────────────────────────────────────────────────────────────────────────

def _function_source(path, name):
    src = open(path).read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and node.name == name:
            return ast.get_source_segment(src, node)
    raise AssertionError(f"{name} not found in {path}")


def test_organ_brain_status_route_is_honestly_gone():
    body = _function_source(
        os.path.join(_REPO, "dsf_ai_service", "app.py"), "organ_brain_status")
    assert "urlopen" not in body, "route must not poll the dead sidecar"
    assert '"warming": True' not in body, "fabricated warming state must be gone"
    assert "410" in body
    assert '"available": False' in body


def test_thought_route_serves_the_in_process_substrate():
    body = _function_source(
        os.path.join(_REPO, "dsf_ai_service", "app.py"), "organ_thought")
    assert "urlopen" not in body
    assert "_cmd_thought" in body
