"""Focused production contracts for canonical binding-window recall."""

import copy
import json
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dsf_ai_service.substrate.recall_query import RecallEngine, RecallQuery
from dsf_ai_service.substrate.window_manager import (
    WindowIntegrityError,
    WindowManager,
)


def _manager(*, tick=None, mirror=None, events=None, atlas_calls=None):
    tick = tick if tick is not None else {"value": 0}
    mirror = mirror if mirror is not None else {}
    events = events if events is not None else []
    atlas_calls = atlas_calls if atlas_calls is not None else []

    def atlas_record(section, motif, chi, at_tick, **kwargs):
        atlas_calls.append((section, motif, chi, at_tick, kwargs))

    manager = WindowManager(
        atlas_record_fn=atlas_record,
        log_event_fn=lambda kind, **detail: events.append((kind, detail)),
        get_tick_fn=lambda: tick["value"],
        get_presence_fn=lambda: {"joe": True},
        get_affect_fn=lambda: {"arousal": 0.7, "valence": -0.2},
        get_needs_fn=lambda: {"stability": 0.6, "connection": 0.8},
        atlas_windows=mirror,
    )
    return manager, tick, mirror, events, atlas_calls


def _add(manager, context_id, chi, *, modality="word", section="listen",
         source_tag="word", tick=1, fact=None, **kwargs):
    return manager.add_entry(
        modality=modality,
        section=section,
        motif_id=chi * 10 + tick,
        chi=chi,
        tick=tick,
        source_tag=source_tag,
        context_id=context_id,
        structural_fact=fact,
        source="joe",
        episode_ref=f"episode:{context_id}",
        bundle_id=f"bundle:{context_id}",
        salience=1.25,
        dwell_ticks=4,
        **kwargs,
    )


def test_complete_json_provenance_ordered_language_and_fact_strand():
    manager, tick, mirror, _events, atlas_calls = _manager()
    manager.open("sentence", context_id="sentence:1", speaker="joe")

    _add(
        manager, "sentence:1", 11, source_tag="moon", tick=10,
        fact={"kind": "relation", "subject": "moon",
              "relation": "is", "object": "bright"},
        sensory_refs=["pic:moon"],
        presence=["joe"], location="her_room", sky_state="night",
        place=["window"], ambient=["quiet"], surprise=0.4,
        detail={"observation": "spoken and seen"},
        phase_vec=[1 + 2j, 3 + 4j],
    )
    # A second section commit for the same token retains the same language
    # ordinal; the next token advances it.
    _add(manager, "sentence:1", 11, section="subject",
         source_tag="moon", tick=10)
    _add(manager, "sentence:1", 12, section="object",
         source_tag="bright", tick=11)
    window_id = manager.close("sentence_complete", context_id="sentence:1")

    record = manager.windows[window_id]
    assert [entry["language_position"] for entry in record["entries"]] == [0, 0, 1]
    provenance = record["entries"][0]["provenance"]
    assert provenance["source"] == "joe"
    assert provenance["episode_ref"] == "episode:sentence:1"
    assert provenance["bundle_id"] == "bundle:sentence:1"
    assert provenance["scene"] == {
        "presence": ["joe"], "location": "her_room",
        "sky_state": "night", "place": ["window"],
        "ambient": ["quiet"],
    }
    assert provenance["affect"]["arousal"] == 0.7
    assert provenance["affect"]["valence"] == -0.2
    assert provenance["affect"]["surprise"] == 0.4
    assert provenance["needs"] == {"stability": 0.6, "connection": 0.8}
    assert provenance["salience"] == 1.25
    assert provenance["dwell_ticks"] == 4
    assert provenance["detail"]["observation"] == "spoken and seen"
    assert provenance["detail"]["phase_vec"][0] == {"real": 1.0, "imag": 2.0}
    assert provenance["structural_fact"]["relation"] == "is"
    json.dumps(manager.snapshot(), allow_nan=False)

    # Atlas receives only a compatibility cross-reference.  Its mapping is a
    # detached copy and cannot become the recall authority.
    assert atlas_calls[0][4]["window_id"] == window_id
    assert atlas_calls[0][4]["window_entry_index"] == 0
    assert mirror[window_id] == record
    assert mirror[window_id] is not record


def test_concurrent_contexts_and_adds_are_isolated_and_ordered():
    manager, _tick, _mirror, _events, _calls = _manager()
    both_added = threading.Barrier(3)
    close_a = threading.Event()
    close_b = threading.Event()
    finished_a = threading.Event()
    finished_b = threading.Event()
    errors = []

    def worker(context_id, chi, close_signal, finished):
        try:
            manager.begin_context(context_id, "sentence")
            for index in range(50):
                _add(manager, context_id, chi, source_tag=f"{context_id}-{index}",
                     tick=index + 1)
            both_added.wait(timeout=5)
            assert close_signal.wait(timeout=5)
            manager.end_context(context_id, "sentence_complete")
            finished.set()
        except BaseException as error:  # surfaced below
            errors.append(error)

    threads = [
        threading.Thread(target=worker, args=("sentence:a", 21, close_a, finished_a)),
        threading.Thread(target=worker, args=("sentence:b", 22, close_b, finished_b)),
    ]
    for thread in threads:
        thread.start()
    both_added.wait(timeout=5)

    close_a.set()
    assert finished_a.wait(timeout=5)
    midway = manager.snapshot()
    assert "sentence:a" not in midway["open_contexts"]
    assert "sentence:b" in midway["open_contexts"]
    assert len(midway["open_contexts"]["sentence:b"]["entries"]) == 50

    close_b.set()
    assert finished_b.wait(timeout=5)
    for thread in threads:
        thread.join(timeout=5)
    assert not errors
    assert all(not thread.is_alive() for thread in threads)
    assert len(manager.windows) == 2
    assert len(manager.lookup_chi(21)) == 1
    assert len(manager.lookup_chi(22)) == 1

    # Multiple writers to one explicitly shared context still receive exact,
    # gap-free entry indices.
    manager.begin_context("shared", "shared_context")
    indices = []
    index_lock = threading.Lock()

    def shared_writer(writer):
        local = [
            _add(manager, "shared", 30 + writer, modality="sound",
                 section="audio", source_tag=str(writer), tick=index)
            for index in range(40)
        ]
        with index_lock:
            indices.extend(local)

    writers = [threading.Thread(target=shared_writer, args=(writer,))
               for writer in range(4)]
    for writer in writers:
        writer.start()
    for writer in writers:
        writer.join(timeout=5)
    shared_id = manager.end_context("shared", "complete")
    assert sorted(indices) == list(range(160))
    assert [entry["entry_index"] for entry in manager.windows[shared_id]["entries"]] == list(range(160))


