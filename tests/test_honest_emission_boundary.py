"""Permanent guards for the committed-emission truth boundary.

These tests deliberately use small state doubles instead of booting another
Guala organism.  They exercise the production methods and interfaces without
creating background cognition threads or touching persisted state.
"""

import asyncio
import inspect
import sys
import threading
from collections import defaultdict
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import MethodType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsf_ai_service.v4.gualaloom_v5_engine import (  # noqa: E402
    ConversationTurnResult,
    EmissionCandidateProvenance,
    EmissionSettlement,
    FactEmissionSupport,
    FactEmissionTokenProvenance,
    Guala,
    _committed_candidate_provenance,
    _freeze_candidate_provenance,
    _grandurun_select_candidates,
)


def _dynamics_result(content="", sections=None, n_commits=0, organ=False):
    return {
        "content": content,
        "committed_sections": list(sections or []),
        "n_commits": n_commits,
        "organ_in_commits": organ,
        "tick": 10,
    }


def _settlement(content="", sections=None, n_commits=0, organ=False,
                tick=10, commit_provenance=()):
    return EmissionSettlement(
        content=content,
        committed_sections=tuple(sections or ()),
        n_commits=n_commits,
        organ_in_commits=organ,
        tick=tick,
        commit_provenance=tuple(commit_provenance))


def _lived_provenance(word="warm", section="modifier", mode_id=3,
                       source="joe", origin="grandurun"):
    return _freeze_candidate_provenance({
        "word": word,
        "source": source,
        "origin": origin,
        "episode_ref": "episode:joe:1",
    }, section, mode_id)


def _fact_transport_provenance(word="warm", trace_id="trace-transport"):
    return FactEmissionTokenProvenance(
        word=word,
        structural_fingerprint="f" * 64,
        recognized_strand_ids=("strand-transport",),
        supports=(FactEmissionSupport(
            window_id="window-transport",
            entry_index=1,
            experience_origin="emulated",
            source_tag="story_emulator",
            trace_id=trace_id,
            source_strand_id="strand-transport",
            modalities=("word", "sight", "sound"),
        ),),
    )


def test_only_verified_fact_strand_commits_surface(monkeypatch):
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    g = Guala()
    lived = _lived_provenance()
    try:
        assert g._committed_emission_response(_settlement(
            content="manufactured", sections=[], n_commits=0)) == (
            "", "silence_no_commit")

        # Both legacy candidate routes stay silent even when their old
        # provenance objects are internally self-consistent.
        assert g._committed_emission_response(_settlement(
            content="warm", sections=["modifier"], n_commits=1,
            commit_provenance=(lived,))) == ("", "silence_no_commit")
        organ = _lived_provenance(source="organ", origin="organ")
        assert g._committed_emission_response(_settlement(
            content="warm", sections=["modifier"], n_commits=1,
            organ=True, commit_provenance=(organ,))) == (
                "", "silence_no_commit")

        g.read_sentence("red fox runs warm", source="corpus")
        fact = g._compose_language_fact_settlement(("red", "fox"))
        assert g._committed_emission_response(fact) == (
            "runs warm", "fact_strand_commit")

        assert g._committed_emission_response(None) == (
            "", "silence_no_commit")
    finally:
        g.shutdown()


def test_ranked_non_dynamics_paths_are_retired_as_voice(monkeypatch):
    g = Guala.__new__(Guala)
    g.tick = 0
    g._emission_lock = threading.RLock()

    def must_not_gather(_words):
        raise AssertionError("uncommitted candidate gathering must not run")

    g._brain_emission_candidates = must_not_gather
    monkeypatch.setenv("EMISSION_DYNAMICS", "1")
    assert g._emit_from_invariants(
        [1], ["hello"], mode_override="topk") == EmissionSettlement(tick=0)

    monkeypatch.setenv("EMISSION_DYNAMICS", "0")
    assert g._emit_from_invariants(
        [1], ["hello"], mode_override="grandurun") == EmissionSettlement(tick=0)


