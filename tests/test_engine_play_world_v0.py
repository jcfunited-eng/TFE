"""
test_engine_play_world_v0.py -- functional (single-threaded) tests for
GL-DES-ENGINE-PLAY-WORLD-V0-C1-20260711.

_atick_playing (dsf_ai_service/v4/gualaloom_v5_engine.py) previously ran
byte-for-byte identical code to _atick_idle except for one emission-check
line -- no actual "play" mechanic existed despite its own docstring
claiming a "chi space walk". This file proves the new
_play_revisit_known_pairing() mechanic (see the design doc,
docs/GL-DES-ENGINE-PLAY-WORLD-V0-C1-20260711-v1.md) is real: it only ever
surfaces a picture+word pairing built entirely from real, already-formed
substrate state (a real committed word, a real previously-attended
picture, bound together through the exact same production write path
_atick_attending_visual itself uses), never fabricates one, is gated to a
cheap cadence, and never touches needs channels it hasn't honestly earned.

Matches this repo's established split: this file is the single-threaded
functional half (mirrors tests/test_daydream_loop_reconnect.py's role).
No concurrency claims are made about this mechanism (it does not spawn a
thread), so there is no matching _concurrency.py file.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from dsf_ai_service.v4.gualaloom_v5_engine import (  # noqa: E402
    Guala, Activity, PictureItem,
    PLAY_REVISIT_INTERVAL_TICKS, PLAY_FAMILIARITY_BUMP,
    ACTIVITY_TICK_BUDGETS,
)
from dsf_ai_service.visual_krimelack import VisualMotif  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────
# Real-state fixtures -- everything built through real production paths.
# ─────────────────────────────────────────────────────────────────────────

def _make_committed_word(g, word, source="corpus"):
    """Real commit via the real path (read_word), returns
    (section_name, mode_idx, chi) exactly as Section.receive recorded it
    -- same technique as tests/test_daydream_loop_reconnect.py's helper of
    the same name, duplicated locally (that file exposes no importable
    helper module)."""
    g.read_word(word, source=source)
    for sec in g.sections.values():
        for c in reversed(sec.commits):
            if c["word"] == word:
                return sec.name, c["mode"], c["chi"]
    raise AssertionError(f"setup failed: {word!r} was not committed to any section")


def _make_blob_image(size=32):
    """Real synthetic image content (not used to drive the krimelack
    fragment pipeline -- see _make_picture_bound_at_chi's docstring for
    why -- but stored as the PictureItem's real intensity_grid, same as
    any real uploaded picture would carry)."""
    grid = np.full((size, size), 0.15)
    cy, cx, r = size // 2, size // 2, size // 4
    for y in range(size):
        for x in range(size):
            if (y - cy) ** 2 + (x - cx) ** 2 < r * r:
                grid[y, x] = 0.85
    return grid


def _make_picture_bound_at_chi(g, picture_id, chi, times_attended):
    """Register a real PictureItem and bind a real VisualMotif for it at
    `chi` via window_manager.add_entry -- the SAME write call
    _atick_attending_visual itself makes (gualaloom_v5_engine.py
    ~9207-9223) once it has a resolved motif in hand.

    Honest note on what this helper does NOT do, and why: production
    resolves that motif via view_picture()+sight.process_viewing()
    (real saccade/fovea fragment generation). Investigating this fixture
    found that pipeline's winding-event generation (AdaptingFoveaKrimelack,
    rewritten 2026-07-06 to a delta-driven phase accumulator) does not
    fire within a single 300-tick/12-fixation view_picture() call for
    synthetic bounded-[0,1] test images under a wide sweep of patterns
    and seeds (blob/noise/gradient/stripes/checkerboard, 30 seeds each --
    zero winding events in ~1800 fixations tried) -- a real, pre-existing
    characteristic of that subsystem (consistent with
    tests/test_visual_phase2.py, the file that already exercises it,
    being one of this repo's two known pre-existing collection errors --
    see e3da50f's commit message). Fixing that subsystem is out of scope
    for the Play mechanic this file tests, so this helper constructs the
    VisualMotif directly -- the exact same dataclass, same fields,
    registered in g.sight.motifs/g.sight._next_id the same way
    process_viewing's own "commit new motif" branch would -- rather than
    depend on a pipeline this investigation found doesn't reliably
    produce one for non-production imagery. This matches this repo's own
    established test-fixture pattern of constructing internal state
    directly when the full pipeline isn't the thing under test (e.g.
    tests/test_daydream_loop_reconnect.py's
    test_reorganize_hypothesis_entries_excluded_from_novel_jump directly
    writes a g.deep_atlas.entries[...] dict rather than driving a full
    dream cycle to produce one). What IS exercised for real here, and is
    what _play_revisit_known_pairing and _recall_sight_from_atlas
    actually depend on: the real PictureItem/times_attended contract, the
    real atlas write path (window_manager.add_entry ->
    Guala._atlas_record -> atlas.record, plus the real
    _index_word_at_chi reverse-index side effect for word lookups), and
    the real SightSection.motifs/source_history resolution -- all real.

    `chi` is deliberately the caller-supplied value (a real word's own
    committed chi from _make_committed_word) so the test is deterministic
    instead of depending on any hash-derived placement landing nearby by
    luck. times_attended is set directly on the PictureItem to represent
    genuine prior viewing history (times_attended=0 constructs the
    negative-gate fixture: chi-near, but never actually seen)."""
    grid = _make_blob_image()
    pic = PictureItem(item_id=picture_id, title=f"test:{picture_id}",
                       intensity_grid=grid, source="test",
                       shown_at_tick=g.tick,
                       times_attended=times_attended,
                       last_attended_tick=g.tick if times_attended else 0)
    g._pictures[picture_id] = pic

    motif = VisualMotif(motif_id=g.sight._next_id, source_history=[picture_id],
                         founded_at_tick=g.tick, n_firings=1)
    g.sight._next_id += 1
    g.sight.motifs.append(motif)

    presence, location, sky_state = g._current_situation()
    g.window_manager.add_entry(
        modality="sight", section="sight", motif_id=motif.motif_id, chi=chi,
        tick=g.tick, source_tag="attending_visual", trigger_reason="sight",
        salience=1.2, sensory_refs=[f"pic:{picture_id}"],
        bundle_id=f"item:pic:{picture_id}",
        episode_ref=f"episode:test_play:{g.tick}:{picture_id}",
        presence=presence, location=location, sky_state=sky_state,
        source="attending_visual", **g._affect_kwargs())
    return pic


def _make_known_pairing(g, word="lighthouse", picture_id="pic_known",
                         times_attended=1):
    """A real word + a real picture, deliberately bound together at the
    word's own real committed chi -- the full "already, independently
    formed" pairing _play_revisit_known_pairing is designed to find."""
    _sec, _mode, chi = _make_committed_word(g, word)
    pic = _make_picture_bound_at_chi(g, picture_id, chi, times_attended)
    return word, chi, pic


