"""
GL-CMD-CROSS-SENSE-RECALL-EXPOSE: end-to-end verification that
give_experience's HTTP response now surfaces the cross-modal content
RecallEngine.query() was already computing (recall_query.py, ~lines
62-133) and app.py's /bundle: handler was discarding (previously only
`window_ids`/`top_affect_strength` reached the response).

Real, integration-style test -- same pattern as
test_debug_stdp_state.py: a real Guala() boot (not production state)
plus the actual FastAPI route via TestClient. No mocks of RecallEngine,
WindowManager, or the atlas.

Scenario:
  1. Establish one explicit observed test experience containing word +
     sight + sound + touch entries together.  This does not invoke a
     vocabulary recognizer or manufacture object labels from sensory data.
  2. POST /bundle: a SOUND-ONLY cue (a referenced sound item whose
     stored winding is engineered to equal the same chi=16 the first
     bundle's sound modality used) -- a single-lane bundle, so
     _decode_bundle infers section_hint="sound" the same way a bare
     sound_ref probe would in production.
  3. Assert the second response's `recall` block contains not just
     `windows_returned` (a bare id, already correct pre-fix) but a
     `cross_modal_entries` list surfacing the ORIGINAL window's sight
     entry (chi=31) -- the actual "sound cue retrieves picture" content
     RecallResult.windows[0]['entries'] held all along.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ.setdefault("SUBSTRATE_MODE", "embedded")


def _fresh_guala(event_driven=True):
    """Same helper/pattern as test_debug_stdp_state.py's _fresh_guala:
    sets EVENT_DRIVEN_SUBSTRATE for construction and leaves it set."""
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala
    os.environ["EVENT_DRIVEN_SUBSTRATE"] = "1" if event_driven else "0"
    return Guala()


def _bundle_post(client, name, bundle_dict):
    return client.post(
        "/api/v1/gualaloom",
        json={"command": f"/bundle:{name}", "text": json.dumps(bundle_dict),
              "source": "joe"},
    )


def _establish_observed_ball_window(g, extra_modal_entries=0):
    """Create one explicit observed fixture without semantic recognition.

    mirror_atlas defaults to True here (not the False this fixture used
    before GL-FIX-CHI-INDEX-ELIMINATION-20260720) to match the real bundle-
    upload path in app.py, which never sets mirror_atlas=False -- recall
    now routes chi -> window_id through the atlas's own cross-reference,
    so a fixture that skipped the atlas write would be testing a shape of
    data real uploads never actually produce."""
    g.window_manager.open(
        "test_observed_experience", experience_origin="observed")
    for modality, chi in (("sight", 31), ("sound", 16), ("touch", 25)):
        g.window_manager.add_entry(
            modality=modality,
            section=f"test_{modality}",
            motif_id=chi,
            chi=chi,
            tick=g.tick,
            source_tag="test_observed_fixture",
        )
    for index in range(extra_modal_entries):
        g.window_manager.add_entry(
            modality="smell",
            section="test_smell",
            motif_id=1000 + index,
            chi=1000 + index,
            tick=g.tick,
            source_tag="test_observed_fixture",
        )
    g.read_sentence("ball", source="joe")
    window_id = g.window_manager.close("give_experience_complete")
    g._remember_closed_language_window(window_id)
    return window_id


def test_sound_only_cue_surfaces_sight_entry_from_original_binding():
    """The core scenario: a sound-only give_experience cue must return
    the picture/word content it was bound with, not just a window id."""
    import dsf_ai_service.app as appmod
    from fastapi.testclient import TestClient

    g = _fresh_guala()
    old_guala = appmod._guala
    appmod._guala = g
    try:
        client = TestClient(appmod.app)

        # ── Step 1: establish an explicit observed binding. ──
        window1_id = _establish_observed_ball_window(g)

        closed_windows = g.window_manager.windows
        assert len(closed_windows) == 1, (
            f"expected exactly one closed window after bundle 1, got "
            f"{len(closed_windows)}")
        window1 = closed_windows[window1_id]
        entry_modalities = {e["modality"]: e["chi"] for e in window1["entries"]}
        assert entry_modalities.get("sight") == 31
        assert entry_modalities.get("sound") == 16
        assert entry_modalities.get("touch") == 25

        # ── Step 2: probe with a SOUND-ONLY cue. Seed a referenced sound
        # item (same technique the sound_id reference lane is built for --
        # "Support reference to existing sound", app.py ~line 2540) whose
        # stored winding equals window 1's real sound chi, so the cue's
        # own bundle_chis land on the exact same chi the original
        # binding used. ──
        g._sounds["probe_snd"] = {
            "item_id": "probe_snd", "title": "probe sound",
            "cochlear": {"band0": {"winding": 16, "n_events": 3}},
        }
        r2 = _bundle_post(client, "sound_probe", {"sound_id": "probe_snd"})
        assert r2.status_code == 200, r2.text
        d2 = r2.json()

        assert "recall" in d2, "give_experience response dropped the recall block"
        recall = d2["recall"]

        # Pre-existing fields (backward compatible, unchanged shape).
        assert "query_id" in recall
        assert "top_affect_strength" in recall
        assert window1_id in recall["windows_returned"], (
            f"expected window1 ({window1_id}) in windows_returned, "
            f"got {recall['windows_returned']}")

        # The actual fix: the OTHER-modality content bound in that same
        # window must now be observable, not just the window id.
        assert "cross_modal_entries" in recall
        cross_modal = recall["cross_modal_entries"]
        assert len(cross_modal) > 0, "cross_modal_entries is empty -- fix not effective"

        sight_hits = [e for e in cross_modal
                      if e["modality"] == "sight" and e["chi"] == 31]
        assert sight_hits, (
            f"expected the original binding's sight entry (chi=31) in "
            f"cross_modal_entries, got {cross_modal}")
        assert sight_hits[0]["window_id"] == window1_id

        # The touch entry from the same window should also have ridden
        # along (same real window, same real fix) -- not load-bearing on
        # its own, but strengthens confidence this is the whole window's
        # content, not a one-off special case for sight.
        touch_hits = [e for e in cross_modal
                      if e["modality"] == "touch" and e["chi"] == 25]
        assert touch_hits, f"expected the touch entry (chi=25) too, got {cross_modal}"

        print("test_sound_only_cue_surfaces_sight_entry_from_original_binding: PASS")
    finally:
        appmod._guala = old_guala
        g.shutdown()


def test_cross_modal_entries_exclude_the_cue_itself():
    """Adversarial check: the query's OWN chi (the sound cue just given)
    must not be echoed back inside cross_modal_entries as if it were
    retrieved memory -- that field is for the OTHER content the window
    already held, not a mirror of the input."""
    import dsf_ai_service.app as appmod
    from fastapi.testclient import TestClient

    g = _fresh_guala()
    old_guala = appmod._guala
    appmod._guala = g
    try:
        client = TestClient(appmod.app)
        _establish_observed_ball_window(g)

        g._sounds["probe_snd"] = {
            "item_id": "probe_snd", "title": "probe sound",
            "cochlear": {"band0": {"winding": 16, "n_events": 3}},
        }
        r2 = _bundle_post(client, "sound_probe", {"sound_id": "probe_snd"})
        assert r2.status_code == 200, r2.text
        cross_modal = r2.json()["recall"]["cross_modal_entries"]

        cue_echoes = [e for e in cross_modal if e["chi"] == 16]
        assert not cue_echoes, (
            f"the cue's own chi (16) leaked into cross_modal_entries as "
            f"if it were retrieved content: {cue_echoes}")

        print("test_cross_modal_entries_exclude_the_cue_itself: PASS")
    finally:
        appmod._guala = old_guala
        g.shutdown()


def test_cross_modal_entries_capped_on_a_busy_window():
    """Adversarial check: a window with many entries must not balloon
    the response unboundedly. Seeds extra synthetic entries directly
    onto the already-closed window (same dict shape window_manager.close()
    produces) to exercise the cap deterministically, rather than hoping
    a real bundle happens to produce >25 entries."""
    import dsf_ai_service.app as appmod
    from fastapi.testclient import TestClient

    g = _fresh_guala()
    old_guala = appmod._guala
    appmod._guala = g
    try:
        client = TestClient(appmod.app)
        _establish_observed_ball_window(g, extra_modal_entries=40)

        g._sounds["probe_snd"] = {
            "item_id": "probe_snd", "title": "probe sound",
            "cochlear": {"band0": {"winding": 16, "n_events": 3}},
        }
        r2 = _bundle_post(client, "sound_probe", {"sound_id": "probe_snd"})
        assert r2.status_code == 200, r2.text
        cross_modal = r2.json()["recall"]["cross_modal_entries"]

        assert len(cross_modal) <= 25, (
            f"cross_modal_entries not capped: {len(cross_modal)} entries")
        print("test_cross_modal_entries_capped_on_a_busy_window: PASS "
              f"({len(cross_modal)} entries returned)")
    finally:
        appmod._guala = old_guala
        g.shutdown()


if __name__ == "__main__":
    test_sound_only_cue_surfaces_sight_entry_from_original_binding()
    test_cross_modal_entries_exclude_the_cue_itself()
    test_cross_modal_entries_capped_on_a_busy_window()
    print("ALL PASS: test_give_experience_cross_modal_recall")