def test_dynamics_source_contains_no_arc_argmax_fallback():
    source = inspect.getsource(Guala._emit_dynamics)
    assert "arcs_fallback" not in source
    assert ".arcs()" not in source
    assert "best_fallback" not in source
    assert "agency_cross_modal_fallback" not in source
    assert "cross_modal_fallback" not in source

    voice_router = inspect.getsource(Guala._emit_from_invariants)
    assert "return self._emit_grandurun" not in voice_router
    assert "topk path" not in voice_router


def test_committed_candidate_provenance_is_exact_and_missing_stays_empty():
    candidate = {
        "word": "warm",
        "source": "joe",
        "origin": "organ",
        "chi": 7,
        "sensory_refs": ["pic:p1", "snd:s1"],
        "episode_refs": ["episode:joe:4"],
        "bundle_id": "bundle:b1",
    }
    provenance = _freeze_candidate_provenance(candidate, "modifier", 3)
    assert provenance == EmissionCandidateProvenance(
        section="modifier", mode_id=3, word="warm", source="joe",
        origin="organ", chi=7,
        sensory_refs=("pic:p1", "snd:s1"),
        episode_refs=("episode:joe:4",),
        bundle_ids=("bundle:b1",))

    committed = _committed_candidate_provenance(
        [{"section": "modifier", "mode_id": 3, "word": "warm"}],
        {("modifier", 3): [provenance]})
    settlement = EmissionSettlement(
        content="warm", committed_sections=("modifier",), n_commits=1,
        organ_in_commits=any(p.origin == "organ" for p in committed),
        tick=12, commit_provenance=committed)
    assert settlement.organ_in_commits is True
    assert settlement.commit_provenance == (provenance,)

    empty = _freeze_candidate_provenance(
        {"word": "plain"}, "subject", 1)
    assert empty.source is None
    assert empty.origin is None
    assert empty.sensory_refs == ()
    assert empty.episode_refs == ()
    assert empty.bundle_ids == ()


def test_grandurun_selector_preserves_only_upstream_provenance_evidence():
    sections = {
        "modifier": SimpleNamespace(modes=[(None, None, "warm")]),
    }
    evidence = {
        "chi": 7,
        "source": "joe",
        "origin": "deep_atlas",
        "sensory_refs": ["pic:p1"],
        "episode_ref": "episode:joe:4",
        "bundle_id": "bundle:b1",
    }
    candidates = _grandurun_select_candidates(
        [7], [(evidence, {"modifier": {"0": 1.0}}, 1.0)],
        sections, set(), top_k=10)
    preserved = _freeze_candidate_provenance(
        candidates[0], "modifier", 0)
    assert preserved == EmissionCandidateProvenance(
        section="modifier", mode_id=0, word="warm", source="joe",
        origin="deep_atlas", chi=7, sensory_refs=("pic:p1",),
        episode_refs=("episode:joe:4",), bundle_ids=("bundle:b1",))

    missing = _grandurun_select_candidates(
        [7], [({}, {"modifier": {"0": 1.0}}, 1.0)],
        sections, set(), top_k=10)
    ungrounded = _freeze_candidate_provenance(
        missing[0], "modifier", 0)
    assert ungrounded.source is None
    assert ungrounded.origin is None
    assert ungrounded.chi is None
    assert ungrounded.sensory_refs == ()
    assert ungrounded.episode_refs == ()
    assert ungrounded.bundle_ids == ()


def test_missing_candidate_source_cannot_crash_dynamics_source_match():
    source = inspect.getsource(Guala._emit_dynamics)
    assert 'c.get("source") in ("joe", "joe_voice", "wc", "c1")' in source
    assert 'c["source"] in ("joe", "joe_voice", "wc", "c1")' not in source


