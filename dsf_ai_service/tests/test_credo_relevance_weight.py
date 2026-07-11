"""
GL-CMD-CREDO-RELEVANCE-WEIGHT-C1-20260711: unit + integration tests for the
relevance-weighted credo gate in _brain_emission_candidates_legacy's
deep_atlas gather.

Context (see docs/GL-RPT-READ-MS-ROOTCAUSE-C1-20260711-v1.md's "why the
content is disconnected" section): the credo/grounded-speech gate
(REQUIRE_GROUNDED_SPEECH, enforced via membership in
self._word_to_emission_sections) used to be a flat pass/fail with no
notion of how relevant an eligible candidate was to the CURRENT turn --
so a candidate word that genuinely co-occurs with several of the turn's
own input words got no more credit than one that only a single, possibly
generic, seed word happened to surface. The fix ranks/weights eligible
candidates by real cross-query convergence (how many DISTINCT input
words' own _deep_atlas_neighbor_candidates walk actually surface the
same candidate), reusing that function's existing real co-occurrence
data unchanged -- it does not add a new relevance mechanism, and it
never changes which words are ELIGIBLE (the real-grounding gate itself
is untouched).

Mirrors dsf_ai_service/tests/test_emission_shadow.py's own style: fast,
deterministic stub-based tests that exercise the real aggregation/boost
code in _brain_emission_candidates_legacy, plus integration-level tests
against a real Guala() boot with real atlas.record()/deep_atlas.promote()
co-occurrence data (not hand-faked weights) -- matching
dsf_ai_service/substrate/test_cognition_bundle.py's _build_engine()
convention for constructing realistic fixtures.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ.setdefault("SUBSTRATE_MODE", "embedded")


def _fresh_guala():
    """Same convention as test_emission_shadow.py's helper. Stubs
    organism.recall_fast to a harmless non-empty vote for an unrelated
    nonsense word -- source #1 (organism-vote) is a documented dead end
    for known words (self-echo) and returns nothing for never-taught
    words either way (see _brain_emission_candidates_legacy's own
    2026-07-08 comment); without this stub, merged_votes would be
    entirely empty and the function would short-circuit with `return []`
    before ever reaching the deep_atlas gather these tests exercise.
    That early-return behavior is real, already-documented, and
    deliberately NOT what this test file is about."""
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala
    g = Guala()
    g.organism.recall_fast = lambda signal: {"__unrelated_dummy__": 1}
    return g


def _ground_word(g, word, section):
    """Give `word` a real mode + a real committed section home so it
    passes the credo gate, both as a query seed and as a candidate --
    same direct-index-seeding convention test_emission_shadow.py's own
    test_membrane_top_words_grounded_filter uses."""
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
    g._word_to_emission_sections.setdefault(word.lower(), []).append((section, mid, word))
    return chi, mid


# ─────────────────────────────────────────────────────────────────────
# Stub-based tests: exercise the real aggregation/boost math directly,
# fast and deterministic (mirrors test_emission_shadow.py's dispatcher
# tests). _deep_atlas_neighbor_candidates itself is stubbed so these
# tests are about the NEW gathering/ranking logic around it, not about
# that (unchanged) function's own internals.
# ─────────────────────────────────────────────────────────────────────

def test_single_seed_candidate_weight_unchanged():
    """The common case (only one seed word surfaces a candidate) must be
    numerically IDENTICAL to pre-fix behavior -- boost factor 1.0."""
    g = _fresh_guala()
    try:
        table = {"ocean": [("word1", 0.5, "modifier", 10)]}
        g._deep_atlas_neighbor_candidates = (
            lambda seed_word, exclude_words=None: table.get(seed_word, []))
        cands = g._brain_emission_candidates_legacy(["ocean"])
        assert len(cands) == 1, cands
        de, co, weight = cands[0]
        assert abs(weight - 0.5) < 1e-9, weight
        assert co == {"modifier": {"10": 0.5}}, co
        print("test_single_seed_candidate_weight_unchanged: PASS")
    finally:
        g.shutdown()


def test_multi_seed_convergence_boosts_weight():
    """A candidate surfaced by TWO distinct seed words gets boosted by
    (1 + BOOST_PER_SEED * (n_distinct_queries - 1)), using the stronger
    of the two raw proposals as its base."""
    from dsf_ai_service.v4.gualaloom_v5_engine import DEEP_ATLAS_RELEVANCE_BOOST_PER_SEED
    g = _fresh_guala()
    try:
        table = {
            "ocean": [("blue", 0.4, "modifier", 20)],
            "wave": [("blue", 0.6, "modifier", 20)],
        }
        g._deep_atlas_neighbor_candidates = (
            lambda seed_word, exclude_words=None: table.get(seed_word, []))
        cands = g._brain_emission_candidates_legacy(["ocean", "wave"])
        assert len(cands) == 1, cands
        de, co, weight = cands[0]
        expected = 0.6 * (1.0 + DEEP_ATLAS_RELEVANCE_BOOST_PER_SEED * 1)
        assert abs(weight - expected) < 1e-9, (weight, expected)
        print("test_multi_seed_convergence_boosts_weight: PASS")
    finally:
        g.shutdown()


def test_boost_capped_at_max():
    """Many distinct converging seeds must not let convergence COUNT
    alone dominate the real co-occurrence weight -- capped at
    DEEP_ATLAS_RELEVANCE_BOOST_MAX."""
    from dsf_ai_service.v4.gualaloom_v5_engine import DEEP_ATLAS_RELEVANCE_BOOST_MAX
    g = _fresh_guala()
    try:
        queries = [f"q{i}" for i in range(10)]
        table = {q: [("conv", 0.2, "modifier", 30)] for q in queries}
        g._deep_atlas_neighbor_candidates = (
            lambda seed_word, exclude_words=None: table.get(seed_word, []))
        cands = g._brain_emission_candidates_legacy(queries)
        assert len(cands) == 1, cands
        de, co, weight = cands[0]
        expected = 0.2 * DEEP_ATLAS_RELEVANCE_BOOST_MAX
        assert abs(weight - expected) < 1e-9, (weight, expected)
        print("test_boost_capped_at_max: PASS")
    finally:
        g.shutdown()


def test_repeated_same_query_word_not_double_counted():
    """The SAME input word repeated in a sentence ('the the ocean') must
    not itself inflate the convergence count -- only DISTINCT query
    words count."""
    g = _fresh_guala()
    try:
        table = {"ocean": [("blue", 0.4, "modifier", 20)]}
        g._deep_atlas_neighbor_candidates = (
            lambda seed_word, exclude_words=None: table.get(seed_word, []))
        cands = g._brain_emission_candidates_legacy(["ocean", "ocean"])
        assert len(cands) == 1, cands
        de, co, weight = cands[0]
        assert abs(weight - 0.4) < 1e-9, weight  # boost factor 1.0, not 1.5
        print("test_repeated_same_query_word_not_double_counted: PASS")
    finally:
        g.shutdown()


def test_candidate_word_never_duplicated_across_queries():
    """Regardless of how many seeds converge on it, a candidate word
    must appear exactly ONCE in the returned candidate list (matches
    the pre-fix invariant -- this fix changes weight/order, never the
    shape of what gets returned)."""
    g = _fresh_guala()
    try:
        table = {
            "ocean": [("blue", 0.4, "modifier", 20), ("green", 0.3, "modifier", 21)],
            "wave": [("blue", 0.5, "modifier", 20)],
            "tide": [("blue", 0.2, "modifier", 20)],
        }
        g._deep_atlas_neighbor_candidates = (
            lambda seed_word, exclude_words=None: table.get(seed_word, []))
        cands = g._brain_emission_candidates_legacy(["ocean", "wave", "tide"])
        words = []
        for de, co, weight in cands:
            for sec_co in co.values():
                words.extend(sec_co.keys())
        assert words.count("20") == 1, words  # "blue"'s mode_idx, exactly once
        assert words.count("21") == 1, words  # "green"'s mode_idx, exactly once
        print("test_candidate_word_never_duplicated_across_queries: PASS")
    finally:
        g.shutdown()


# ─────────────────────────────────────────────────────────────────────
# Integration-level tests: real Guala() boot, real atlas.record() /
# deep_atlas.promote() co-occurrence data (production code, not a
# hand-faked weight) -- matches test_cognition_bundle.py's _build_engine
# convention.
# ─────────────────────────────────────────────────────────────────────

def test_topically_relevant_candidate_outranks_generic_one_real_data():
    """The scenario GL-RPT-READ-MS-ROOTCAUSE-C1-20260711-v1 names
    directly: a candidate ('deep') that genuinely co-occurs with TWO of
    the turn's own input words ('ocean', 'current') must now outrank a
    candidate ('nice') that only resonates with a single, unrelated seed
    ('sun') -- even though their RAW, single-source co-occurrence
    weights (computed by the real, unmodified deep_atlas._update_
    invariant) are equal. Pre-fix, these would have been added to the
    candidate list at IDENTICAL weight -- whichever won downstream
    sorting was an accident of iteration order, never a computed
    relevance judgment. Real data: entries built via g.atlas.record() +
    g.deep_atlas.promote(working_atlas=g.atlas), the exact same
    production calls test_cognition_bundle.py's _build_engine() uses,
    not hand-written co_occurrence dicts."""
    os.environ["REQUIRE_GROUNDED_SPEECH"] = "1"
    g = _fresh_guala()
    try:
        chi_ocean, mid_ocean = _ground_word(g, "ocean", "object")
        chi_current, mid_current = _ground_word(g, "current", "subject")
        chi_sun, mid_sun = _ground_word(g, "sun", "intro")
        _chi_deep, mid_deep = _ground_word(g, "deep", "modifier")
        _chi_nice, mid_nice = _ground_word(g, "nice", "modifier")
        assert len({chi_ocean, chi_current, chi_sun}) == 3, \
            "test fixture bug: seed chis collided"

        # Real working-atlas neighbor evidence for "deep" near BOTH ocean
        # and current -- becomes real co_occurrence on each seed's own
        # promoted deep-atlas entry via _update_invariant.
        g.atlas.record("modifier", mid_deep, chi_ocean + 1, tick=10,
                       salience=1.8, dwell_ticks=5, source="corpus")
        g.atlas.record("modifier", mid_deep, chi_current + 1, tick=10,
                       salience=1.8, dwell_ticks=5, source="corpus")
        # "nice": single-source real neighbor evidence near sun only.
        g.atlas.record("modifier", mid_nice, chi_sun + 0, tick=10,
                       salience=1.8, dwell_ticks=5, source="corpus")

        # The seeds' own working-atlas entries (promoted below).
        g.atlas.record("object", mid_ocean, chi_ocean, tick=10,
                       salience=1.8, dwell_ticks=5, source="corpus")
        g.atlas.record("subject", mid_current, chi_current, tick=10,
                       salience=1.8, dwell_ticks=5, source="corpus")
        g.atlas.record("intro", mid_sun, chi_sun, tick=10,
                       salience=1.8, dwell_ticks=5, source="corpus")

        g.tick = 100
        for _chi_k, entries in list(g.atlas.entries.items()):
            for e in entries:
                if (e["section"] in ("object", "subject", "intro")
                        and e["motif"] in (mid_ocean, mid_current, mid_sun)):
                    g.deep_atlas.promote(e, "episodic", g.tick, working_atlas=g.atlas)

        # Sanity: confirm the raw (pre-boost) weights really are equal --
        # otherwise this wouldn't isolate the effect of convergence alone.
        raw_ocean = g._deep_atlas_neighbor_candidates("ocean")
        raw_sun = g._deep_atlas_neighbor_candidates("sun")
        deep_raw = next(w for (wl, w, s, m) in raw_ocean if wl == "deep")
        nice_raw = next(w for (wl, w, s, m) in raw_sun if wl == "nice")
        assert abs(deep_raw - nice_raw) < 1e-9, \
            f"fixture bug: raw weights not equal ({deep_raw} vs {nice_raw})"

        candidates = g._brain_emission_candidates_legacy(["ocean", "current", "sun"])
        weight_by_mid = {}
        for de, co, weight in candidates:
            for sec_co in co.values():
                for mid_str, w in sec_co.items():
                    weight_by_mid[int(mid_str)] = w

        assert mid_deep in weight_by_mid, "deep must still be an eligible candidate"
        assert mid_nice in weight_by_mid, "nice must still be an eligible candidate"
        assert weight_by_mid[mid_deep] > weight_by_mid[mid_nice], (
            f"topically-relevant candidate did not outrank the generic one: "
            f"deep={weight_by_mid[mid_deep]} nice={weight_by_mid[mid_nice]}")
        # Precise check, not just "bigger": deep should be boosted by
        # exactly the 2-distinct-seed factor over its equal-to-nice raw weight.
        assert abs(weight_by_mid[mid_deep] - deep_raw * 1.5) < 1e-9
        assert abs(weight_by_mid[mid_nice] - nice_raw) < 1e-9  # nice: unboosted
        print(f"test_topically_relevant_candidate_outranks_generic_one_real_data: "
              f"PASS (deep={weight_by_mid[mid_deep]:.4f} > nice={weight_by_mid[mid_nice]:.4f}, "
              f"both raw={deep_raw:.4f})")
    finally:
        os.environ.pop("REQUIRE_GROUNDED_SPEECH", None)
        g.shutdown()


def test_ungrounded_word_still_excluded_despite_strong_convergence():
    """No-regression check: a word that has real, strongly-convergent
    deep_atlas co-occurrence with the turn's input (the exact shape that
    would otherwise earn the maximum relevance boost) must still be
    completely excluded if it was never actually grounded -- proves the
    relevance weighting operates strictly WITHIN the existing eligible
    set and cannot smuggle a new word past the credo gate."""
    os.environ["REQUIRE_GROUNDED_SPEECH"] = "1"
    g = _fresh_guala()
    try:
        chi_ocean, mid_ocean = _ground_word(g, "ocean", "object")
        chi_current, mid_current = _ground_word(g, "current", "subject")

        # "ungrounded" gets a real mode slot (so a walk COULD resolve it
        # to a word) but is deliberately never added to
        # _word_to_emission_sections -- never actually spoken/grounded.
        from dsf_ai_service.v4.gualaloom_v5_engine import deterministic_motif_id
        mid_ungrounded = deterministic_motif_id("ungrounded")
        sec = g.sections["modifier"]
        while len(sec.modes) <= mid_ungrounded:
            sec.modes.append((0, 0, ""))
        sec.modes[mid_ungrounded] = (0, 0, "ungrounded")
        assert "ungrounded" not in g._word_to_emission_sections

        # Real convergent co-occurrence from BOTH seeds -- the strongest
        # possible boost case, deliberately.
        g.atlas.record("modifier", mid_ungrounded, chi_ocean + 1, tick=10,
                       salience=1.8, dwell_ticks=5, source="corpus")
        g.atlas.record("modifier", mid_ungrounded, chi_current + 1, tick=10,
                       salience=1.8, dwell_ticks=5, source="corpus")
        g.atlas.record("object", mid_ocean, chi_ocean, tick=10,
                       salience=1.8, dwell_ticks=5, source="corpus")
        g.atlas.record("subject", mid_current, chi_current, tick=10,
                       salience=1.8, dwell_ticks=5, source="corpus")

        g.tick = 100
        for _chi_k, entries in list(g.atlas.entries.items()):
            for e in entries:
                if (e["section"] in ("object", "subject")
                        and e["motif"] in (mid_ocean, mid_current)):
                    g.deep_atlas.promote(e, "episodic", g.tick, working_atlas=g.atlas)

        candidates = g._brain_emission_candidates_legacy(["ocean", "current"])
        seen_mids = set()
        for de, co, weight in candidates:
            for sec_co in co.values():
                seen_mids.update(int(m) for m in sec_co.keys())
        assert mid_ungrounded not in seen_mids, \
            "ungrounded word leaked through the credo gate via the relevance boost"
        print("test_ungrounded_word_still_excluded_despite_strong_convergence: PASS")
    finally:
        os.environ.pop("REQUIRE_GROUNDED_SPEECH", None)
        g.shutdown()


def test_require_grounded_speech_off_unaffected_by_boost_logic():
    """REQUIRE_GROUNDED_SPEECH=0 (kill switch) path is untouched by this
    fix -- _deep_atlas_neighbor_candidates' own gate check is skipped
    exactly as before, the new aggregation pass just ranks whatever that
    function returns."""
    os.environ["REQUIRE_GROUNDED_SPEECH"] = "0"
    g = _fresh_guala()
    try:
        table = {"ocean": [("blue", 0.4, "modifier", 20)]}
        g._deep_atlas_neighbor_candidates = (
            lambda seed_word, exclude_words=None: table.get(seed_word, []))
        cands = g._brain_emission_candidates_legacy(["ocean"])
        assert len(cands) == 1, cands
        assert abs(cands[0][2] - 0.4) < 1e-9
        print("test_require_grounded_speech_off_unaffected_by_boost_logic: PASS")
    finally:
        os.environ.pop("REQUIRE_GROUNDED_SPEECH", None)
        g.shutdown()


if __name__ == "__main__":
    test_single_seed_candidate_weight_unchanged()
    test_multi_seed_convergence_boosts_weight()
    test_boost_capped_at_max()
    test_repeated_same_query_word_not_double_counted()
    test_candidate_word_never_duplicated_across_queries()
    test_topically_relevant_candidate_outranks_generic_one_real_data()
    test_ungrounded_word_still_excluded_despite_strong_convergence()
    test_require_grounded_speech_off_unaffected_by_boost_logic()
    print("ALL PASS: test_credo_relevance_weight")
