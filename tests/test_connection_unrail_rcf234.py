"""
test_connection_unrail_rcf234.py — GL-SPC-DRIVE-PHYSICS-SUBSTRATE-TRUE-
20260718-v1 RCF-2 + RCF-3 + RCF-4 (Step 3 of the drive-physics
sequencing): connection un-rail.

Gates:
1. tick_drift no longer touches connection (the ~23s wall-clock slide is
   gone); stability/novelty keep their existing drift.
2. _desaturate: asymptotic floor — never crosses below it, at-or-below
   input returned unchanged, zero/negative gain returned unchanged.
3. Set-site gate: solo corpus/curriculum reading can NEVER set
   recent_connection_boost; a genuinely pair-bonded source can; the
   wake-eligible but non-bonded c1 cannot.
4. connection_sig is consumed contact-only: equals the boost, then the
   boost is zeroed — and with no bonded contact it is exactly 0 through
   a real regulate pass (no cross_density structural bias in either
   direction).
5. Erosion physics: connection falls only when real atlas writes happen
   with no bonded companion; zero writes ⇒ exactly zero erosion; bonded
   presence ⇒ exactly zero erosion.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsf_ai_service.v4.gualaloom_v5_engine import (
    Guala, Needs, _desaturate, NEEDS_DRIFT_RATE, CONN_EROSION_PER_WRITE,
)


def test_gate1_tick_drift_leaves_connection_alone():
    print("Gate 1: tick_drift...")
    needs = Needs()
    needs.stability = needs.novelty = needs.connection = 0.7
    for _ in range(1000):
        needs.tick_drift()
    assert needs.connection == 0.7, \
        f"connection must not drift by clock: {needs.connection}"
    assert abs((0.7 - needs.stability) - NEEDS_DRIFT_RATE * 1000) < 1e-9
    assert abs((0.7 - needs.novelty) - NEEDS_DRIFT_RATE * 1000) < 1e-9
    print("  PASS: connection untouched, stability/novelty drift unchanged")


def test_gate2_desaturate_floor_physics():
    print("Gate 2: _desaturate...")
    v = 0.7
    for _ in range(100000):
        v = _desaturate(v, 0.01)
    assert v > 0.05 - 1e-12, f"crossed the floor: {v}"
    assert v < 0.051, f"did not approach the floor: {v}"
    assert _desaturate(0.05, 0.5) == 0.05      # at floor: unchanged
    assert _desaturate(0.0, 0.5) == 0.0        # below floor: never lifted
    assert _desaturate(0.7, 0.0) == 0.7        # zero gain: unchanged
    assert _desaturate(0.7, -0.1) == 0.7       # negative gain: unchanged
    print("  PASS: asymptotic floor, no lift, no zero-gain motion")


def test_gate3_set_site_gated_on_real_bond():
    """A regulate pass can legitimately consume the boost INSIDE the same
    read_sentence call (ticks advance during word processing) — consumed
    means converted into the connection nudge, which is the intended
    physics. So assert the EFFECT: bonded sources push connection up;
    non-bonded sources exert no upward force on it, ever."""
    print("Gate 3: set-site gate...")
    g = Guala()
    g.recent_connection_boost = 0.0

    for src, text in (("corpus", "the cat sat on the mat"),
                      ("curriculum", "one two three four"),
                      ("c1", "hello from c1")):
        before = g.needs.connection
        g.read_sentence(text, source=src)
        assert g.recent_connection_boost == 0.0, \
            f"{src} must never set the contact boost"
        assert g.needs.connection <= before + 1e-12, \
            f"{src} exerted upward force on connection: " \
            f"{before} -> {g.needs.connection}"

    for src in ("joe", "joe_voice"):
        g.recent_connection_boost = 0.0
        before = g.needs.connection
        g.read_sentence("hello little one", source=src)
        registered = (g.recent_connection_boost > 0.0
                      or g.needs.connection > before)
        assert registered, \
            f"bonded source {src} must register as contact " \
            f"(boost={g.recent_connection_boost}, " \
            f"conn {before} -> {g.needs.connection})"
    print("  PASS: corpus/curriculum/c1 exert no upward force; "
          "joe and joe_voice register")


def test_gate4_connection_sig_consumed_contact_only():
    print("Gate 4: consumed connection_sig...")
    g = Guala()

    # No bonded contact: signal must be exactly 0 (no structural bias).
    g.recent_connection_boost = 0.0
    sigs = g.coordinator._read_substrate_signals(g, g.atlas, g.sections)
    assert sigs["connection"] == 0.0, \
        f"no-contact baseline must be exactly 0, got {sigs['connection']}"

    # With contact: signal equals the boost, and the boost is consumed.
    g.recent_connection_boost = 0.12
    sigs = g.coordinator._read_substrate_signals(g, g.atlas, g.sections)
    assert abs(sigs["connection"] - 0.12) < 1e-12
    assert g.recent_connection_boost == 0.0, \
        "boost must be consumed, not decayed on a cadence"
    sigs = g.coordinator._read_substrate_signals(g, g.atlas, g.sections)
    assert sigs["connection"] == 0.0, \
        "consumed signal must not persist into the next pass"
    print("  PASS: exact-0 baseline, consume semantics verified")


def _run_one_awake_tick(g):
    g._autonomy_tick()


def test_gate5_erosion_event_delta_physics():
    print("Gate 5: erosion physics...")
    g = Guala()
    g.add_corpus("book", "Book", ["the cat sat on the mat"])
    # Reach a stable awake READING state.
    for _ in range(50):
        g._autonomy_tick()
    g.needs.connection = 0.5
    g.recent_connection_boost = 0.0

    # (a) zero atlas writes => exactly zero erosion (regulate nudge is 0
    # with boost 0, and tick_drift no longer touches connection).
    g._dp_last_write_count = getattr(g, "_atlas_write_count", 0)
    before = g.needs.connection
    for _ in range(7):     # spans a regulate pass (every 5 ticks)
        g._dp_last_write_count = getattr(g, "_atlas_write_count", 0)
        _run_one_awake_tick(g)
    # Reading a corpus DOES produce real writes; force the zero-write
    # comparison by pinning the delta baseline each tick above. Any
    # change to connection here would be a non-event force.
    assert abs(g.needs.connection - before) < 1e-9, \
        f"zero-write ticks moved connection: {before} -> {g.needs.connection}"

    # (b) real writes with no bonded companion => connection falls.
    before = g.needs.connection
    g._atlas_write_count = getattr(g, "_atlas_write_count", 0) + 10_000
    _run_one_awake_tick(g)
    assert g.needs.connection < before, \
        f"real solo writes must erode connection: {before} -> {g.needs.connection}"
    eroded = before - g.needs.connection
    expected = CONN_EROSION_PER_WRITE * 10_000 * (before - 0.05)
    assert abs(eroded - expected) < expected * 0.5 + 1e-9, \
        f"erosion magnitude off: {eroded} vs ~{expected}"

    # (c) same writes with a bonded companion present => zero erosion.
    g.coordinator._presence["joe"] = True
    g.coordinator._pair_bond["joe"] = True
    before = g.needs.connection
    g._atlas_write_count = getattr(g, "_atlas_write_count", 0) + 10_000
    _run_one_awake_tick(g)
    assert g.needs.connection >= before - 1e-9, \
        f"bonded presence must zero erosion: {before} -> {g.needs.connection}"
    print("  PASS: off-state genuine (zero writes / presence), "
          f"solo erosion real ({eroded:.6f} per 10k writes)")


if __name__ == "__main__":
    test_gate1_tick_drift_leaves_connection_alone()
    test_gate2_desaturate_floor_physics()
    test_gate3_set_site_gated_on_real_bond()
    test_gate4_connection_sig_consumed_contact_only()
    test_gate5_erosion_event_delta_physics()
    print("\nAll RCF-2/3/4 gates pass.")