def test_provenance_excludes_displaced_and_suppressed_commits():
    displaced = _freeze_candidate_provenance({
        "word": "organ-word", "origin": "organ", "source": "organ",
    }, "modifier", 1)
    surfaced = _freeze_candidate_provenance({
        "word": "corpus-word", "origin": "grandurun", "source": "corpus",
    }, "modifier", 2)
    duplicate = _freeze_candidate_provenance({
        "word": "corpus-word", "origin": "organ", "source": "organ",
    }, "object", 4)

    exact = _committed_candidate_provenance(
        [{"section": "modifier", "mode_id": 2, "word": "corpus-word"}],
        {
            ("modifier", 1): [displaced],
            ("modifier", 2): [surfaced],
            ("object", 4): [duplicate],
        })

    assert exact == (surfaced,)
    assert all(item.origin != "organ" for item in exact)
    assert _committed_candidate_provenance(
        [{"section": "modifier", "mode_id": 2, "word": "corpus-word"}],
        {("modifier", 2): [surfaced, surfaced]}) == ()


class _ConversationStub:
    def __init__(self, response, response_source, dynamics,
                 recalled_pictures=(), commit_provenance=()):
        self.response = response
        self._last_response_source = response_source
        self._last_dynamics_result = dynamics
        self._last_emission_id = "e1" if response else None
        self._last_recalled_pictures = []
        self._pictures = {}
        self.recalled_pictures = tuple(recalled_pictures)
        self.commit_provenance = tuple(commit_provenance)
        self._current_activity = None
        self.tick = 10
        self.vocab = {"warm"}
        self.source_history = defaultdict(int)
        self.is_asleep = False
        self._live_converse_pending = False

    def _current_situation(self):
        return [], None, None

    def converse(self, _text, **_kwargs):
        dynamics = self._last_dynamics_result or {}
        return ConversationTurnResult(
            response=self.response,
            response_source=self._last_response_source,
            emission_id=self._last_emission_id,
            committed_sections=tuple(
                dynamics.get("committed_sections") or ()),
            recalled_pictures=self.recalled_pictures,
            source_turn_index=1,
            commit_provenance=self.commit_provenance)

    def log_event(self, *_args, **_kwargs):
        return None

    def introspect(self):
        return {"vocab": len(self.vocab)}


@pytest.mark.parametrize(
    "response,response_source,dynamics",
    [
        ("", "silence_no_commit", _dynamics_result()),
        ("warm", "fact_strand_commit", _dynamics_result(
            "warm", ["language_fact"], 1)),
    ],
)
def test_runner_remote_transports_engine_truth_without_second_gate(
        monkeypatch, response, response_source, dynamics):
    import dsf_ai_service.substrate_runner as runner

    stub = _ConversationStub(response, response_source, dynamics)
    monkeypatch.setattr(runner, "_guala", stub)
    monkeypatch.setattr(runner, "_synthesize_voice", lambda _text: None)

    result = runner._cmd_converse("hello", "joe", emission_mode="grandurun")
    assert result["response"] == response
    assert result["response_source"] == response_source
    if response:
        # A single genuinely committed section is sufficient.
        assert result["committed_sections"] == ["language_fact"]
        assert result["emission_id"] == "e1"
    else:
        assert "speech" not in result
        assert "emission_id" not in result
        assert "committed_sections" not in result
        assert result["commit_provenance"] == []


def test_runner_carries_exact_turn_local_commit_provenance(monkeypatch):
    import dsf_ai_service.substrate_runner as runner

    provenance = _freeze_candidate_provenance({
        "word": "warm",
        "source": "joe",
        "origin": "organ",
        "chi": 7,
        "sensory_refs": ["pic:p1"],
        "episode_refs": ["episode:joe:1"],
        "bundle_ids": ["bundle:b1"],
    }, "modifier", 3)
    stub = _ConversationStub(
        "warm", "fact_strand_commit",
        _dynamics_result("warm", ["language_fact"], 1),
        commit_provenance=(_fact_transport_provenance(),))
    monkeypatch.setattr(runner, "_guala", stub)
    monkeypatch.setattr(runner, "_synthesize_voice", lambda _text: None)

    result = runner._cmd_converse("hello", "joe", emission_mode="grandurun")

    assert result["response_source"] == "fact_strand_commit"
    assert result["commit_provenance"] == [
        _fact_transport_provenance().as_record()]


