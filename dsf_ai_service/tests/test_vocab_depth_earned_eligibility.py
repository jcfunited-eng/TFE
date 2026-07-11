"""
GL-DES-VOCAB-DEPTH-EARNED-ELIGIBILITY-C1-20260711 Part 1: unit + integration
tests for wiring DeepAtlas.strength into the real-speech eligibility
backfill (_backfill_grounded_from_deep_atlas / _entry_grants_grounding /
_backfill_eligibility_for_promotion).

Context (see docs/GL-DES-VOCAB-DEPTH-EARNED-ELIGIBILITY-C1-20260711-v1.md):
eligibility to ever be spoken (membership in self._word_to_emission_sections)
used to be gated ONLY on real camera/mic/touch/smell/taste co-occurrence at
the moment a word's mode was first created -- a word taught purely through
text (the "ocean" case: read about it, never seen/heard/touched it) could
never become eligible no matter how much real repeated exposure it got.
_backfill_grounded_from_deep_atlas already existed as the retroactive-
grounding mechanism but only ever checked a boolean (co_occurrence
presence), throwing away DeepAtlas's own graduated `strength` value. This
fix adds a SECOND, independent path to grounding: an entry's own
accumulated strength crossing DeepAtlas's existing Path-A survival bar
(ELIGIBILITY_STRENGTH_THETA == SURVIVAL_THETA, reused, not reinvented),
gated behind DEEP_ATLAS_ELIGIBILITY_BACKFILL_ENABLED (default OFF).

Mirrors dsf_ai_service/tests/test_credo_relevance_weight.py's own style and
helpers (_fresh_guala, _ground_word) -- real Guala() boot, real
atlas.record()/deep_atlas.promote()/dream_promotion_gate calls, not
hand-faked weights.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ.setdefault("SUBSTRATE_MODE", "embedded")

ENV_FLAG = "DEEP_ATLAS_ELIGIBILITY_BACKFILL_ENABLED"


def _fresh_guala():
    """Same convention as test_credo_relevance_weight.py's helper."""
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala
    g = Guala()
    g.organism.recall_fast = lambda signal: {"__unrelated_dummy__": 1}
    return g


def _make_mode(g, word, section):
    """Give `word` a mode slot in `section` WITHOUT granting emission
    eligibility (unlike test_credo_relevance_weight.py's _ground_word,
    which deliberately seeds straight into _word_to_emission_sections).
    Returns (chi, mid)."""
    from dsf_ai_service.v4.gualaloom_v5_engine import (
        LanguageKrimelack, deterministic_motif_id,
    )
    k = LanguageKrimelack()
    k.transduce(word)
    chi = k.winding
    mid = deterministic_motif_id(word)
    sec = g.sections[section]
    while len(sec.modes) <= mid:
        sec.modes.append((0, 0, ""))
    sec.modes[mid] = (0, 0, word)
    return chi, mid


def _commit_ungrounded(g, word, section, chi, mid, tick=10):
    """Append a real Section.commits record with grounded=False -- the
    exact shape read_word/Section.receive produces for a word committed
    with no real sensory co-occurrence (see gualaloom_v5_engine.py
    ~line 1588-1594). This is what a purely text-taught word's commit
    history really looks like today."""
    g.sections[section].commits.append({
        "tick": tick, "mode": mid, "chi": chi, "word": word, "grounded": False,
    })


