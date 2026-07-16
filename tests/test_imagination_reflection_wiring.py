"""
GL-CMD-SINGLE-STACK-ALL-LIVE-20260716 (organ 1): imagination + reflection
wired into the live activity loop.

Embryo.imagine()/reflect() were built + tested 2026-07-11 and called by
NOTHING. This proves the wiring:
  - imagine() runs from the PLAYING tick (interval) and from the dream
    cycle, and its output lands as a real imagination_formed event;
  - reflect() runs at the activity boundary (_end_activity) and lands as
    a real organism_reflection event (honest empty=True when the bounded
    snapshot history hasn't accrued yet);
  - imagined content re-enters as real experience tagged
    origin='imagined' and is EXCLUDED from language-fact accretion (the
    certified composer's corpus) with a loud exclusion event -- imagined
    content never certifies as lived fact for speech.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SUBSTRATE_MODE", "embedded")

from dsf_ai_service.v4.gualaloom_v5_engine import Guala  # noqa: E402


def _event_kinds(g):
    return [ev.kind for ev in g._substrate_events]


def _events(g, kind):
    return [ev for ev in g._substrate_events if ev.kind == kind]


def test_imagined_origin_is_real_experience_but_never_certifies():
    g = Guala()
    try:
        facts_before = len(g.language_fact_memory)
        g.read_sentence("blue river", source="imagination",
                        experience_origin="imagined")
        # The window closed as real experience...
        assert len(g.language_fact_memory) == facts_before, (
            "imagined content accreted into language-fact memory -- it "
            "would be citable as lived fact for certified speech")
        excl = _events(g, "imagined_window_excluded_from_certification")
        assert excl, ("no loud exclusion event -- the imagined window was "
                      "either silently swallowed or silently certified")
        assert excl[-1].detail.get("window_id"), (
            "exclusion event carries no window id -- the imagined window "
            "did not actually close/persist as experience")

        # Control: the same sentence as lived (emulated) experience DOES
        # accrete -- proving the gate discriminates on origin, not text.
        g.read_sentence("blue river", source="test",
                        experience_origin="emulated")
        assert len(g.language_fact_memory) > facts_before, (
            "control failed: an emulated window did not accrete facts, "
            "so the imagined assertion above proves nothing")
        print("test_imagined_origin_is_real_experience_but_never_certifies: "
              "PASS")
    finally:
        g.shutdown()


def test_meaning_origins_do_not_contain_imagined():
    from dsf_ai_service.substrate.language_fact_strand import MEANING_ORIGINS
    assert "imagined" not in MEANING_ORIGINS, (
        "MEANING_ORIGINS gained 'imagined' -- imagined content would "
        "certify as lived fact; this must never happen")
    print("test_meaning_origins_do_not_contain_imagined: PASS")


def test_imagine_tick_logs_event_even_when_young():
    g = Guala()
    try:
        g._organism_imagine_tick(context="play")
        formed = _events(g, "imagination_formed")
        assert formed, "no imagination_formed event from an imagine tick"
        ev = formed[-1]
        assert ev.detail["context"] == "play"
        assert "n_pairs" in ev.detail and "duration_ms" in ev.detail
        print("test_imagine_tick_logs_event_even_when_young: PASS "
              f"(n_pairs={ev.detail['n_pairs']})")
    finally:
        g.shutdown()


def test_playing_tick_triggers_imagination_at_interval():
    g = Guala()
    try:
        from dsf_ai_service.v4.gualaloom_v5_engine import Activity
        g.tick = g.IMAGINE_PLAY_INTERVAL_TICKS * 2  # off the %300 emission mark? interval is the trigger
        a = Activity(kind="PLAYING", target=None,
                     started_tick=g.tick,
                     expected_end_tick=g.tick + 1500)
        with g.lock:
            g._atick_playing(a)
        assert _events(g, "imagination_formed"), (
            "PLAYING tick at the imagine interval did not run imagination")
        print("test_playing_tick_triggers_imagination_at_interval: PASS")
    finally:
        g.shutdown()


def test_dream_cycle_triggers_imagination():
    g = Guala()
    try:
        g.tick = 200  # _run_dream_cycle's own %200 gate
        with g.lock:
            g._run_dream_cycle(caller_kind="DREAMING")
        assert _events(g, "imagination_formed"), (
            "an executed dream cycle did not run imagination")
        assert _events(g, "imagination_formed")[-1].detail["context"] == "dream"
        print("test_dream_cycle_triggers_imagination: PASS")
    finally:
        g.shutdown()


def test_activity_end_triggers_reflection():
    g = Guala()
    try:
        from dsf_ai_service.v4.gualaloom_v5_engine import Activity
        g._current_activity = Activity(kind="DREAMING", target=None,
                                       started_tick=0,
                                       expected_end_tick=10)
        with g.lock:
            g._end_activity()
        refl = _events(g, "organism_reflection")
        assert refl, "activity end (dream end) produced no reflection event"
        ev = refl[-1]
        assert ev.detail["boundary"] == "activity_end:DREAMING"
        # A young organism has no snapshot history yet -- honesty check:
        # empty must be reported as empty, never fabricated as a delta.
        assert "empty" in ev.detail
        print("test_activity_end_triggers_reflection: PASS "
              f"(empty={ev.detail['empty']})")
    finally:
        g.shutdown()


if __name__ == "__main__":
    test_imagined_origin_is_real_experience_but_never_certifies()
    test_meaning_origins_do_not_contain_imagined()
    test_imagine_tick_logs_event_even_when_young()
    test_playing_tick_triggers_imagination_at_interval()
    test_dream_cycle_triggers_imagination()
    test_activity_end_triggers_reflection()
    print("ALL PASS: test_imagination_reflection_wiring")