def test_runner_uses_turn_local_picture_snapshot(monkeypatch):
    import dsf_ai_service.substrate_runner as runner

    stub = _ConversationStub(
        "warm", "fact_strand_commit",
        _dynamics_result("warm", ["language_fact"], 1),
        recalled_pictures=(("motif", "right-picture"),))
    stub._pictures = {
        "right-picture": SimpleNamespace(title="Right"),
        "wrong-picture": SimpleNamespace(title="Wrong"),
    }
    stub._last_recalled_pictures = [("motif", "wrong-picture")]
    monkeypatch.setattr(runner, "_guala", stub)
    monkeypatch.setattr(runner, "_synthesize_voice", lambda _text: None)

    result = runner._cmd_converse("hello", "joe", emission_mode="grandurun")
    assert result["pictures"] == [
        {"item_id": "right-picture", "title": "Right"}]


def _task_record():
    return {
        "status": "queued",
        "phase": None,
        "started_at": 1.0,
        "started_tick": 0,
        "source": "joe",
    }


def test_app_embedded_and_remote_preserve_the_same_truth(monkeypatch):
    import dsf_ai_service.app as appmod

    provenance = _fact_transport_provenance()
    truth = {
        "response": "warm",
        "response_source": "fact_strand_commit",
        "motifs": 1,
        "emission_id": "e1",
        "committed_sections": ["language_fact"],
        "source_turn_index": 1,
        "commit_provenance": [provenance.as_record()],
    }

    embedded = _ConversationStub(
        truth["response"], truth["response_source"],
        _dynamics_result("warm", ["language_fact"], 1),
        commit_provenance=(provenance,))
    monkeypatch.setattr(appmod, "_guala", embedded)
    monkeypatch.setattr(appmod, "SUBSTRATE_MODE", "embedded")
    appmod._converse_tasks["embedded"] = _task_record()
    asyncio.run(appmod._run_converse(
        "embedded", "hello", "joe", "grandurun"))
    embedded_task = dict(appmod._converse_tasks.pop("embedded"))

    class _Client:
        async def call(self, *_args, **_kwargs):
            return dict(truth)

    monkeypatch.setattr(appmod, "_guala", None)
    monkeypatch.setattr(appmod, "SUBSTRATE_MODE", "remote")
    monkeypatch.setattr(appmod, "_get_substrate_client", lambda: _Client())
    appmod._converse_tasks["remote"] = _task_record()
    asyncio.run(appmod._run_converse(
        "remote", "hello", "joe", "grandurun"))
    remote_task = dict(appmod._converse_tasks.pop("remote"))

    for key in ("response", "response_source", "emission_id",
                "committed_sections", "source_turn_index"):
        assert embedded_task[key] == truth[key]
        assert remote_task[key] == truth[key]
    assert "commit_provenance" not in embedded_task
    assert "commit_provenance" not in remote_task
    poll_source = inspect.getsource(appmod.get_converse_task)
    assert '"commit_provenance"' not in poll_source