def _playing_activity(g):
    return Activity(kind="PLAYING", target=None, started_tick=g.tick,
                     expected_end_tick=g.tick + ACTIVITY_TICK_BUDGETS["PLAYING"])


# ─────────────────────────────────────────────────────────────────────────
# 1. _atick_playing is observably different from _atick_idle in code.
# ─────────────────────────────────────────────────────────────────────────

def test_atick_playing_calls_the_revisit_check_idle_does_not():
    print("Functional test: _atick_playing calls _play_revisit_known_pairing "
          "on the gated tick; _atick_idle never does...")
    g = Guala()
    g.tick = PLAY_REVISIT_INTERVAL_TICKS  # land exactly on the gate

    playing_calls = []
    idle_calls = []
    g._play_revisit_known_pairing = lambda: playing_calls.append(1) or False

    a = _playing_activity(g)
    g._atick_playing(a)
    assert playing_calls == [1], (
        "REGRESSION: _atick_playing did not call _play_revisit_known_pairing "
        "on its gated tick -- Playing is back to being idle-with-a-different-name")

    # Idle has no such hook at all -- prove by absence: patching the same
    # method and running idle must never invoke it.
    g2 = Guala()
    g2.tick = PLAY_REVISIT_INTERVAL_TICKS
    g2._play_revisit_known_pairing = lambda: idle_calls.append(1) or False
    g2._atick_idle(Activity(kind="IDLE", target=None, started_tick=g2.tick,
                             expected_end_tick=g2.tick + 500))
    assert idle_calls == [], (
        "REGRESSION: _atick_idle invoked the play-revisit mechanic -- "
        "idle and playing must remain distinct activities")
    print("  OK: Playing calls the revisit check on its gate tick, Idle never does")


