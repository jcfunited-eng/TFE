"""
GL-FIX-ONESHOT-REDISTRIBUTION-PROTECTION-C1-20260711

Tests for the one-shot teaching protection window added to
LivingAtlas.record()'s heterosynaptic redistribution -- see that
constant's own docstring in gualaloom_v6_living_atlas.py
(ONE_SHOT_PROTECTION_TICKS) for the full rationale.

Root cause + retention floor this fix targets:
GL-RPT-INDEX-INVARIANT-C1-20260704-163-v1 Part B -- of 10 one-shot
give_experience-taught words, 3 were evicted or near-evicted within
~3562-3717 ticks, quantitatively matched to LivingAtlas.record()'s
heterosynaptic mass-conservation redistribution stealing strength from
co-located taught entries every time an unrelated word was reinforced
at the same chi. Re-confirmed live against this current code
(2026-07-11) via a fresh 10-word/5000-tick harness run: with this fix
absent, 5/10 taught words were FULLY evicted and the survivors were
down to ~4-12% of their teach-time strength -- all well before any
real dream/consolidation cycle ever ran. With this fix, all 10 survive
at their pure-decay-predicted strength (observed vs. predicted total
diverges by 0.00000 at every checkpoint through tick 5000).

Uses LivingAtlas directly (real substrate code, no engine scaffolding)
-- same pattern as test_metadecay_harness.py in this directory.

test_ordinary_binding_redistribution_unchanged is the load-bearing
"physics for non-taught content is untouched" test at unit level; a
separate byte-for-byte A/B comparison against a full Guala() engine run
(corpus-only, 1500 words, 2707 live entries) was also run manually and
confirmed EXACT equality with the pre-fix code -- see the fix's own
commit message for that reproduction.
"""
import math

import pytest

from dsf_ai_service.v4.gualaloom_v6_living_atlas import (
    LivingAtlas, DWELL_GATE_META,
    ONE_SHOT_PROTECTION_TICKS, ONE_SHOT_PROTECTED_SOURCES,
)


def test_ordinary_binding_redistribution_unchanged():
    """Two ordinary (corpus) entries at the same chi: reinforcing one
    must still steal from the other via the exact pre-existing formula.
    Neither entry qualifies for protection (source='corpus')."""
    atlas = LivingAtlas()
    atlas.record("listen", 1, 100, tick=0, salience=0.3, dwell_ticks=1, source="corpus")
    atlas.record("listen", 2, 100, tick=1, salience=0.3, dwell_ticks=1, source="corpus")
    e1 = next(e for e in atlas.entries[100] if e["motif"] == 1)
    e2 = next(e for e in atlas.entries[100] if e["motif"] == 2)
    assert e1["protected_until_tick"] == 0
    assert e2["protected_until_tick"] == 0
    s1_before = e1["strength"]

    atlas.record("listen", 2, 100, tick=2, salience=1.0, dwell_ticks=1, source="corpus")

    assert e1["strength"] < s1_before, (
        "ordinary entry must still lose strength to heterosynaptic redistribution")
    assert e1["strength"] == 0.0, "exact pre-existing formula: fully drained in this scenario"
    assert e2["strength"] == 1.0
    print("test_ordinary_binding_redistribution_unchanged: PASS")


def test_protected_entry_immune_during_window():
    """A freshly taught (source=joe, dwell=8) entry must NOT lose
    strength when another entry at the same chi is reinforced, while
    inside its protection window."""
    atlas = LivingAtlas()
    atlas.record("listen", 1, 200, tick=0, salience=0.3, dwell_ticks=8, source="joe")
    taught = next(e for e in atlas.entries[200] if e["motif"] == 1)
    assert taught["protected_until_tick"] == ONE_SHOT_PROTECTION_TICKS
    s_before = taught["strength"]

    atlas.record("listen", 2, 200, tick=1, salience=0.3, dwell_ticks=1, source="corpus")
    for i in range(5):
        atlas.record("listen", 2, 200, tick=2 + i, salience=1.0, dwell_ticks=1, source="corpus")

    assert taught["strength"] == s_before, (
        f"protected entry lost strength inside its protection window: "
        f"{s_before} -> {taught['strength']}")
    print("test_protected_entry_immune_during_window: PASS")


def test_protected_entry_pays_after_window_expires():
    """Same setup, but reinforcement happens AFTER protected_until_tick
    -- the taught entry must resume paying heterosynaptic tax exactly
    like an ordinary entry (bounded, reversible immunity, not permanent)."""
    atlas = LivingAtlas()
    atlas.record("listen", 1, 300, tick=0, salience=0.3, dwell_ticks=8, source="joe")
    taught = next(e for e in atlas.entries[300] if e["motif"] == 1)
    s_before = taught["strength"]
    expiry = taught["protected_until_tick"]

    atlas.record("listen", 2, 300, tick=1, salience=0.3, dwell_ticks=1, source="corpus")
    atlas.record("listen", 2, 300, tick=expiry + 1, salience=1.0, dwell_ticks=1, source="corpus")

    assert taught["strength"] < s_before, (
        "protected entry must resume paying redistribution tax once its window expires")
    print("test_protected_entry_pays_after_window_expires: PASS")