def test_concurrent_turns_return_distinct_local_ids_and_attribution(monkeypatch):
    """Two same-source turns reach phase 7 at the same structural tick.

    The old tick/first-chi/count fingerprint would collide.  The production
    converse/read_sentence path must carry each atomically captured persisted
    source-history index into a distinct immutable result and record.
    """
    monkeypatch.setenv("CONVERSE_PHASED", "1")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    g = Guala()
    g.read_sentence("alpha warm", source="corpus")
    g.read_sentence("beta cold", source="corpus")
    both_entered = threading.Event()
    release_alpha = threading.Event()
    release_beta = threading.Event()
    entered_lock = threading.Lock()
    entered_count = {"n": 0}
    results = {}
    errors = []
    emission_calls = {"n": 0}

    def fast_read_word(self, word, **_kwargs):
        with self.lock:
            self.tick += 1
        with entered_lock:
            entered_count["n"] += 1
            if entered_count["n"] == 2:
                both_entered.set()
        release = release_alpha if word == "alpha" else release_beta
        assert release.wait(timeout=10)
        return 0, "subject", {}, None, {}

    def legacy_emission_must_not_run(self, *_args, **_kwargs):
        emission_calls["n"] += 1
        raise AssertionError("legacy emission path must not run")

    g.read_word = MethodType(fast_read_word, g)
    g._recall_response = lambda *_args, **_kwargs: (None, ())
    g._emit_from_invariants = MethodType(legacy_emission_must_not_run, g)
    g._open_response_window = lambda *_args, **_kwargs: None

    def run(key, text):
        try:
            results[key] = g.converse(text, source="joe")
        except Exception as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    try:
        threads = [
            threading.Thread(target=run, args=("a", "alpha")),
            threading.Thread(target=run, args=("b", "beta")),
        ]
        for thread in threads:
            thread.start()
        assert both_entered.wait(timeout=10)
        assert g._live_converse_pending == 2

        # A conversation counted first is a hard barrier for both autonomous
        # entry points, even though their seed state is otherwise sufficient.
        g.sections["subject"].commits.append({"chi": 4})
        g._sample_autonomous_seeds = lambda n=12: [
            {"chi_key": 4, "strength": 1.0}]
        with g.lock:
            assert g.compose_autonomous() is None
            assert Guala._do_emit(g) is False
        assert emission_calls["n"] == 0

        release_alpha.set()
        threads[0].join(timeout=10)
        assert not threads[0].is_alive()
        assert g._live_converse_pending == 1

        release_beta.set()
        for thread in threads:
            thread.join(timeout=15)

        assert not errors
        assert all(not thread.is_alive() for thread in threads)
        assert g._live_converse_pending == 0
        assert set(results) == {"a", "b"}
        ids = {turn.emission_id for turn in results.values()}
        assert len(ids) == 2
        assert {turn.response for turn in results.values()} == {"warm", "cold"}
        assert all(turn.response_source == "fact_strand_commit"
                   for turn in results.values())
        assert {turn.commit_provenance[0].word
                for turn in results.values()} == {"warm", "cold"}
        assert {turn.source_turn_index for turn in results.values()} == {1, 2}
        assert {eid.split(":")[1] for eid in ids} == {"1", "2"}

        recorded_inputs = {
            g._emission_records[turn.emission_id]["input_text"]
            for turn in results.values()
        }
        assert recorded_inputs == {"alpha", "beta"}
        assert all(
            g._emission_records[turn.emission_id]["commit_provenance"]
            == [turn.commit_provenance[0].as_record()]
            for turn in results.values())
        for turn in results.values():
            with pytest.raises(FrozenInstanceError):
                turn.response = "changed"
    finally:
        g.shutdown()


def test_emit_from_invariants_serializes_every_direct_call(monkeypatch):
    g = Guala.__new__(Guala)
    g.tick = 0
    g._emission_lock = threading.RLock()
    first_inside = threading.Event()
    release_first = threading.Event()
    second_calling = threading.Event()
    second_inside = threading.Event()
    call_lock = threading.Lock()
    call_count = {"n": 0}
    errors = []

    def gather(_words):
        with call_lock:
            call_count["n"] += 1
            call_number = call_count["n"]
        if call_number == 1:
            first_inside.set()
            assert release_first.wait(timeout=10)
        else:
            second_inside.set()
        return [({}, {}, 1.0)]

    g._brain_emission_candidates = gather
    g._emit_dynamics = lambda *_args, **_kwargs: EmissionSettlement(tick=0)
    monkeypatch.setenv("EMISSION_DYNAMICS", "1")

    def run(is_second=False):
        try:
            if is_second:
                second_calling.set()
            g._emit_from_invariants(
                [1], ["hello"], mode_override="grandurun")
        except Exception as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    first = threading.Thread(target=run)
    second = threading.Thread(target=run, args=(True,))
    first.start()
    assert first_inside.wait(timeout=10)
    second.start()
    assert second_calling.wait(timeout=10)
    assert not second_inside.wait(timeout=0.2)
    release_first.set()
    first.join(timeout=10)
    second.join(timeout=10)

    assert not errors
    assert not first.is_alive()
    assert not second.is_alive()
    assert second_inside.is_set()
    assert call_count["n"] == 2