def _teach_via_atlas(g, word, section, chi, mid, tick=10, salience=1.0):
    """Real working-atlas commit for `word` via the real, unmodified
    atlas.record() (source='corpus', i.e. text/reading, never a sensory
    modality) -- salience=1.0 (baseline) saturates a fresh entry's
    strength to STRENGTH_CAP=1.0 in one call (impulse = salience/(1+0)),
    the maximally-strong "read about it repeatedly" case. dwell_ticks=1
    (< deep_atlas.DWELL_GATE) deliberately keeps DeepAtlas's Path B
    (episodic) compound gate closed at teach time -- Path B's OTHER half
    (encoded_strength >= ENCODE_GATE) is already satisfied by any real
    strength this high, so dwell is the only lever available to isolate
    Path A (survival) for tests that need it. Also appends the matching
    Section.commits record (see _commit_ungrounded) so this word has
    real, ordinary (non-grounded) commit history, same as a real
    read_word() call with no sensory co-occurrence would leave behind."""
    g.atlas.record(section, mid, chi, tick=tick, salience=salience,
                   dwell_ticks=1, source="corpus")
    _commit_ungrounded(g, word, section, chi, mid, tick=tick)


def _advance_survival_history_and_promote(g, tick):
    """Mirrors _run_dream_cycle's own survival-history bookkeeping (the
    real per-entry "append this cycle's current strength" loop) then
    calls the REAL, unmodified DeepAtlas.dream_promotion_gate -- still
    100% real DeepAtlas code/thresholds, just without _run_dream_cycle's
    OUTER orchestration (priority-replay sampling + reinforcement, decay,
    reorganize). That orchestration's replay-reinforcement step legitimately
    bumps a sampled entry's dwell_ticks to DWELL_GATE_META (real "dream
    consolidation IS dwell-earning" physics, gualaloom_v5_engine.py's own
    documented design) -- great for realism, but it means Path B (episodic)
    can fire well before 3 cycles for ANY strongly-taught entry that gets
    replay-sampled, which would confound a test aimed specifically at
    Path A (survival)'s real 3-consecutive-dream-cycle requirement. Used
    only by tests that need that isolation; see
    test_ocean_case_end_to_end_via_real_dream_cycle_loop below for the
    complementary test that DOES go through the full, real
    _run_dream_cycle() (Path A or B, whichever legitimately fires first)."""
    g.tick = tick
    for chi_k, entries in g.atlas.entries.items():
        for e in entries:
            key = (chi_k, e.get("section", ""), e.get("motif", 0))
            g._deep_survival_history[key].append(e["strength"])
    return g.deep_atlas.dream_promotion_gate(g.atlas, g.tick, g._deep_survival_history)


def _promote_and_backfill(g, promoted):
    """Exercises the exact same real trigger call _run_dream_cycle/
    _run_dream_cycle_phased make for each promoted entry (see those
    functions' own call sites) -- real _backfill_eligibility_for_promotion,
    just driven by this test file's own promotion loop instead of the
    full dream-cycle orchestration."""
    for path, chi_k, sec, mid in promoted:
        g._backfill_eligibility_for_promotion(chi_k, sec, mid)


def _run_n_dream_cycles(g, n, start_tick=200, step=200):
    """Advance g.tick to successive multiples of 200 (the real
    self.tick % 200 == 0 gate _run_dream_cycle enforces) and call the
    real, unmodified _run_dream_cycle() each time -- this is the actual
    production function (not a reimplementation), matching
    DREAM_CYCLE_PHASED=0 (unset in these tests), the non-phased body.
    Returns the list of `promoted` tuples from the LAST cycle."""
    promoted = []
    for i in range(n):
        g.tick = start_tick + i * step
        # Capture what dream_promotion_gate itself returns this cycle by
        # wrapping it transparently (real call, just observed).
        orig = g.deep_atlas.dream_promotion_gate
        captured = {}

        def _wrap(*a, __orig=orig, **kw):
            r = __orig(*a, **kw)
            captured["r"] = r
            return r
        g.deep_atlas.dream_promotion_gate = _wrap
        try:
            g._run_dream_cycle(caller_kind="DREAMING")
        finally:
            g.deep_atlas.dream_promotion_gate = orig
        promoted = captured.get("r", [])
    return promoted


# ─────────────────────────────────────────────────────────────────────
# Unit-level: _entry_grants_grounding (the single shared decision point)
# ─────────────────────────────────────────────────────────────────────