def test_protection_not_renewed_on_reinforcement():
    """Re-teaching (reinforcing) the SAME taught entry must NOT push
    protected_until_tick forward -- creation-time only, by design (see
    the constant's docstring: 'never renewed on later touches')."""
    atlas = LivingAtlas()
    atlas.record("listen", 1, 400, tick=0, salience=0.3, dwell_ticks=8, source="joe")
    taught = next(e for e in atlas.entries[400] if e["motif"] == 1)
    expiry_1 = taught["protected_until_tick"]

    atlas.record("listen", 1, 400, tick=100, salience=0.3, dwell_ticks=8, source="joe")

    assert taught["protected_until_tick"] == expiry_1, (
        "protection window must not be renewed/extended on reinforcement")
    print("test_protection_not_renewed_on_reinforcement: PASS")


def test_self_heard_speech_not_protected():
    """source='guala' (self-heard speech) carries dwell_ticks=4 in
    production (>= DWELL_GATE_META) but is deliberately NOT in
    ONE_SHOT_PROTECTED_SOURCES -- protection is for deliberately-
    attended teaching specifically, not every dwell>=4 write."""
    assert "guala" not in ONE_SHOT_PROTECTED_SOURCES
    atlas = LivingAtlas()
    atlas.record("listen", 1, 500, tick=0, salience=0.3, dwell_ticks=DWELL_GATE_META, source="guala")
    e = next(e for e in atlas.entries[500] if e["motif"] == 1)
    assert e["protected_until_tick"] == 0
    print("test_self_heard_speech_not_protected: PASS")


def test_low_dwell_interactive_source_not_protected():
    """source='joe' but dwell_ticks below DWELL_GATE_META is not
    protected -- both conditions (interactive source AND attended
    dwell) are required, matching an actual give_experience/chat commit
    rather than any caller that merely labels itself 'joe'."""
    atlas = LivingAtlas()
    atlas.record("listen", 1, 600, tick=0, salience=0.3, dwell_ticks=1, source="joe")
    e = next(e for e in atlas.entries[600] if e["motif"] == 1)
    assert e["protected_until_tick"] == 0
    print("test_low_dwell_interactive_source_not_protected: PASS")


def test_kill_switch_restores_legacy_behavior(monkeypatch):
    """ONE_SHOT_PROTECTED_ENABLED=0 must restore the exact pre-fix
    redistribution behavior, including for taught content -- an instant
    live rollback path, same convention as META_DECAY_ENABLED/
    REORGANIZE_ENABLED elsewhere in this codebase."""
    monkeypatch.setenv("ONE_SHOT_PROTECTED_ENABLED", "0")
    atlas = LivingAtlas()
    atlas.record("listen", 1, 700, tick=0, salience=0.3, dwell_ticks=8, source="joe")
    taught = next(e for e in atlas.entries[700] if e["motif"] == 1)
    assert taught["protected_until_tick"] == 0, "kill switch must suppress the field being set"
    s_before = taught["strength"]

    atlas.record("listen", 2, 700, tick=1, salience=0.3, dwell_ticks=1, source="corpus")
    atlas.record("listen", 2, 700, tick=2, salience=1.0, dwell_ticks=1, source="corpus")

    assert taught["strength"] < s_before, "kill switch must restore full theft-vulnerability"
    print("test_kill_switch_restores_legacy_behavior: PASS")


def test_decay_untouched_for_protected_entries():
    """decay() itself is not modified by this fix at all -- a protected
    entry must decay via the exact same two-speed metaplastic formula as
    an otherwise-identical unprotected entry (protected_until_tick plays
    no role anywhere in decay())."""
    atlas_a = LivingAtlas()
    atlas_a.record("listen", 1, 800, tick=0, salience=0.3, dwell_ticks=8, source="joe")
    taught = next(e for e in atlas_a.entries[800] if e["motif"] == 1)

    atlas_b = LivingAtlas()
    atlas_b.record("listen", 1, 800, tick=0, salience=0.3, dwell_ticks=8, source="corpus")
    twin = next(e for e in atlas_b.entries[800] if e["motif"] == 1)

    assert taught["strength"] == twin["strength"]
    assert taught["protected_until_tick"] != twin["protected_until_tick"]  # only diff

    atlas_a.decay(current_tick=1_000_000)
    atlas_b.decay(current_tick=1_000_000)

    assert math.isclose(taught["strength"], twin["strength"], rel_tol=1e-12), (
        "decay() must treat protected and unprotected entries identically")
    print("test_decay_untouched_for_protected_entries: PASS")


