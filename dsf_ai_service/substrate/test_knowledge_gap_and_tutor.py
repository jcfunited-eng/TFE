"""Tests for GL-CMD-AUTOMATED-TEACHING-20260717: gap ledger + tutor logic.

Pure-logic coverage (no engine boot): the ledger's record/top/persist/cap
behavior, the record helpers' filtering, and the tutor's item selection,
stem/expected split, and reality-graded verdict.  Plus one fake-engine
exchange proving the tutor glue calls the real teacher gateway with the
exact arguments the manual (Joe) flow uses.
"""

import importlib
import json
import os
import time

import pytest

from dsf_ai_service.substrate import knowledge_gap_ledger as kgl
from dsf_ai_service.substrate.autonomous_tutor import (
    judge_attempt, pick_tutor_item, split_stem)


@pytest.fixture
def ledger(tmp_path):
    return kgl.GapLedger(str(tmp_path))


# ── GapLedger ──────────────────────────────────────────────────────

def test_record_top_and_addressed_cooldown(ledger):
    for _ in range(3):
        ledger.record("river", "compose_refusal")
    ledger.record("stone", "recognition_miss")
    assert ledger.top_gaps(5) == ["river", "stone"]
    ledger.mark_addressed("river")
    # Addressed within cooldown -> not re-served; stone remains.
    assert ledger.top_gaps(5) == ["stone"]


def test_persistence_round_trip(tmp_path):
    a = kgl.GapLedger(str(tmp_path))
    a.record("meadow", "compose_refusal")
    a.record_tutor_teach()  # forces a persist
    b = kgl.GapLedger(str(tmp_path))
    assert "meadow" in b.top_gaps(5)
    assert b.tutor_teaches_today() == 1


def test_entry_cap_keeps_highest_counts(tmp_path):
    led = kgl.GapLedger(str(tmp_path))

    def alphabetic_suffix(value):
        suffix = ""
        while True:
            suffix = chr(ord("a") + value % 26) + suffix
            value //= 26
            if not value:
                return suffix

    for i in range(kgl.ENTRY_CAP + 50):
        led.record(f"gap{alphabetic_suffix(i)}", "recognition_miss")
    led.record("heavy", "recognition_miss")
    for _ in range(5):
        led.record("heavy", "recognition_miss")

    assert len(led._entries) == kgl.ENTRY_CAP
    assert "heavy" in led._entries

    with led._lock:
        led._dirty = True
        led._persist_locked(force=True)
    reloaded = kgl.GapLedger(str(tmp_path))
    assert len(reloaded._entries) <= kgl.ENTRY_CAP
    assert "heavy" in reloaded._entries


def test_tutor_day_counter_rolls_and_bounds(ledger):
    for _ in range(3):
        ledger.record_tutor_teach()
    assert ledger.tutor_teaches_today() == 3
    # A different day starts at zero.
    ledger._tutor_days = {"1999-01-01": 40}
    assert ledger.tutor_teaches_today() == 0


def test_corrupt_ledger_file_survives(tmp_path):
    path = os.path.join(str(tmp_path), kgl.LEDGER_FILE)
    with open(path, "w") as f:
        f.write("{torn json")
    led = kgl.GapLedger(str(tmp_path))
    led.record("safe", "recognition_miss")
    assert led.top_gaps(3) == ["safe"]


# ── record helpers (the engine hooks call exactly these) ───────────

def test_record_compose_refusal_input_unknown_records_content_words(
        tmp_path, monkeypatch):
    monkeypatch.setattr(kgl, "_ledger", kgl.GapLedger(str(tmp_path)))
    kgl.record_compose_refusal("input_unknown",
                               ["the", "zorply", "sings"])
    top = kgl.get_ledger().top_gaps(5)
    assert "zorply" in top and "sings" in top and "the" not in top


def test_record_compose_refusal_successor_records_boundary_word(
        tmp_path, monkeypatch):
    monkeypatch.setattr(kgl, "_ledger", kgl.GapLedger(str(tmp_path)))
    kgl.record_compose_refusal("no_successor", ["i", "am", "guala"])
    assert kgl.get_ledger().top_gaps(5) == ["guala"]
    kgl.record_compose_refusal("empty_query", [])  # records nothing, no raise


def test_record_recognition_miss_thresholds_and_stopwords(
        tmp_path, monkeypatch):
    monkeypatch.setattr(kgl, "_ledger", kgl.GapLedger(str(tmp_path)))
    kgl.record_recognition_miss("kremvat", 0.95)   # fresh, high -> recorded
    kgl.record_recognition_miss("familiar", 0.2)   # low surprise -> ignored
    kgl.record_recognition_miss("the", 0.99)       # stopword -> ignored
    assert kgl.get_ledger().top_gaps(5) == ["kremvat"]


