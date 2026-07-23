from types import SimpleNamespace

from dsf_ai_service.loom_model.curriculum_scheduler import CurriculumScheduler
from dsf_ai_service import substrate_runner
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


class _AdmissionGuala:
    def __init__(self, *, pending=False):
        self.pending = pending
        self.read = []
        self.tick = 100
        self._live_converse_pending = 0
        self._live_interaction_pending = 0
        self.is_asleep = False

    def organism_experience_pending(self):
        return self.pending

    def _current_situation(self):
        return [], "her_room", "day"

    def read_sentence(self, sentence, **_kwargs):
        self.read.append(sentence)
        self.pending = True

    def _log_substrate_event(self, *_args, **_kwargs):
        return None


def _isolate_curriculum_runner(monkeypatch, guala):
    monkeypatch.setattr(substrate_runner, "_guala", guala)
    monkeypatch.setattr(substrate_runner, "_current_block", lambda: "study")
    monkeypatch.setattr(
        substrate_runner, "_scaffold_rate_cap_gate", lambda requested: requested)
    monkeypatch.setattr(substrate_runner, "_activity_bundle_id", lambda: None)
    monkeypatch.setattr(substrate_runner, "_pause_autonomy_for_bulk", lambda: None)
    monkeypatch.setattr(substrate_runner, "_resume_autonomy_for_bulk", lambda: None)
    monkeypatch.setattr(substrate_runner, "_bind_sensory_words", lambda _sentence: None)
    monkeypatch.setattr(substrate_runner, "_rate_window", [])


def test_curriculum_admits_no_sentence_while_prior_experience_is_pending(
        monkeypatch):
    guala = _AdmissionGuala(pending=True)
    _isolate_curriculum_runner(monkeypatch, guala)

    admitted, learned = substrate_runner._curriculum_feed_chunk(
        ["first", "second", "third"])

    assert (admitted, learned) == (0, 0)
    assert guala.read == []


def test_curriculum_admits_one_sentence_then_waits_for_exact_settlement(
        monkeypatch):
    guala = _AdmissionGuala(pending=False)
    _isolate_curriculum_runner(monkeypatch, guala)

    admitted, learned = substrate_runner._curriculum_feed_chunk(
        ["first", "second", "third"])

    assert (admitted, learned) == (1, 0)
    assert guala.read == ["first"]


def test_curriculum_progress_advances_only_by_admitted_sentences(tmp_path):
    scheduler = CurriculumScheduler(
        state_dir=str(tmp_path),
        feed_chunk=lambda _sentences: (1, 0),
        is_busy=lambda: False,
        fetch_fn=lambda _book_id: ["first", "second", "third"],
        now_fn=lambda: 10.0,
    )
    scheduler.curriculum = [{"book_id": 1, "title": "test"}]
    scheduler.progress = {
        "book_index": 0,
        "offset": 0,
        "cycles": 0,
        "studied_book_ids": [],
        "last_ts": 0.0,
        "total_sentences": 0,
        "total_organ_tokens": 0,
    }

    status = scheduler.study_once()

    assert status["n_fed"] == 1
    assert scheduler.progress["offset"] == 1


def test_autonomous_reading_waits_for_prior_organism_settlement():
    class _Engine:
        def organism_experience_pending(self):
            return True

        @property
        def _corpora(self):
            raise AssertionError("a new sentence was accessed before settlement")

    Guala._atick_reading(
        _Engine(), SimpleNamespace(target="corpus", kind="READING"))