def test_entry_grants_grounding_has_real_path_unaffected_by_kill_switch():
    """The pre-existing has_real (co_occurrence) path must behave
    IDENTICALLY regardless of the new kill switch's state -- proves the
    fix is additive, never a replacement of the original check."""
    g = _fresh_guala()
    try:
        de_real = {"co_occurrence": {"sight": {"0": 0.5}}, "strength": 0.01}
        de_fake_only = {"co_occurrence": {"modal_sight": {"0": 0.9}}, "strength": 0.01}
        for flag in ("0", "1"):
            os.environ[ENV_FLAG] = flag
            assert g._entry_grants_grounding(de_real) is True, flag
            assert g._entry_grants_grounding(de_fake_only) is False, flag
        print("test_entry_grants_grounding_has_real_path_unaffected_by_kill_switch: PASS")
    finally:
        os.environ.pop(ENV_FLAG, None)
        g.shutdown()


def test_entry_grants_grounding_strength_path_off_by_default():
    """A high-strength, fully-promoted-looking entry with NO real
    co_occurrence must NOT grant grounding while the kill switch is at
    its default (unset -> OFF)."""
    os.environ.pop(ENV_FLAG, None)
    g = _fresh_guala()
    try:
        de = {"co_occurrence": {}, "strength": 1.0, "source_path": "survival"}
        assert g._entry_grants_grounding(de) is False
        print("test_entry_grants_grounding_strength_path_off_by_default: PASS")
    finally:
        g.shutdown()


def test_entry_grants_grounding_strength_path_requires_threshold():
    """With the kill switch ON, strength below ELIGIBILITY_STRENGTH_THETA
    must still fail; at/above it must pass. Reuses SURVIVAL_THETA
    directly (no invented second threshold)."""
    from dsf_ai_service.substrate.deep_atlas import (
        ELIGIBILITY_STRENGTH_THETA, SURVIVAL_THETA,
    )
    assert ELIGIBILITY_STRENGTH_THETA == SURVIVAL_THETA, (
        "eligibility threshold must be the SAME constant as Path A's "
        "survival bar, not a new parallel one")
    os.environ[ENV_FLAG] = "1"
    g = _fresh_guala()
    try:
        below = {"co_occurrence": {}, "strength": ELIGIBILITY_STRENGTH_THETA - 0.05}
        at = {"co_occurrence": {}, "strength": ELIGIBILITY_STRENGTH_THETA}
        above = {"co_occurrence": {}, "strength": min(1.0, ELIGIBILITY_STRENGTH_THETA + 0.3)}
        assert g._entry_grants_grounding(below) is False
        assert g._entry_grants_grounding(at) is True
        assert g._entry_grants_grounding(above) is True
        print("test_entry_grants_grounding_strength_path_requires_threshold: PASS")
    finally:
        os.environ.pop(ENV_FLAG, None)
        g.shutdown()


def test_entry_grants_grounding_reorganize_hypothesis_never_reached_via_full_backfill():
    """No-shortcut regression: a reorganize_hypothesis entry must be
    excluded by _backfill_grounded_from_deep_atlas BEFORE
    _entry_grants_grounding is even consulted -- confirmed by checking
    that a reorganize_hypothesis entry with strength/co_occurrence that
    would otherwise pass never contributes a word to the full backfill's
    output, regardless of kill-switch state."""
    os.environ[ENV_FLAG] = "1"
    g = _fresh_guala()
    try:
        chi, mid = _make_mode(g, "hypothetical", "modifier")
        g.deep_atlas.entries[chi].append({
            "section": "modifier", "motif": mid, "chi": chi,
            "strength": 1.0, "co_occurrence": {"sight": {"0": 0.9}},
            "source_path": "reorganize_hypothesis",
        })
        grounded = g._backfill_grounded_from_deep_atlas()
        assert "hypothetical" not in grounded
        print("test_entry_grants_grounding_reorganize_hypothesis_never_reached_via_full_backfill: PASS")
    finally:
        os.environ.pop(ENV_FLAG, None)
        g.shutdown()


