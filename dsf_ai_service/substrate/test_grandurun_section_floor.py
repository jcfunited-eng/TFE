"""
GRANDURUN_SECTION_FLOOR_ENABLED verification.

Root cause (verified live + against the ArcLoom spec, see
docs/GL-RPT-SINGLE-WORD-UNAWARE-ROOTCAUSE-C1-20260710-v1.md): emission
happens across 6 independent Section objects (subject/verb/object/
modifier/ground/intro). _grandurun_select_candidates
(gualaloom_v5_engine.py) pools candidates from all 6 sections, sorts by
one global coherent_magnitude score, then does a single global top_k
cut. Because her learned vocabulary/atlas naturally scores some
grammatical roles higher than others, a flat global cut leaves some
sections with ZERO candidates most turns -> evidence_pressure==0 ->
Section.commit_check's hard evidence floor (assemblage.py:
"if evidence_pressure < 0.15: return False, None") permanently blocks
those sections from ever committing, regardless of keyhole excitation.

Fix: an opt-in (env-gated, default OFF) per-section reserved floor +
global overflow allocation in _grandurun_select_candidates.

Tests here run directly against the real function and the real
gualaloom_v5_engine.Section class (no mocks), with no whole-Guala
engine required -- _grandurun_select_candidates only needs
(input_chis, deep_candidates, sections, input_words_set, top_k).

  1. test_off_matches_legacy_behavior: switch OFF (default/unset) is a
     pure regression guard -- must reproduce the exact pre-change
     global top-K cut (same length, same global sort, deterministic),
     AND must reproduce the known starvation pattern this fix targets.
  2. test_on_gives_every_section_a_floor: switch ON gives every section
     with real candidates at least min(min_per_section, available)
     slots, while the rest of top_k still fills by global score.
  3. test_on_never_fabricates_or_duplicates: every candidate returned
     with the switch ON traces back to a real (section, motif, word)
     triple present in the input deep_candidates -- no synthetic or
     duplicated evidence.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dsf_ai_service.v4.gualaloom_v5_engine import (
    _grandurun_select_candidates,
    Section,
)

EMISSION_SECTIONS = ("subject", "verb", "object", "modifier", "ground", "intro")


def build_sections():
    """Real Section objects (gualaloom_v5_engine.Section, not
    assemblage.Section), each with enough .modes entries to cover every
    mid index the test's deep_candidates reference."""
    sections = {}
    for name in EMISSION_SECTIONS:
        sec = Section(name, role_class=name if name in
                      ("subject", "verb", "object", "modifier") else None)
        for i in range(50):
            sec.modes.append((None, 0, f"{name}_w{i}"))
        sections[name] = sec
    return sections


def build_imbalanced_deep_candidates():
    """Mimics the live-measured imbalance: subject/verb/intro have deep
    co-occurrence data for many candidate words this turn; modifier/
    ground/object have very little -- the exact shape of the root cause
    (modifier/ground at 8-36% "capacity" vs 127-148% for subject/verb/
    intro under a pure global top-K cut).

    Single deep_candidate entry, single input anchor at the same chi as
    the entry -- this makes coherent_magnitude collapse to exactly
    `strength` (phi = pi*|chi_a-chi_b|/CHI_CORR_LENGTH = 0 when
    chi_a==chi_b), so the intended per-section ranking is easy to
    reason about directly without re-deriving the phase-coherence math.
    """
    de = {
        "chi": 10, "source": "corpus", "arousal": 0.5, "valence": 0.0,
        "surprise": 0.0, "polarity": 1.0, "sensory_refs": [],
    }
    co = {
        "subject":  {str(i): 0.90 - i * 0.01 for i in range(40)},
        "verb":     {str(i): 0.85 - i * 0.01 for i in range(40)},
        "intro":    {str(i): 0.80 - i * 0.01 for i in range(40)},
        "modifier": {str(i): 0.30 - i * 0.02 for i in range(3)},
        "ground":   {str(i): 0.25 - i * 0.02 for i in range(2)},
        "object":   {str(i): 0.20 - i * 0.02 for i in range(4)},
    }
    clarity = 1.0
    return [(de, co, clarity)]


AVAILABLE_PER_SECTION = {
    "subject": 40, "verb": 40, "intro": 40,
    "modifier": 3, "ground": 2, "object": 4,
}


def counts_by_section(candidates):
    counts = {name: 0 for name in EMISSION_SECTIONS}
    for c in candidates:
        counts[c["section"]] = counts.get(c["section"], 0) + 1
    return counts