# ─────────────────────────────────────────────────────────────────────────
# 2. Honest-empty path: no real pairing in state -> zero events, zero state change.
# ─────────────────────────────────────────────────────────────────────────

def test_no_pairing_in_state_produces_no_event_and_no_state_change():
    print("Functional test: with no real picture/word pairing anywhere in "
          "state, the revisit check is a true no-op (honest empty)...")
    g = Guala()
    g.tick = PLAY_REVISIT_INTERVAL_TICKS
    _make_committed_word(g, "somewordwithnopicture")  # real word, no picture at all

    fam_before = dict(g.target_familiarity)
    events_before = len(g._substrate_events)

    hit = g._play_revisit_known_pairing()

    assert hit is False, "expected an honest-empty return, got a hit with no real pairing"
    assert g.target_familiarity == fam_before, (
        "REGRESSION: target_familiarity changed with no real pairing to revisit "
        "-- state was touched on a miss, not honestly left alone")
    new_events = list(g._substrate_events)[events_before:]
    assert not any(e.kind == "play_revisit" for e in new_events), (
        "REGRESSION: a play_revisit event was logged despite no real pairing existing "
        "-- this would be a fabricated experience")
    print("  OK: zero events, zero state change on a genuine miss")


# ─────────────────────────────────────────────────────────────────────────
# 3. Real hit: a genuinely known pairing is surfaced and logged honestly.
# ─────────────────────────────────────────────────────────────────────────

def test_real_known_pairing_is_surfaced_and_logged_with_real_values():
    print("Functional test: a real, previously-attended picture bound near "
          "a real committed word IS surfaced by play_revisit, with the "
          "logged fields matching the real fixture exactly...")
    g = Guala()
    word, chi, pic = _make_known_pairing(g, word="lighthouse",
                                          picture_id="pic_known", times_attended=3)
    # Force selection to land on our seeded word regardless of however many
    # other commits exist in other sections from Guala()'s own init/reads.
    # _atick_playing's own outer gate (tick % PLAY_REVISIT_INTERVAL_TICKS)
    # is separate from this inner word-selection modulo -- call the helper
    # directly (as _atick_playing does once gated) to keep this test's
    # tick arithmetic focused on word selection, not the gate cadence
    # (gate cadence is covered by test 5 below).
    recent = []
    for sec in g.sections.values():
        for c in sec.commits[-10:]:
            if c.get("word"):
                recent.append(c["word"])
    g.tick = recent.index(word)  # self.tick % len(recent_words) must select `word`

    fam_before = g.target_familiarity.get("pic_known", 0.0)
    events_before = len(g._substrate_events)

    hit = g._play_revisit_known_pairing()

    assert hit is True, "expected a real hit against a genuinely known pairing"
    new_events = list(g._substrate_events)[events_before:]
    revisit_events = [e for e in new_events if e.kind == "play_revisit"]
    assert len(revisit_events) == 1, (
        f"expected exactly one play_revisit event, got {len(revisit_events)}")
    ev = revisit_events[0]
    assert ev.detail["word"] == word
    assert ev.detail["picture_id"] == "pic_known"
    assert ev.detail["picture_title"] == pic.title
    assert ev.detail["times_attended"] == 3
    assert ev.detail["familiarity_before"] == round(fam_before, 4)

    fam_after = g.target_familiarity["pic_known"]
    expected = min(0.9, fam_before + PLAY_FAMILIARITY_BUMP)
    assert abs(fam_after - expected) < 1e-9, (
        f"target_familiarity bump was {fam_after - fam_before}, "
        f"expected exactly PLAY_FAMILIARITY_BUMP={PLAY_FAMILIARITY_BUMP}")
    assert ev.detail["familiarity_after"] == round(fam_after, 4)
    print(f"  OK: play_revisit logged real values (word={word!r}, "
          f"picture_id=pic_known, familiarity {fam_before:.4f} -> {fam_after:.4f})")