# ─────────────────────────────────────────────────────────────────────
# Additive-only regression: words already eligible today must stay eligible
# ─────────────────────────────────────────────────────────────────────

def test_already_grounded_word_unaffected_by_kill_switch_either_way():
    """A word grounded the OLD way (Section.commits' own 'grounded' field,
    e.g. a word first committed during real camera/mic co-occurrence)
    must remain eligible after a full _rebuild_word_to_emission_index()
    call, identically, whether the new kill switch is on or off. This is
    the core additive-only guarantee: nothing about this change can ever
    remove or alter an already-earned eligibility."""
    os.environ["REQUIRE_GROUNDED_SPEECH"] = "1"
    for flag in ("0", "1"):
        os.environ[ENV_FLAG] = flag
        g = _fresh_guala()
        try:
            chi, mid = _make_mode(g, "campfire", "object")
            g.sections["object"].commits.append({
                "tick": 5, "mode": mid, "chi": chi, "word": "campfire",
                "grounded": True,  # real sensory co-occurrence at teach time
            })
            g._rebuild_word_to_emission_index()
            assert "campfire" in g._word_to_emission_sections, flag
            assert g._word_to_emission_sections["campfire"] == [("object", mid, "campfire")], flag
            print(f"test_already_grounded_word_unaffected_by_kill_switch_either_way[{flag}]: PASS")
        finally:
            os.environ.pop(ENV_FLAG, None)
            g.shutdown()
    os.environ.pop("REQUIRE_GROUNDED_SPEECH", None)


def test_has_real_deep_atlas_word_unaffected_by_kill_switch_either_way():
    """Same guarantee, but for a word grounded via the PRE-EXISTING
    deep_atlas co_occurrence backfill path (has_real), not the direct
    Section.commits flag -- the other real path that already grants
    eligibility today. Must be identical with the kill switch on or off."""
    os.environ["REQUIRE_GROUNDED_SPEECH"] = "1"
    for flag in ("0", "1"):
        os.environ[ENV_FLAG] = flag
        g = _fresh_guala()
        try:
            chi, mid = _make_mode(g, "riverbank", "modifier")
            g.deep_atlas.entries[chi].append({
                "section": "modifier", "motif": mid, "chi": chi,
                "strength": 0.01,  # deliberately BELOW the strength threshold
                "co_occurrence": {"sight": {"0": 0.4}},  # real grounding evidence
                "source_path": "episodic",
            })
            g.sections["modifier"].commits.append({
                "tick": 5, "mode": mid, "chi": chi, "word": "riverbank",
                "grounded": False,
            })
            g._rebuild_word_to_emission_index()
            assert "riverbank" in g._word_to_emission_sections, flag
            print(f"test_has_real_deep_atlas_word_unaffected_by_kill_switch_either_way[{flag}]: PASS")
        finally:
            os.environ.pop(ENV_FLAG, None)
            g.shutdown()
    os.environ.pop("REQUIRE_GROUNDED_SPEECH", None)


# ─────────────────────────────────────────────────────────────────────
# Kill switch OFF (default, what actually deploys tonight): true no-op
# ─────────────────────────────────────────────────────────────────────