def _autonomous_stub(settlement):
    g = Guala.__new__(Guala)
    g.tick = 10
    g._emission_lock = threading.RLock()
    g._live_converse_state_lock = threading.Lock()
    g._live_converse_pending = 0
    g.sections = {"subject": SimpleNamespace(commits=[{"chi": 4}])}
    g._last_emission_tick = -100
    g._last_dynamics_result = _dynamics_result(
        settlement.content, settlement.committed_sections,
        settlement.n_commits, settlement.organ_in_commits)
    g._emit_from_invariants = lambda *_args, **_kwargs: settlement
    g._recall_sight_from_atlas = lambda *_args, **_kwargs: []
    g._open_response_window_calls = []
    g._open_response_window = lambda *args, **kwargs: (
        g._open_response_window_calls.append((args, kwargs)))
    g._substrate_event_calls = []
    g._log_substrate_event = lambda kind, **detail: (
        g._substrate_event_calls.append((kind, detail)))
    g.coordinator = SimpleNamespace(
        _presence={"joe": True}, _pair_bond={"joe": True})
    g.needs = SimpleNamespace(connection=0.4)
    g._total_emissions = 0
    g._emission_lengths = []
    g._question_count = 0
    g._novel_compositions = 0
    g._seen_triples = set()
    g._self_hear = lambda *_args, **_kwargs: (
        pytest.fail("autonomous silence must not self-hear"))
    return g


def test_autonomous_silence_has_no_downstream_cyclic_effects():
    g = _autonomous_stub(_settlement("manufactured", [], 0))
    assert Guala._do_emit(g) is False
    assert g._total_emissions == 0
    assert g._emission_lengths == []
    assert g._open_response_window_calls == []
    assert [kind for kind, _ in g._substrate_event_calls] == [
        "emission_silence"]

    activity = SimpleNamespace(started_tick=9)
    g._do_emit = lambda: False
    Guala._atick_emitting(g, activity)
    assert g.needs.connection == pytest.approx(0.4)


def test_autonomous_genuine_commit_is_counted_and_can_satisfy_connection():
    g = Guala()
    try:
        g.read_sentence("red fox runs warm", source="corpus")
        settlement = g._compose_language_fact_settlement(("red", "fox"))
        g.sections["subject"].commits.append({"chi": 4})
        g._emit_from_invariants = lambda *_args, **_kwargs: settlement
        g._recall_sight_from_atlas = lambda *_args, **_kwargs: []
        opened = []
        events = []
        g._open_response_window = lambda *args, **kwargs: opened.append(
            (args, kwargs))
        g._log_substrate_event = lambda kind, **detail: events.append(
            (kind, detail))
        g.coordinator._presence["joe"] = True
        g.coordinator._pair_bond["joe"] = True
        before_total = g._total_emissions

        assert Guala._do_emit(g) is True
        assert g._total_emissions == before_total + 1
        assert g._emission_lengths[-1] == 2
        assert len(opened) == 1
        assert [kind for kind, _ in events] == ["emission"]
    finally:
        g.shutdown()