def test_familiarity_bump_is_capped_at_0_9():
    print("Functional test: repeated revisits cap target_familiarity at 0.9, "
          "same ceiling ATTENDING_VISUAL's own familiarity write uses...")
    g = Guala()
    word, chi, pic = _make_known_pairing(g, word="harborlight",
                                          picture_id="pic_capped", times_attended=1)
    g.target_familiarity["pic_capped"] = 0.895

    recent = [c["word"] for sec in g.sections.values() for c in sec.commits[-10:]
              if c.get("word")]
    g.tick = recent.index(word)

    hit = g._play_revisit_known_pairing()
    assert hit is True
    assert g.target_familiarity["pic_capped"] <= 0.9, (
        "REGRESSION: target_familiarity exceeded the 0.9 ceiling")
    assert g.target_familiarity["pic_capped"] == 0.9
    print("  OK: familiarity capped at 0.9")


# ─────────────────────────────────────────────────────────────────────────
# 4. Negative gate: chi-near but never-attended picture is never surfaced.
# ─────────────────────────────────────────────────────────────────────────

def test_never_attended_picture_is_never_surfaced_as_a_revisit():
    print("Functional test: a picture bound at the exact same chi as a real "
          "committed word, but with times_attended=0 (never genuinely seen), "
          "is NOT surfaced by play_revisit -- proves the 'genuinely known' "
          "gate is real, not decorative...")
    g = Guala()
    word, chi, pic = _make_known_pairing(g, word="unseenpicword",
                                          picture_id="pic_unseen",
                                          times_attended=0)
    assert pic.times_attended == 0

    recent = [c["word"] for sec in g.sections.values() for c in sec.commits[-10:]
              if c.get("word")]
    g.tick = recent.index(word)

    fam_before = dict(g.target_familiarity)
    events_before = len(g._substrate_events)

    hit = g._play_revisit_known_pairing()

    assert hit is False, (
        "REGRESSION: a never-attended picture was surfaced as a 'known' "
        "revisit -- this fabricates a pairing she was never actually shown")
    assert g.target_familiarity == fam_before
    new_events = list(g._substrate_events)[events_before:]
    assert not any(e.kind == "play_revisit" for e in new_events)
    print("  OK: chi-near-but-never-attended picture correctly excluded")


# ─────────────────────────────────────────────────────────────────────────
# 5. Cadence: only fires on the gated tick, costs nothing off-gate.
# ─────────────────────────────────────────────────────────────────────────