def test_kill_switch_off_default_is_true_no_op_through_real_dream_cycles():
    """The exact scenario that would make "ocean" eligible WITH the flag
    on must produce IDENTICAL (no-change) behavior with the flag at its
    default (unset). Runs three REAL dream cycles via the full, real
    _run_dream_cycle() (production orchestration, not a stub) -- confirms
    DeepAtlas's own promotion still happens (that part is untouched) but
    eligibility is never granted through the new path while it's off."""
    os.environ.pop(ENV_FLAG, None)
    os.environ["REQUIRE_GROUNDED_SPEECH"] = "1"
    g = _fresh_guala()
    try:
        chi, mid = _make_mode(g, "ocean", "object")
        _teach_via_atlas(g, "ocean", "object", chi, mid, tick=10, salience=1.0)
        assert "ocean" not in g._word_to_emission_sections

        promoted = _run_n_dream_cycles(g, 3)
        # DeepAtlas's OWN promotion must still have happened (that part of
        # the mechanism is untouched by the kill switch) -- via whichever
        # real path (survival or episodic) legitimately fires first.
        assert any(sec == "object" and m == mid for (_p, _c, sec, m) in promoted), promoted
        # -- but the flag being off means _backfill_eligibility_for_
        # promotion's strength path must still refuse to grant eligibility.
        assert "ocean" not in g._word_to_emission_sections, (
            "REGRESSION: kill switch OFF (default) must be a true no-op -- "
            "'ocean' became eligible without DEEP_ATLAS_ELIGIBILITY_BACKFILL_ENABLED=1")
        print("test_kill_switch_off_default_is_true_no_op_through_real_dream_cycles: PASS")
    finally:
        os.environ.pop("REQUIRE_GROUNDED_SPEECH", None)
        g.shutdown()


# ─────────────────────────────────────────────────────────────────────
# The actual "ocean" case: text-only word, real dream cycles, real
# threshold crossing -- end-to-end through the real production functions.
# ─────────────────────────────────────────────────────────────────────

def test_ocean_case_text_only_word_survives_dream_cycles_becomes_eligible():
    """The scenario the whole design doc is about, isolating Path A
    (survival) specifically to match its exact "3 consecutive real dream
    cycles" narrative: a word taught ONLY via text (real
    atlas.record(source='corpus'), never once co-occurring with a real
    camera/mic/touch/smell/taste event), surviving 3 REAL dream-cycle
    promotion checks (real DeepAtlas.dream_promotion_gate, real Path-A
    survival logic -- see _advance_survival_history_and_promote's
    docstring for why Path B/episodic is deliberately kept out of THIS
    test), with the promoted entry's own strength crossing
    ELIGIBILITY_STRENGTH_THETA, MUST become eligible when the kill switch
    is on."""
    os.environ[ENV_FLAG] = "1"
    os.environ["REQUIRE_GROUNDED_SPEECH"] = "1"
    g = _fresh_guala()
    try:
        chi, mid = _make_mode(g, "ocean", "object")
        _teach_via_atlas(g, "ocean", "object", chi, mid, tick=10, salience=1.0)
        assert "ocean" not in g._word_to_emission_sections, (
            "fixture bug: 'ocean' must start ineligible (text-only teach, "
            "no real sensory grounding ever)")

        # Sanity: confirm this word truly never had real grounding co-
        # occurrence recorded anywhere (the has_real path must be closed).
        assert not any(
            c.get("grounded") for c in g.sections["object"].commits
            if c.get("word") == "ocean")

        promoted_c1 = _advance_survival_history_and_promote(g, 200)
        _promote_and_backfill(g, promoted_c1)
        assert "ocean" not in g._word_to_emission_sections, (
            "must not become eligible after only 1 dream cycle "
            f"(promoted={promoted_c1})")

        promoted_c2 = _advance_survival_history_and_promote(g, 400)
        _promote_and_backfill(g, promoted_c2)
        assert "ocean" not in g._word_to_emission_sections, (
            "must not become eligible after only 2 dream cycles "
            f"(promoted={promoted_c2})")

        promoted_c3 = _advance_survival_history_and_promote(g, 600)
        assert any(path == "survival" and sec == "object" and m == mid
                   for (path, _c, sec, m) in promoted_c3), (
            f"fixture bug: DeepAtlas Path-A (survival) promotion did not "
            f"fire on cycle 3: {promoted_c3}")
        _promote_and_backfill(g, promoted_c3)

        de = next(e for e in g.deep_atlas.entries[chi]
                  if e["section"] == "object" and e["motif"] == mid)
        from dsf_ai_service.substrate.deep_atlas import ELIGIBILITY_STRENGTH_THETA
        assert de["strength"] >= ELIGIBILITY_STRENGTH_THETA, (
            f"fixture bug: promoted entry strength {de['strength']} did not "
            f"cross the real threshold {ELIGIBILITY_STRENGTH_THETA}")

        assert "ocean" in g._word_to_emission_sections, (
            "'ocean' survived 3 real dream cycles and crossed the real "
            "strength threshold but was NOT granted eligibility")
        assert g._word_to_emission_sections["ocean"] == [("object", mid, "ocean")]
        assert "ocean" in g._grounded_words

        print("test_ocean_case_text_only_word_survives_dream_cycles_becomes_eligible: PASS "
              f"(strength={de['strength']:.3f})")
    finally:
        os.environ.pop(ENV_FLAG, None)
        os.environ.pop("REQUIRE_GROUNDED_SPEECH", None)
        g.shutdown()


