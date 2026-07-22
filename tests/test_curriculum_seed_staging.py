"""GL-CMD-STAGE-CURRICULUM-SEED-20260722: the graded caption curriculum
(tools/curriculum_seed.json, Eve 2026-06-30) staged into the scheduler.

Design under test:
  - The seed is an ADDITIONAL curriculum entry appended AFTER the 10-book
    carousel (so persisted live progress indexes 0-9 keep their meaning).
  - Its captions feed IN FILE ORDER (the file's bundle order is its grade)
    through the same injected feed_chunk path as every book — intake
    mechanics untouched.
  - A missing seed file is exception-walled exactly like an unreachable
    book: the scheduler skips the entry and moves on.
"""

import json
import os

from dsf_ai_service.loom_model.curriculum_scheduler import (
    CurriculumScheduler, DEFAULT_CURRICULUM)
from dsf_ai_service.substrate.autonomous_tutor import is_quality_material

_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), ".."))
_SEED_PATH = os.path.join(_REPO_ROOT, "tools", "curriculum_seed.json")


def _seed_captions():
    with open(_SEED_PATH) as f:
        data = json.load(f)
    return [str(b["caption"]).strip()
            for b in data["bundles"] if b.get("caption")]


def _make_scheduler(tmp_path, fed):
    sched = CurriculumScheduler(
        state_dir=str(tmp_path),
        feed_chunk=lambda sents: (fed.extend(sents), 0) and (len(sents), 0),
        is_busy=lambda: False,
    )
    return sched


def test_seed_staged_after_ten_book_carousel():
    # Appended, not inserted: the original 10 Gutenberg ids keep their
    # positions so live curriculum_progress.json resumes unshifted.
    assert len(DEFAULT_CURRICULUM) == 11
    assert [b["book_id"] for b in DEFAULT_CURRICULUM[:10]] == [
        11, 12, 11339, 289, 271, 2591, 16, 113, 45, 514]
    seed = DEFAULT_CURRICULUM[10]
    assert seed["book_id"] == "seed:curriculum_seed_v1"
    assert seed["seed_path"] == "tools/curriculum_seed.json"


def test_scheduler_feeds_seed_captions_in_file_order(tmp_path):
    captions = _seed_captions()
    assert len(captions) == 100  # the seed's 100 bundles, all with captions
    fed = []
    sched = _make_scheduler(tmp_path, fed)
    # Land on the seed entry (index 10); chunk small to prove ordering
    # across multiple study steps, not just within one chunk.
    sched.progress["book_index"] = 10
    sched.chunk_size = 30
    statuses = []
    while True:
        st = sched.study_once()
        statuses.append(st)
        if st.get("state") != "studied" or st.get("book_complete"):
            break
    assert all(st["state"] == "studied" for st in statuses)
    assert all(st["book_id"] == "seed:curriculum_seed_v1" for st in statuses)
    # Every caption fed, exactly once, in the file's own graded order.
    assert fed == captions
    # Book-complete advances back to the start of the carousel (loop).
    assert statuses[-1]["book_complete"] is True
    assert sched.progress["book_index"] == 0
    assert "seed:curriculum_seed_v1" in sched.progress["studied_book_ids"]


def test_seed_resumes_from_persisted_offset(tmp_path):
    captions = _seed_captions()
    fed = []
    sched = _make_scheduler(tmp_path, fed)
    sched.progress["book_index"] = 10
    sched.progress["offset"] = 40
    sched.chunk_size = 25
    st = sched.study_once()
    assert st["state"] == "studied"
    assert fed == captions[40:65]


def test_missing_seed_file_is_walled_like_a_bad_book(tmp_path, monkeypatch):
    monkeypatch.setenv("CURRICULUM_SEED_PATH", str(tmp_path / "absent.json"))
    fed = []
    sched = _make_scheduler(tmp_path, fed)
    sched.progress["book_index"] = 10

    # Force the repo/app fallbacks to miss too, isolating the walled path.
    def _raise(rel_path):
        raise FileNotFoundError(rel_path)
    monkeypatch.setattr(sched, "_seed_caption_lines", _raise)

    st = sched.study_once()
    assert st["state"] == "fetch_failed"
    assert fed == []
    assert sched.progress["book_index"] == 0  # advanced past the bad entry


def test_seed_captions_pass_tutor_junk_gate():
    # Cross-check with Item 1: the graded material the seed stages is
    # exactly the kind of prose the tutor's junk gate must keep accepting.
    for cap in _seed_captions():
        assert is_quality_material(cap), f"seed caption rejected: {cap!r}"