def test_off_matches_legacy_behavior():
    """Regression guard: switch unset/OFF must be the exact pre-change
    global top-K cut."""
    os.environ.pop("GRANDURUN_SECTION_FLOOR_ENABLED", None)
    sections = build_sections()
    deep_candidates = build_imbalanced_deep_candidates()
    input_chis = [10]
    top_k = 30

    result_off = _grandurun_select_candidates(
        input_chis, deep_candidates, sections, set(), top_k=top_k)

    mags = [c["coherent_magnitude"] for c in result_off]
    assert mags == sorted(mags, reverse=True), (
        "OFF path must stay globally sorted by coherent_magnitude")
    assert len(result_off) == top_k, (
        f"expected exactly top_k={top_k} candidates, got {len(result_off)}")

    counts = counts_by_section(result_off)
    print(f"  OFF counts by section: {counts}")
    # This IS the bug being fixed: with imbalanced scoring, a pure global
    # cut lets the highest-scoring sections dominate entirely (subject
    # 15 + verb 10 + intro 5 = top_k=30, deterministic from the fixture's
    # arithmetic score sequences) and starves object/modifier/ground to
    # zero candidates -- exactly the live-measured pattern (some
    # sections at 0% "capacity" this turn -> evidence_pressure==0 ->
    # hard-blocked from committing).
    assert counts == {"subject": 15, "verb": 10, "object": 0,
                       "modifier": 0, "ground": 0, "intro": 5}, (
        f"expected the legacy global cut's deterministic starvation "
        f"pattern, got {counts}")

    # Determinism: switch OFF must be repeatable / side-effect-free.
    result_off_2 = _grandurun_select_candidates(
        input_chis, deep_candidates, sections, set(), top_k=top_k)
    assert result_off == result_off_2, "OFF path must be deterministic/repeatable"
    print("  PASS: switch OFF matches legacy global top-K behavior (byte-identical, deterministic)")


def test_on_gives_every_section_a_floor():
    os.environ["GRANDURUN_SECTION_FLOOR_ENABLED"] = "1"
    try:
        sections = build_sections()
        deep_candidates = build_imbalanced_deep_candidates()
        input_chis = [10]
        top_k = 30

        result_on = _grandurun_select_candidates(
            input_chis, deep_candidates, sections, set(), top_k=top_k)

        min_per_section = max(3, top_k // (len(EMISSION_SECTIONS) * 4))
        counts = counts_by_section(result_on)
        print(f"  ON counts by section (min_per_section={min_per_section}): {counts}")

        for name in EMISSION_SECTIONS:
            expected_floor = min(min_per_section, AVAILABLE_PER_SECTION[name])
            assert counts[name] >= expected_floor, (
                f"section {name} got {counts[name]} candidates, "
                f"expected at least floor {expected_floor}"
            )

        assert len(result_on) <= top_k, (
            f"returned {len(result_on)} candidates, exceeds top_k={top_k}")

        mags = [c["coherent_magnitude"] for c in result_on]
        assert mags == sorted(mags, reverse=True), (
            "ON path must still return a list sorted by -coherent_magnitude "
            "(downstream callers, e.g. _emit_dynamics's backtrack/tie logic, "
            "read candidates[0]/[1] assuming this order)")

        print("  PASS: switch ON gives every section its reserved floor, "
              "overflow fills the rest by score, order preserved")
    finally:
        os.environ.pop("GRANDURUN_SECTION_FLOOR_ENABLED", None)


def test_on_never_fabricates_or_duplicates():
    os.environ["GRANDURUN_SECTION_FLOOR_ENABLED"] = "1"
    try:
        sections = build_sections()
        deep_candidates = build_imbalanced_deep_candidates()
        input_chis = [10]
        top_k = 30

        # Reference universe of legitimate (section, motif, word) triples,
        # built the same way Pass 1 of the real function derives them.
        legit = set()
        for de, co, clarity in deep_candidates:
            for sec_name, sec_co in co.items():
                sec = sections.get(sec_name)
                for mid_str in sec_co:
                    mid = int(mid_str)
                    if sec is None or mid >= len(sec.modes):
                        continue
                    _, _, word = sec.modes[mid]
                    legit.add((sec_name, mid, word))

        result_on = _grandurun_select_candidates(
            input_chis, deep_candidates, sections, set(), top_k=top_k)

        seen_keys = set()
        for c in result_on:
            key = (c["section"], c["motif"], c["word"])
            assert key in legit, f"fabricated candidate not present in input: {key}"
            assert key not in seen_keys, f"duplicate candidate returned: {key}"
            seen_keys.add(key)

        print(f"  PASS: all {len(result_on)} ON-path candidates trace to real "
              "input, no duplicates")
    finally:
        os.environ.pop("GRANDURUN_SECTION_FLOOR_ENABLED", None)


def test_on_small_topk_never_exceeds_topk():
    """Edge case: a pathologically small top_k where the floor
    reservation alone (min_per_section=3 floor * 6 sections = 18) would
    exceed top_k. Never happens at the real GRANDURUN_TOPK=200 default,
    but the function must still honor its 'at most top_k' contract."""
    os.environ["GRANDURUN_SECTION_FLOOR_ENABLED"] = "1"
    try:
        sections = build_sections()
        deep_candidates = build_imbalanced_deep_candidates()
        input_chis = [10]
        top_k = 10

        result_on = _grandurun_select_candidates(
            input_chis, deep_candidates, sections, set(), top_k=top_k)
        assert len(result_on) <= top_k, (
            f"returned {len(result_on)} candidates, exceeds top_k={top_k}")
        print(f"  PASS: small top_k={top_k} still respects 'at most top_k' "
              f"(got {len(result_on)})")
    finally:
        os.environ.pop("GRANDURUN_SECTION_FLOOR_ENABLED", None)


def main():
    print("test_off_matches_legacy_behavior")
    test_off_matches_legacy_behavior()
    print("test_on_gives_every_section_a_floor")
    test_on_gives_every_section_a_floor()
    print("test_on_never_fabricates_or_duplicates")
    test_on_never_fabricates_or_duplicates()
    print("test_on_small_topk_never_exceeds_topk")
    test_on_small_topk_never_exceeds_topk()
    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    main()