def test_ocean_case_end_to_end_via_real_dream_cycle_loop():
    """Complementary to the Path-A-isolated test above: drives the word
    through the FULL, real, unmodified _run_dream_cycle() (the actual
    production orchestration -- priority-replay sampling/reinforcement,
    real decay, real reorganize, real logging -- called exactly as
    _atick_dreaming calls it), not a hand-assembled survival_history.
    Deliberately does not assert which specific gate (Path A or B)
    fires first, since real replay-driven dwell-earning can legitimately
    accelerate Path B for a strongly-taught entry -- that is correct,
    pre-existing, unmodified DeepAtlas behavior. What this test proves
    end-to-end: a text-only word starts ineligible, a control word with
    literally zero exposure NEVER becomes eligible no matter how many
    real dream cycles run, and the taught word DOES become eligible via
    real production orchestration once DeepAtlas's real strength/
    promotion gates are satisfied."""
    os.environ[ENV_FLAG] = "1"
    os.environ["REQUIRE_GROUNDED_SPEECH"] = "1"
    g = _fresh_guala()
    try:
        chi, mid = _make_mode(g, "ocean", "object")
        _teach_via_atlas(g, "ocean", "object", chi, mid, tick=10, salience=1.0)
        # Zero-exposure control word: gets a mode slot (so it COULD in
        # principle resolve to a word) but no atlas.record()/commit at
        # all -- must never be touched by any of this.
        _make_mode(g, "neverexposed", "object")
        assert "ocean" not in g._word_to_emission_sections
        assert "neverexposed" not in g._word_to_emission_sections

        _run_n_dream_cycles(g, 5)

        assert "ocean" in g._word_to_emission_sections, (
            "text-only 'ocean' never became eligible through 5 real, full "
            "dream cycles with the kill switch on")
        assert "neverexposed" not in g._word_to_emission_sections, (
            "REGRESSION: a word with ZERO real exposure became eligible -- "
            "purely fabricated signal, must be impossible")
        print("test_ocean_case_end_to_end_via_real_dream_cycle_loop: PASS")
    finally:
        os.environ.pop(ENV_FLAG, None)
        os.environ.pop("REQUIRE_GROUNDED_SPEECH", None)
        g.shutdown()