def test_backward_compat_missing_field_treated_as_unprotected():
    """An entry loaded from a pre-fix persisted snapshot (guala_atlas.json
    written before this fix shipped) has no protected_until_tick key at
    all -- must behave exactly as an explicitly-unprotected (0) entry,
    never crash on the missing key."""
    atlas = LivingAtlas()
    atlas.record("listen", 1, 900, tick=0, salience=0.3, dwell_ticks=8, source="joe")
    legacy_entry = next(e for e in atlas.entries[900] if e["motif"] == 1)
    del legacy_entry["protected_until_tick"]  # simulate pre-fix persisted state
    s_before = legacy_entry["strength"]

    atlas.record("listen", 2, 900, tick=1, salience=0.3, dwell_ticks=1, source="corpus")
    atlas.record("listen", 2, 900, tick=2, salience=1.0, dwell_ticks=1, source="corpus")

    assert legacy_entry["strength"] < s_before, (
        "entries missing the field must be treated as unprotected, not crash or get skipped")
    print("test_backward_compat_missing_field_treated_as_unprotected: PASS")


def test_protection_is_victim_side_only():
    """A protected taught entry that is ITSELF reinforced must still
    draw from unprotected neighbors normally -- protection is a shield,
    not a sword. No extra offensive power granted."""
    atlas = LivingAtlas()
    atlas.record("listen", 1, 1000, tick=0, salience=0.3, dwell_ticks=8, source="joe")
    taught = next(e for e in atlas.entries[1000] if e["motif"] == 1)

    atlas.record("listen", 2, 1000, tick=1, salience=0.3, dwell_ticks=1, source="corpus")
    other = next(e for e in atlas.entries[1000] if e["motif"] == 2)
    s_other_before = other["strength"]

    # Re-teach/reinforce the protected entry itself.
    atlas.record("listen", 1, 1000, tick=2, salience=1.0, dwell_ticks=8, source="joe")

    assert other["strength"] < s_other_before, (
        "a protected entry's OWN reinforcement must still draw from "
        "unprotected neighbors exactly as before this fix")
    print("test_protection_is_victim_side_only: PASS")


def test_ordinary_neighbor_loss_unaffected_by_coexisting_protected_entry():
    """Adversarial check (caught by self-review of an earlier version of
    this fix): an ORDINARY entry sharing a chi with a PROTECTED entry
    must lose exactly what it would have lost had the protected entry
    been an ordinary (unprotected) twin instead -- the exempted entry's
    share must go uncollected, NOT get redistributed/concentrated onto
    remaining ordinary neighbors. That earlier version computed
    total_other/share over payers only, which made every ordinary
    entry at a mixed chi pay MORE than the pre-fix formula gives it,
    purely because of who else happened to share the address. This
    compares a mixed (protected + ordinary) chi against a fully-ordinary
    control chi with a same-strength twin standing in for the protected
    entry, and requires the surviving ordinary entry's final strength to
    match exactly."""
    # Mixed chi: A (protected, strength 0.5) + B (ordinary, 0.1) + C (ordinary, 0.5).
    atlas = LivingAtlas()
    atlas.record("listen", 1, 1100, tick=0, salience=0.5, dwell_ticks=8, source="joe")
    atlas.record("listen", 2, 1100, tick=1, salience=0.1, dwell_ticks=1, source="corpus")
    atlas.record("listen", 3, 1100, tick=2, salience=0.5, dwell_ticks=1, source="corpus")
    C_mixed = next(e for e in atlas.entries[1100] if e["motif"] == 3)
    atlas.record("listen", 2, 1100, tick=3, salience=0.2, dwell_ticks=1, source="corpus")

    # Control chi: same B/C, but A's stand-in (motif 9) is ordinary, not protected.
    control = LivingAtlas()
    control.record("listen", 9, 1200, tick=0, salience=0.5, dwell_ticks=1, source="corpus")
    control.record("listen", 2, 1200, tick=1, salience=0.1, dwell_ticks=1, source="corpus")
    control.record("listen", 3, 1200, tick=2, salience=0.5, dwell_ticks=1, source="corpus")
    C_control = next(e for e in control.entries[1200] if e["motif"] == 3)
    control.record("listen", 2, 1200, tick=3, salience=0.2, dwell_ticks=1, source="corpus")

    assert math.isclose(C_mixed["strength"], C_control["strength"], rel_tol=1e-12), (
        f"ordinary neighbor's loss changed due to a co-located protected "
        f"entry: mixed={C_mixed['strength']!r} control={C_control['strength']!r}")
    print("test_ordinary_neighbor_loss_unaffected_by_coexisting_protected_entry: PASS")


if __name__ == "__main__":
    test_ordinary_binding_redistribution_unchanged()
    test_protected_entry_immune_during_window()
    test_protected_entry_pays_after_window_expires()
    test_protection_not_renewed_on_reinforcement()
    test_self_heard_speech_not_protected()
    test_low_dwell_interactive_source_not_protected()
    test_decay_untouched_for_protected_entries()
    test_backward_compat_missing_field_treated_as_unprotected()
    test_protection_is_victim_side_only()
    test_ordinary_neighbor_loss_unaffected_by_coexisting_protected_entry()
    print("ALL PASS (run via pytest for the monkeypatch-based kill-switch test)")
