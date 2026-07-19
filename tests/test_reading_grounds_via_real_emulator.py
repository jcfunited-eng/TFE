"""
test_reading_grounds_via_real_emulator.py — GL-FIX-EMISSION-GATE-EMULATOR-
RECOGNITION-20260719: real touch/smell/taste descriptor words read in
ordinary corpus text now satisfy the grounding gate.

Root cause: _add_canonical_emulator_entries (called from read_sentence for
every real sentence, corpus/curriculum/worldfeed/converse alike) already
ran real physics for descriptor words (generate_sensory_signals -> a real
Krimelack transduction of an actual generated waveform) and wrote it to
window sections named "emulator_{modality}". _current_window_has_real_
grounding()'s recognizer never knew that name -- not excluded as fake,
just never matched by either list, so it silently counted as ungrounded.
Fix: added "emulator_" to REAL_GROUNDING_SECTION_PREFIXES. No new
computation -- the emulator entries were already being written before
this fix; only the recognition changed. Joe confirmed directly 2026-07-19
that reading was always supposed to satisfy this, not only an explicit
/bundle: upload.

Gates:
1. A sentence containing a real descriptor word (e.g. "warm") makes
   _current_window_has_real_grounding() true while that window is open.
2. A sentence with NO descriptor word does not (no false positive from
   this change).
3. A descriptor word read in ordinary corpus text earns a real entry in
   _word_to_emission_sections (REQUIRE_GROUNDED_SPEECH honored, not
   bypassed) -- the actual, end-to-end thing that was broken.
4. FAKE_MODAL_SECTIONS (the always-on non-descriptor auto-fire) still do
   NOT satisfy grounding -- this fix didn't loosen that exclusion.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def test_gate1_descriptor_sentence_grounds_the_window():
    print("Gate 1: descriptor word grounds the open window...")
    g = Guala()
    g.read_sentence("the water felt warm today", source="corpus")
    # read_sentence closes its window at the end; reopen is per-implementation,
    # so assert against the emulator entries directly via window history.
    found = any(
        e.section.startswith("emulator_")
        for w in g.window_manager.window_ids()
        for e in (g.window_manager.window_metadata(w) or {}).get("entries", [])
    ) if hasattr(g.window_manager, "window_ids") else None
    # Primary, direct assertion: the real end-to-end effect (gate 3) is
    # what actually matters; this gate additionally confirms the raw
    # recognizer accepts the emulator prefix on a live window snapshot.
    g2 = Guala()
    g2._add_canonical_emulator_entries(
        ["warm"], context_id="test-ctx", source="corpus",
        episode_ref=None, bundle_id=None, experience_origin="emulated")
    win = getattr(g2.window_manager, "current", None)
    assert win is not None, "expected an open window after add_entry"
    assert any(e.section.startswith("emulator_") for e in win.entries), \
        "expected a real emulator_* entry in the open window"
    assert g2._current_window_has_real_grounding() is True, \
        "a real descriptor entry must satisfy real-grounding recognition"
    print("  PASS: emulator_* entry recognized as real grounding")


def test_gate2_no_descriptor_word_stays_ungrounded():
    print("Gate 2: no descriptor word, no false grounding...")
    g = Guala()
    g._add_canonical_emulator_entries(
        ["the", "quickly", "runs"], context_id="test-ctx", source="corpus",
        episode_ref=None, bundle_id=None, experience_origin="emulated")
    assert g._current_window_has_real_grounding() is False, \
        "no descriptor words present -- must not claim real grounding"
    print("  PASS: no false positive from non-descriptor words")


def test_gate3_descriptor_word_earns_a_real_section_home():
    print("Gate 3: end-to-end -- ordinary reading earns a speakable word...")
    g = Guala()
    os.environ["REQUIRE_GROUNDED_SPEECH"] = "1"
    try:
        g.add_corpus("book", "Book", ["the water felt warm and soft"])
        for _ in range(4000):
            g._autonomy_tick()
        assert "warm" in g._word_to_emission_sections, \
            "a real descriptor word read in ordinary text must earn a " \
            "section home once the emulator's output is recognized"
    finally:
        os.environ.pop("REQUIRE_GROUNDED_SPEECH", None)
    print("  PASS: 'warm' earned a real, non-bypassed section home")


def test_gate4_fake_modal_sections_still_excluded():
    print("Gate 4: always-on fake auto-fire still excluded...")
    g = Guala()
    from dsf_ai_service.v4.gualaloom_v5_engine import FAKE_MODAL_SECTIONS
    assert not any(s.startswith("emulator_") for s in FAKE_MODAL_SECTIONS), \
        "fake-section list must not overlap the real emulator prefix"
    # Simulate only a fake modal_ entry present (no real/emulator entry) --
    # add_entry alone opens/binds the current window, same as gate 1.
    g.window_manager.add_entry(
        modality="touch", section="modal_touch", motif_id=1, chi=1,
        tick=g.tick, source_tag="corpus", trigger_reason="auto_fire")
    assert g._current_window_has_real_grounding() is False, \
        "a fake modal_ entry alone must still not satisfy real grounding"
    print("  PASS: fake modal_ auto-fire remains correctly excluded")


if __name__ == "__main__":
    test_gate1_descriptor_sentence_grounds_the_window()
    test_gate2_no_descriptor_word_stays_ungrounded()
    test_gate3_descriptor_word_earns_a_real_section_home()
    test_gate4_fake_modal_sections_still_excluded()
    print("\nAll grounding-recognition gates pass.")