def test_word_that_never_survives_dream_cycles_never_becomes_eligible():
    """No-shortcut regression: a word that gets real exposure (a real
    atlas.record() commit) but never reaches DeepAtlas's OWN Path-A
    promotion bar (its strength drops below SURVIVAL_THETA on what would
    be the 3rd consecutive dream cycle, breaking the streak) must NOT
    become eligible even with the kill switch on -- there is no shortcut
    around dream_promotion_gate's own real consecutive-survival
    requirement. Uses _advance_survival_history_and_promote (see its
    docstring) to isolate Path A so the controlled strength drop actually
    determines the outcome, rather than being masked by Path B's
    real-but-unrelated replay-driven dwell-earning."""
    os.environ[ENV_FLAG] = "1"
    os.environ["REQUIRE_GROUNDED_SPEECH"] = "1"
    g = _fresh_guala()
    try:
        chi, mid = _make_mode(g, "mirage", "modifier")
        _teach_via_atlas(g, "mirage", "modifier", chi, mid, tick=10, salience=1.0)

        _advance_survival_history_and_promote(g, 200)
        _advance_survival_history_and_promote(g, 400)
        # Simulate the binding failing to hold (real decay/interference,
        # not a fabricated shortcut) right before the 3rd dream cycle --
        # directly manipulating atlas entry strength is the same technique
        # dsf_ai_service/substrate/test_deep_atlas_harness.py already uses
        # to model real decay between dream cycles. atlas.record() writes
        # a CHI BAND (band=2 -> 5 neighboring chi buckets), all sharing
        # this section+motif -- every one of them must drop, or the
        # untouched neighbors alone would still satisfy Path A and this
        # fixture would prove nothing.
        for _chi_k, entries in g.atlas.entries.items():
            for e in entries:
                if e["section"] == "modifier" and e["motif"] == mid:
                    e["strength"] = 0.05
        promoted_c3 = _advance_survival_history_and_promote(g, 600)
        _promote_and_backfill(g, promoted_c3)

        assert not any(sec == "modifier" and m == mid for (_p, _c, sec, m) in promoted_c3), (
            f"fixture bug: entry should NOT have been promoted: {promoted_c3}")
        assert "mirage" not in g._word_to_emission_sections, (
            "REGRESSION: a word that never survived DeepAtlas's own real "
            "3-consecutive-dream-cycle promotion bar became eligible anyway")
        print("test_word_that_never_survives_dream_cycles_never_becomes_eligible: PASS")
    finally:
        os.environ.pop(ENV_FLAG, None)
        os.environ.pop("REQUIRE_GROUNDED_SPEECH", None)
        g.shutdown()


# ─────────────────────────────────────────────────────────────────────
# The live trigger is scoped -- never a full index rebuild
# ─────────────────────────────────────────────────────────────────────

def test_live_promotion_trigger_never_calls_full_rebuild():
    """_backfill_eligibility_for_promotion must never call
    _rebuild_word_to_emission_index() -- confirms the live per-word path
    stays O(this word's own commits), not a full corpus rescan, matching
    the dispatch's explicit 'not a full index rebuild' requirement."""
    os.environ[ENV_FLAG] = "1"
    os.environ["REQUIRE_GROUNDED_SPEECH"] = "1"
    g = _fresh_guala()
    try:
        chi, mid = _make_mode(g, "current", "verb")
        _teach_via_atlas(g, "current", "verb", chi, mid, tick=10, salience=1.0)

        calls = {"n": 0}
        orig_rebuild = g._rebuild_word_to_emission_index

        def _spy():
            calls["n"] += 1
            return orig_rebuild()
        g._rebuild_word_to_emission_index = _spy

        _run_n_dream_cycles(g, 3)

        assert "current" in g._word_to_emission_sections
        assert calls["n"] == 0, (
            f"REGRESSION: full _rebuild_word_to_emission_index() was called "
            f"{calls['n']} time(s) by the live per-word promotion trigger")
        print("test_live_promotion_trigger_never_calls_full_rebuild: PASS")
    finally:
        os.environ.pop(ENV_FLAG, None)
        os.environ.pop("REQUIRE_GROUNDED_SPEECH", None)
        g.shutdown()