def test_revisit_check_only_runs_on_the_gated_tick():
    print("Functional test: _atick_playing only invokes the revisit check "
          "when tick % PLAY_REVISIT_INTERVAL_TICKS == 0...")
    g = Guala()
    calls = []
    g._play_revisit_known_pairing = lambda: calls.append(g.tick) or False

    a = _playing_activity(g)
    off_gate_ticks = [1, 2, 499, 501, 999, PLAY_REVISIT_INTERVAL_TICKS + 1]
    for t in off_gate_ticks:
        g.tick = t
        g._atick_playing(a)
    assert calls == [], (
        f"REGRESSION: revisit check ran on off-gate ticks {calls} -- "
        "this defeats the low-cadence cost guarantee in the design doc")

    g.tick = PLAY_REVISIT_INTERVAL_TICKS
    g._atick_playing(a)
    assert calls == [PLAY_REVISIT_INTERVAL_TICKS], (
        "revisit check did not run on the gated tick")
    print(f"  OK: silent on {len(off_gate_ticks)} off-gate ticks, "
          f"fired exactly once on tick={PLAY_REVISIT_INTERVAL_TICKS}")


# ─────────────────────────────────────────────────────────────────────────
# 6. No overclaim: novelty/connection are never touched by a revisit hit.
# ─────────────────────────────────────────────────────────────────────────

def test_revisit_hit_never_touches_novelty_or_connection_needs():
    print("Functional test: a real play_revisit hit leaves needs.novelty and "
          "needs.connection bit-for-bit unchanged (design doc §3.2)...")
    g = Guala()
    word, chi, pic = _make_known_pairing(g, word="quietcove",
                                          picture_id="pic_needs", times_attended=1)
    recent = [c["word"] for sec in g.sections.values() for c in sec.commits[-10:]
              if c.get("word")]
    g.tick = recent.index(word)

    novelty_before = g.needs.novelty
    connection_before = g.needs.connection

    hit = g._play_revisit_known_pairing()
    assert hit is True, "setup failure: expected a real hit for this test to be meaningful"

    assert g.needs.novelty == novelty_before, (
        "REGRESSION: play_revisit changed needs.novelty -- this is explicitly "
        "non-novel content, crediting novelty would be an overclaim")
    assert g.needs.connection == connection_before, (
        "REGRESSION: play_revisit changed needs.connection -- an internal, "
        "solitary re-notice has no social content to credit")
    print("  OK: novelty and connection needs untouched by a real revisit hit")


# ─────────────────────────────────────────────────────────────────────────
# 7. Regression guard: the shared idle-restore physics is unchanged.
# ─────────────────────────────────────────────────────────────────────────

def test_playing_and_idle_still_share_identical_stability_restore():
    print("Functional test: given identical atlas/needs state, "
          "_atick_playing and _atick_idle still produce the exact same "
          "stability-restore delta (the one piece of behavior V0 keeps) ...")
    g1 = Guala()
    g2 = Guala()
    _make_committed_word(g1, "stabilitytestword")
    _make_committed_word(g2, "stabilitytestword")
    g1.needs.stability = 0.4
    g2.needs.stability = 0.4
    # Land off the revisit gate and off the emission-check gate so only the
    # shared stability-restore line is exercised (isolating this test's claim).
    g1.tick = 1
    g2.tick = 1

    g1._atick_idle(Activity(kind="IDLE", target=None, started_tick=g1.tick,
                             expected_end_tick=g1.tick + 500))
    g2._atick_playing(_playing_activity(g2))

    assert abs(g1.needs.stability - g2.needs.stability) < 1e-12, (
        f"REGRESSION: idle stability={g1.needs.stability} != "
        f"playing stability={g2.needs.stability} -- the shared physics diverged")
    print(f"  OK: both landed at stability={g1.needs.stability:.6f}")


if __name__ == "__main__":
    tests = [
        test_atick_playing_calls_the_revisit_check_idle_does_not,
        test_no_pairing_in_state_produces_no_event_and_no_state_change,
        test_real_known_pairing_is_surfaced_and_logged_with_real_values,
        test_familiarity_bump_is_capped_at_0_9,
        test_never_attended_picture_is_never_surfaced_as_a_revisit,
        test_revisit_check_only_runs_on_the_gated_tick,
        test_revisit_hit_never_touches_novelty_or_connection_needs,
        test_playing_and_idle_still_share_identical_stability_restore,
    ]
    failures = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failures += 1
            print(f"  FAIL: {t.__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