def test_self_hear_requires_and_persists_commit_provenance(monkeypatch):
    g = Guala.__new__(Guala)
    g.tick = 10
    g.atlas = SimpleNamespace(band=0, entries={})
    g._self_hearing = False
    reads = []
    windows = []
    events = []

    def read_sentence(text, **kwargs):
        reads.append((text, kwargs))
        g.tick += 1

    g.read_sentence = read_sentence
    g._open_response_window = lambda *args, **kwargs: windows.append(
        (args, kwargs))
    g._tag_response_bindings = lambda *_args, **_kwargs: None
    g._log_substrate_event = lambda kind, **detail: events.append(
        (kind, detail))
    monkeypatch.setenv("SELF_HEARING_ENABLED", "1")
    monkeypatch.setenv("SELF_VOICE_AUDIO_ENABLED", "0")

    Guala._self_hear(
        g, "manufactured", "joe", emission_id=None,
        response_source="silence_no_commit")
    assert reads == []
    assert windows == []

    Guala._self_hear(
        g, "legacy", "joe", emission_id="old",
        response_source="v5_commit")
    assert reads == []
    assert windows == []

    Guala._self_hear(
        g, "warm", "joe", emission_id="e1",
        response_source="fact_strand_commit")
    assert reads[0][1]["source"] == "guala"
    assert reads[0][1]["episode_ref"] == "emission:e1:fact_strand_commit"
    assert len(windows) == 1
    assert events[-1][0] == "self_heard"
    assert events[-1][1]["response_source"] == "fact_strand_commit"


def test_legacy_emission_records_are_preserved_and_never_reinforced():
    g = Guala.__new__(Guala)
    provenance = _lived_provenance().as_record()
    g._emission_records = {
        "legacy": {"text": "unknown provenance", "input_text": "hello"},
        "committed": {
            "text": "warm", "input_text": "hello",
            "response_source": "v5_commit",
            "committed_sections": ["modifier"],
            "n_commits": 1,
            "commit_provenance": [provenance],
        },
        "missing_link": {
            "text": "warm", "input_text": "hello",
            "response_source": "v5_commit",
            "committed_sections": ["modifier"],
            "n_commits": 1,
            "commit_provenance": [{
                **provenance,
                "episode_refs": [], "sensory_refs": [], "bundle_ids": [],
            }],
        },
        "mismatched": {
            "text": "cold", "input_text": "hello",
            "response_source": "v5_commit",
            "committed_sections": ["modifier"],
            "n_commits": 1,
            "commit_provenance": [provenance],
        },
    }
    assert g._certified_emission_record("legacy") is None
    assert g._emission_records["legacy"]["text"] == "unknown provenance"
    assert g._certified_emission_record("committed") is None
    assert g._certified_emission_record("missing_link") is None
    assert g._certified_emission_record("mismatched") is None


def test_teacher_handlers_and_ui_consume_certified_truth_only():
    import dsf_ai_service.app as appmod
    import dsf_ai_service.substrate_runner as runner

    for handler in (
            appmod.handle_teacher_feedback_local,
            appmod.handle_teacher_correction_local,
            runner.handle_teacher_feedback,
            runner.handle_teacher_correction):
        assert "_certified_emission_record" in inspect.getsource(handler)

    ui = (ROOT / "dsf_ai_service/static/gualaloom.html").read_text()
    assert "const resp=d.response||'...';" not in ui
    assert "if(!emissionText)" in ui
    committed_gate = "d.response_source==='fact_strand_commit'"
    assert committed_gate in ui
    assert "addEmissionMsg(resp,d.emission_id);gualaSpeak(resp);" in ui

    app_source = inspect.getsource(appmod._run_converse)
    runner_source = inspect.getsource(runner.handle_gualaloom_post)
    assert 'task["response_source"] = "sleep_quiet"' in app_source
    assert '"response_source": "sleep_quiet"' in runner_source

    v7_feedback = inspect.getsource(runner.handle_v7_feedback)
    assert "_last_converse_input" not in v7_feedback
    assert "_last_converse_reply" not in v7_feedback
    assert "apply_teacher_correction" not in v7_feedback

    # The MCP bridge is a transparent transport; it does not synthesize or
    # reinterpret response content after polling completes.
    bridge = (ROOT / "bridge/server.py").read_text()
    assert 'if pd.get("status") in ("complete", "error"):\n                    return pd' in bridge