def test_live_promotion_trigger_does_not_disturb_unrelated_words():
    """Confirms the per-word grant only ever adds the ONE word that
    actually promoted -- an unrelated word with its own real (ungrounded)
    commit history, sharing no chi/section/motif with the promoted entry,
    must stay exactly as ineligible as before."""
    os.environ[ENV_FLAG] = "1"
    os.environ["REQUIRE_GROUNDED_SPEECH"] = "1"
    g = _fresh_guala()
    try:
        chi_o, mid_o = _make_mode(g, "ocean", "object")
        _teach_via_atlas(g, "ocean", "object", chi_o, mid_o, tick=10, salience=1.0)

        chi_u, mid_u = _make_mode(g, "unrelated", "subject")
        _commit_ungrounded(g, "unrelated", "subject", chi_u, mid_u, tick=10)
        # 'unrelated' deliberately gets NO atlas.record()/promotion -- it
        # should be completely untouched by the dream cycles below.

        _run_n_dream_cycles(g, 3)

        assert "ocean" in g._word_to_emission_sections
        assert "unrelated" not in g._word_to_emission_sections
        print("test_live_promotion_trigger_does_not_disturb_unrelated_words: PASS")
    finally:
        os.environ.pop(ENV_FLAG, None)
        os.environ.pop("REQUIRE_GROUNDED_SPEECH", None)
        g.shutdown()


def test_require_grounded_speech_off_makes_backfill_trigger_a_no_op():
    """When the overall credo gate (REQUIRE_GROUNDED_SPEECH) is off, the
    live per-word trigger must do nothing -- there is nothing meaningful
    to backfill since every word is already eligible immediately at first
    commit in that mode (unrelated existing behavior, untouched)."""
    os.environ[ENV_FLAG] = "1"
    os.environ["REQUIRE_GROUNDED_SPEECH"] = "0"
    g = _fresh_guala()
    try:
        chi, mid = _make_mode(g, "current", "verb")
        _teach_via_atlas(g, "current", "verb", chi, mid, tick=10, salience=1.0)
        _run_n_dream_cycles(g, 3)
        # Whatever state _word_to_emission_sections is in, the live
        # trigger itself must be an early-return no-op -- checked directly.
        assert g._backfill_eligibility_for_promotion(chi, "verb", mid) is None
        print("test_require_grounded_speech_off_makes_backfill_trigger_a_no_op: PASS")
    finally:
        os.environ.pop(ENV_FLAG, None)
        os.environ.pop("REQUIRE_GROUNDED_SPEECH", None)
        g.shutdown()


if __name__ == "__main__":
    tests = [
        test_entry_grants_grounding_has_real_path_unaffected_by_kill_switch,
        test_entry_grants_grounding_strength_path_off_by_default,
        test_entry_grants_grounding_strength_path_requires_threshold,
        test_entry_grants_grounding_reorganize_hypothesis_never_reached_via_full_backfill,
        test_already_grounded_word_unaffected_by_kill_switch_either_way,
        test_has_real_deep_atlas_word_unaffected_by_kill_switch_either_way,
        test_kill_switch_off_default_is_true_no_op_through_real_dream_cycles,
        test_ocean_case_text_only_word_survives_dream_cycles_becomes_eligible,
        test_ocean_case_end_to_end_via_real_dream_cycle_loop,
        test_word_that_never_survives_dream_cycles_never_becomes_eligible,
        test_live_promotion_trigger_never_calls_full_rebuild,
        test_live_promotion_trigger_does_not_disturb_unrelated_words,
        test_require_grounded_speech_off_makes_backfill_trigger_a_no_op,
    ]
    failures = []
    for t in tests:
        try:
            t()
        except Exception as e:
            import traceback
            traceback.print_exc()
            failures.append((t.__name__, str(e)))

    print("\n" + "=" * 60)
    if failures:
        print(f"FAILED: {len(failures)}/{len(tests)}")
        for name, err in failures:
            print(f"  - {name}: {err}")
        sys.exit(1)
    else:
        print(f"ALL {len(tests)} TESTS PASSED")