# ── tutor pure logic ───────────────────────────────────────────────

def test_split_stem_gap_targeted():
    words = "the little boat sails on water".split()
    stem, expected = split_stem(words, gap_word="sails")
    assert stem == ["the", "little", "boat"]
    assert expected == ["sails", "on", "water"]


def test_split_stem_fallback_and_bounds():
    assert split_stem("too short one".split()) is None
    stem, expected = split_stem("the dog sleeps by the warm fire".split())
    assert stem + expected == "the dog sleeps by the warm fire".split()
    assert 1 <= len(expected) and len(stem) >= 2


def test_pick_tutor_item_prefers_gap_word():
    archive = ["the sun is warm today",
               "a little fish swims in the river"]
    item = pick_tutor_item(["swims"], archive)
    assert item["gap_word"] == "swims"
    assert item["expected"].split()[0] == "swims"
    assert item["stem"] == "a little fish"


def test_pick_tutor_item_rotates_fallback():
    archive = ["the sun is warm today", "the moon is bright tonight"]
    first = pick_tutor_item([], archive, rotation=0)
    second = pick_tutor_item([], archive, rotation=1)
    assert first["sentence"] != second["sentence"]
    assert pick_tutor_item([], []) is None


def test_judge_attempt_reality_graded():
    assert judge_attempt("sails on the water", "sails on water")
    assert judge_attempt("i think sails maybe", "sails on water")
    assert not judge_attempt("boat boat boat", "sails on water")
    assert not judge_attempt("", "sails on water")        # silence: teachable
    assert not judge_attempt("anything", "")


# ── glue: the tutor exchange calls the real gateway correctly ──────

class _FakeGuala:
    """Records gateway calls; answers wrongly so a teach must follow."""

    def __init__(self):
        self.corrections = []
        self._live_converse_pending = 0

    def apply_teacher_correction(self, **kw):
        self.corrections.append(kw)


def test_tutor_exchange_wires_gateway_like_manual_flow(tmp_path, monkeypatch):
    """The automated exchange must be indistinguishable in mechanism from
    Joe's manual flow: ask via converse, correct via apply_teacher_correction
    with source='curriculum' and the true continuation as expected."""
    monkeypatch.setenv("STATE_DIR", str(tmp_path))
    monkeypatch.setattr(kgl, "_ledger", None)
    importlib.reload(kgl)

    ledger = kgl.get_ledger(str(tmp_path))
    fake = _FakeGuala()
    archive = ["a little fish swims in the river"]
    item = pick_tutor_item(["swims"], archive)
    attempt = "the warm sun"  # her (wrong) real answer stand-in
    correct = judge_attempt(attempt, item["expected"])
    assert not correct
    fake.apply_teacher_correction(
        original_input=item["stem"], her_emission=attempt,
        correct=correct,
        expected_response=None if correct else item["expected"],
        source="curriculum")
    ledger.record_tutor_teach()
    ledger.mark_addressed(item["gap_word"])

    kw = fake.corrections[0]
    assert kw["source"] == "curriculum"
    assert kw["correct"] is False
    assert kw["expected_response"].split()[0] == "swims"
    assert kw["original_input"] == "a little fish"
    assert ledger.tutor_teaches_today() == 1
    assert "swims" not in ledger.top_gaps(5)


def test_judge_attempt_detail_classifies_syntax_failures():
    """GL-CMD-SYNTAX-TUTOR-20260718: right-words-wrong-order is a SYNTAX
    verdict, distinct from plain wrong."""
    from dsf_ai_service.substrate.autonomous_tutor import judge_attempt_detail

    assert judge_attempt_detail("sails on water",
                                "sails on water")["verdict"] == "correct"
    assert judge_attempt_detail("water on sails",
                                "sails on water")["verdict"] == "wrong_order"
    assert judge_attempt_detail("boat boat boat",
                                "sails on water")["verdict"] == "wrong"
    assert judge_attempt_detail("", "sails on water")["verdict"] == "wrong"


def test_fallback_stem_cut_rotates_positions():
    """Order drilling: repeated passes over the same archive quiz the same
    sentence at DIFFERENT stem positions."""
    from dsf_ai_service.substrate.autonomous_tutor import pick_tutor_item

    archive = ["the little boat sails on the water"]
    cuts = set()
    for rotation in range(0, 6):
        item = pick_tutor_item([], archive, rotation=rotation)
        cuts.add(len(item["stem"].split()))
        assert (item["stem"] + " " + item["expected"]).split() == \
            "the little boat sails on the water".split()
    assert len(cuts) >= 3, f"stem positions must rotate, got {cuts}"