def test_no_window_count_eviction_and_first_class_chi_index():
    manager, _tick, _mirror, _events, _calls = _manager()
    for index in range(2005):
        context_id = f"retained:{index}"
        _add(manager, context_id, index % 7, modality="sound",
             section="audio", tick=index)
        manager.end_context(context_id, "complete")

    assert len(manager.windows) == 2005
    snapshot = manager.snapshot()
    assert len(snapshot["windows"]) == 2005
    assert set(snapshot["chi_index"]) == {str(index) for index in range(7)}
    assert sum(len(bucket) for bucket in snapshot["chi_index"].values()) == 2005
    assert len(manager.lookup_chi(0)) == 287


def test_snapshot_restore_is_atomic_and_rejects_index_corruption():
    manager, _tick, _mirror, _events, _calls = _manager()
    _add(manager, "closed", 41, fact={"kind": "language_fact", "value": "warm"})
    closed_id = manager.end_context("closed", "complete")
    _add(manager, "still-open", 42, source_tag="continuing")
    snapshot = manager.snapshot()

    restored, _tick2, mirror2, _events2, _calls2 = _manager()
    restored.restore(snapshot)
    assert restored.snapshot() == snapshot
    assert restored.validate_integrity() == ()
    assert restored.lookup_chi(41)[0]["window_id"] == closed_id
    assert "still-open" in restored.snapshot()["open_contexts"]
    assert mirror2 == snapshot["windows"]

    before = restored.snapshot()
    corrupt = copy.deepcopy(snapshot)
    corrupt["chi_index"]["41"][0]["entry_index"] = 999
    with pytest.raises(WindowIntegrityError, match="chi_index"):
        restored.restore(corrupt)
    assert restored.snapshot() == before


def test_recall_returns_all_windows_without_mislabeling_chi_routing_as_recognition():
    manager, _tick, mirror, events, _calls = _manager()

    _add(manager, "full", 51, fact={"kind": "fact", "name": "full"})
    _add(manager, "full", 52, section="subject", source_tag="second", tick=2)
    full_id = manager.end_context("full", "complete")

    _add(manager, "partial-a", 51)
    partial_a = manager.end_context("partial-a", "complete")
    _add(manager, "partial-b", 51, modality="sound", section="audio")
    partial_b = manager.end_context("partial-b", "complete")

    # Legacy constructor wiring resolves the mirror to its canonical owner.
    recall = RecallEngine(
        atlas_windows_fn=lambda: mirror,
        get_tick_fn=lambda: 100,
        log_event_fn=lambda kind, **detail: events.append((kind, detail)),
    )

    # Corrupt the compatibility mirror after construction.  Canonical recall
    # remains unchanged because it uses WindowManager's chi index and windows.
    mirror.clear()
    mirror["fabricated"] = {"window_id": "fabricated", "entries": []}
    result = recall.query(RecallQuery(chis=[51, 52], max_results=1))
    assert set(result.window_ids()) == {full_id, partial_a, partial_b}
    assert len(result.windows) == 3
    assert result.truncated is False
    assert result.resolution == "routing_candidates"
    assert result.selected_window_id is None
    assert result.unknown_reason == "requires_fact_strand_reciprocity"
    assert result.routing_projection == "chi_index"
    assert result.decision_authority is False
    full_candidate = next(candidate for candidate in result.candidates
                          if candidate["window_id"] == full_id)
    assert full_candidate["matched_chis"] == [51, 52]
    assert full_candidate["structural_facts"] == [{"kind": "fact", "name": "full"}]

    # Equal Chi coverage is not broken by recency, affect, storage order, or
    # max_results.  The projection never becomes recognition authority.
    _add(manager, "full-tie", 51)
    _add(manager, "full-tie", 52, tick=2)
    tie_id = manager.end_context("full-tie", "complete")
    tied = recall.query(RecallQuery(
        chis=[51, 52], section_hint="word", max_results=1))
    assert tie_id in tied.window_ids()
    assert tied.resolution == "routing_candidates"
    assert tied.selected_window_id is None
    assert tied.unknown_reason == "requires_fact_strand_reciprocity"
    assert tied.top_affect_strength() == 0.0

    absent = recall.query(RecallQuery(chis=[999999]))
    assert absent.windows == []
    assert absent.resolution == "unknown"
    assert absent.unknown_reason == "no_chi_route"


def test_unregistered_atlas_mapping_cannot_be_recall_authority():
    with pytest.raises(ValueError, match="cannot be recall authority"):
        RecallEngine(
            atlas_windows_fn=lambda: {"fabricated": {}},
            get_tick_fn=lambda: 0,
            log_event_fn=lambda *_args, **_kwargs: None,
        )
