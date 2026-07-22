"""GL-CMD-TUTOR-JUNK-GATE-20260722: the tutor's source-quality filter.

The tutor drills from _GAP_ARCHIVE — her real reading — which leaks
navigation junk from world feeds and book headers.  is_quality_material is
the deterministic gate that keeps automated teaching from quizzing on
garbage; pick_tutor_item must apply it on BOTH selection paths
(gap-targeted and rotation fallback).  Intake is untouched: the gate only
decides what may be drilled, never what she reads.
"""

from dsf_ai_service.substrate.autonomous_tutor import (
    is_quality_material, pick_tutor_item)


REAL_PROSE = [
    # Ordinary children's prose (the archive's intended material).
    "the cat sat on the warm mat",
    "alice was beginning to get very tired",
    "the rabbit took a watch out of its pocket",
    "she asks the good question with bright eyes",
    # Captions from the staged curriculum seed (Eve, 2026-06-30) — the
    # graded material must never be rejected by its own tutor's gate.
    "the moon is bright and gentle",
    "the moon shines through the window",
    "the happy cat purrs",
    "yellow balloons are round and light",
    "warm soft hug holds you safe",
    "daddy is here and everything is warm",
]

JUNK = [
    # R1 mostly-non-alpha
    "= = = = = footer 2024",
    "*** *** *** page 12 *** ***",
    # R2 URL / domain fragments
    "visit www.gutenberg.org for more books",
    "terms of use at gutenberg.org apply here",
    "see https://example.com for details today",
    "open the file index.html in your browser",
    # R3 ALL-CAPS runs (headers, shouting navigation)
    "CHAPTER XII THE SECRET GARDEN gate",
    "START OF THE PROJECT GUTENBERG EBOOK",
    "the END OF CHAPTER marker line here",
    # R4 repeated boilerplate
    "next next next previous page links",
    "menu menu search login menu here",
    # R5 no verb-like structure / no function words
    "Home About Contact Privacy Terms Careers",
    "Sign Up Log In Register Subscribe Now",
    "click here to subscribe to our newsletter",
]


def test_accepts_real_prose():
    for s in REAL_PROSE:
        assert is_quality_material(s), f"real prose rejected: {s!r}"


def test_rejects_junk():
    for s in JUNK:
        assert not is_quality_material(s), f"junk accepted: {s!r}"


def test_rejects_empty_and_none():
    assert not is_quality_material("")
    assert not is_quality_material(None)
    assert not is_quality_material("   ")


def test_pick_tutor_item_skips_junk_on_rotation_path():
    good = "the cat sat on the warm mat"
    archive = JUNK + [good] + JUNK
    # Every rotation lands on the single quality sentence — junk is never
    # drilled no matter how the rotation counter advances.
    for rotation in range(10):
        item = pick_tutor_item([], archive, rotation=rotation)
        assert item is not None
        assert item["sentence"] == good


def test_pick_tutor_item_skips_junk_on_gap_path():
    # The gap word appears mid-sentence in a junk line AND a real line;
    # only the real line is drillable material.
    junk_with_gap = "Home Subscribe garden Privacy Terms Careers"
    real_with_gap = "she walked into the garden every day"
    item = pick_tutor_item(["garden"], [junk_with_gap, real_with_gap])
    assert item is not None
    assert item["sentence"] == real_with_gap
    assert item["gap_word"] == "garden"


def test_pick_tutor_item_none_when_archive_is_all_junk():
    assert pick_tutor_item(["garden"], list(JUNK)) is None
