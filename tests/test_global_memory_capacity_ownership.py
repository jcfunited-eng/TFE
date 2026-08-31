"""Focused proof that lifetime memory growth has explicit physical owners."""

import copy

import pytest

from dsf_ai_service.substrate.deep_atlas import (
    DeepAtlas,
    DeepAtlasCapacityExceeded,
)
from dsf_ai_service.substrate.window_manager import (
    WindowCapacityRefusal,
    WindowManager,
    _canonical_wal_bytes,
)
from dsf_ai_service.v4.gualaloom_v4_uf_kernel import DSF
from dsf_ai_service.v4.gualaloom_v5_engine import (
    BoundedSourceMap,
    Section,
    SectionModeCapacityRefusal,
    SourceIdentityCapacityRefusal,
)


def _deep_entry(motif, *, source="experience"):
    return {
        "chi": 7,
        "section": "ground",
        "motif": motif,
        "strength": 0.8,
        "encoded_strength": 0.8,
        "dwell_ticks": 8,
        "clarity": 0.9,
        "source": source,
    }


def _deep_entries_snapshot(atlas):
    if hasattr(atlas, "persistence_snapshot"):
        return copy.deepcopy(atlas.persistence_snapshot()["entries"])
    return copy.deepcopy(atlas.to_json()["entries"])


def _manager(*, retain=True, max_store_bytes=10_000_000,
             max_window_bytes=10_000_000):
    state = {"tick": 1, "atlas_calls": [], "events": []}
    manager = WindowManager(
        atlas_record_fn=lambda *args, **kwargs: state["atlas_calls"].append(
            (args, kwargs)),
        log_event_fn=lambda kind, **detail: state["events"].append(
            (kind, detail)),
        get_tick_fn=lambda: state["tick"],
        retain_closed_windows=retain,
        max_store_bytes=max_store_bytes,
        max_window_bytes=max_window_bytes,
    )
    return manager, state


def _dsf(seed):
    value = float(seed) / 100.0
    return DSF(value, value, value, value, value, value, value, value)


def _add_one(manager, context_id, motif):
    manager.begin_context(context_id)
    manager.add_entry(
        "word", "ground", motif, 7,
        context_id=context_id, source_tag=f"source-{motif}")


def test_deep_atlas_refuses_new_identity_without_changing_learned_state():
    probe = DeepAtlas(max_bytes=1_000_000)
    assert probe.promote(_deep_entry(1), "episodic", 1)
    exact_first_bytes = probe.snapshot()["logical_bytes"]

    atlas = DeepAtlas(max_bytes=exact_first_bytes)
    assert atlas.promote(_deep_entry(1), "episodic", 1)
    before_entries = _deep_entries_snapshot(atlas)

    assert atlas.promote(_deep_entry(2), "episodic", 2) is False
    assert _deep_entries_snapshot(atlas) == before_entries
    status = atlas.snapshot()
    assert status["logical_bytes"] == exact_first_bytes
    assert status["capacity_refusals"] == 1
    assert status["recent_capacity_refusals"][0]["operation"] == "promote"


def test_deep_atlas_refuses_oversize_reinforcement_atomically():
    probe = DeepAtlas(max_bytes=1_000_000)
    assert probe.promote(_deep_entry(1), "episodic", 1)
    existing_bytes = probe.snapshot()["logical_bytes"]

    atlas = DeepAtlas(max_bytes=existing_bytes + 8)
    assert atlas.promote(_deep_entry(1), "episodic", 1)
    before_entries = _deep_entries_snapshot(atlas)
    assert atlas.promote(
        _deep_entry(1, source="x" * 1000), "episodic", 2) is False
    assert _deep_entries_snapshot(atlas) == before_entries
    assert atlas.snapshot()["recent_capacity_refusals"][0][
        "operation"] == "reinforce"


def test_deep_atlas_restore_never_discards_state_to_fit():
    source = DeepAtlas(max_bytes=1_000_000)
    assert source.promote(_deep_entry(1), "episodic", 1)
    payload = source.to_json()
    required = source.snapshot()["logical_bytes"]

    target = DeepAtlas(max_bytes=required - 1)
    with pytest.raises(DeepAtlasCapacityExceeded):
        target.load_from_json(payload)


def test_deep_promotion_gate_never_reports_a_refused_write_as_promoted():
    probe = DeepAtlas(max_bytes=1_000_000)
    assert probe.promote(_deep_entry(1), "episodic", 1)
    atlas = DeepAtlas(max_bytes=probe.snapshot()["logical_bytes"])
    assert atlas.promote(_deep_entry(1), "episodic", 1)

    working = type("WorkingAtlas", (), {
        "band": 0,
        "entries": {7: [_deep_entry(2)]},
    })()
    assert atlas.dream_promotion_gate(working, 2, {}) == []
    assert atlas.live_count() == 1
    assert atlas.gate_rejects[-1]["failed"].startswith(
        "deep_atlas_capacity:")


def test_open_window_refusal_precedes_atlas_write_and_preserves_entries():
    probe, _ = _manager()
    _add_one(probe, "bounded", 1)
    one_entry_bytes = len(_canonical_wal_bytes(
        probe._contexts["bounded"].to_record()))

    manager, state = _manager(max_window_bytes=one_entry_bytes + 1024)
    _add_one(manager, "bounded", 1)
    manager._max_window_bytes = len(_canonical_wal_bytes(
        manager._contexts["bounded"].to_record()))
    assert len(state["atlas_calls"]) == 1
    with pytest.raises(WindowCapacityRefusal) as caught:
        manager.add_entry(
            "word", "ground", 2, 7,
            context_id="bounded", source_tag="source-2")
    assert caught.value.scope == "open_window"
    assert len(manager._contexts["bounded"].entries) == 1
    assert len(state["atlas_calls"]) == 1
    assert manager.resource_stats()["capacity_refusal_count"] == 1


def test_retained_store_refusal_keeps_prior_memory_and_context_retryable():
    probe, _ = _manager()
    _add_one(probe, "probe", 1)
    probe.end_context("probe")
    one_window_bytes = probe.resource_stats()["retained_store_bytes"]

    manager, _ = _manager(max_store_bytes=one_window_bytes + 1024)
    _add_one(manager, "first", 1)
    first_id = manager.end_context("first")
    assert manager.closed_window_count() == 1
    retained_after_first = manager.resource_stats()["retained_store_bytes"]

    _add_one(manager, "second", 2)
    manager._max_store_bytes = manager.resource_stats()["total_owned_bytes"]
    with pytest.raises(WindowCapacityRefusal) as caught:
        manager.end_context("second")
    assert caught.value.scope == "retained_window_store"
    assert manager.closed_window_count() == 1
    assert manager.closed_window(first_id)["window_id"] == first_id
    assert "second" in manager.open_context_ids()
    stats = manager.resource_stats()
    assert stats["retained_store_bytes"] == retained_after_first
    assert stats["reserved_store_bytes"] == 0
    assert stats["resident_window_metadata"] == 1


def test_production_transient_windows_have_zero_lifetime_metadata_growth():
    manager, _ = _manager(retain=False)
    for index in range(200):
        context_id = f"transient-{index}"
        _add_one(manager, context_id, index)
        manager.end_context(context_id)

    stats = manager.resource_stats()
    assert manager.closed_window_count() == 0
    assert stats["retained_store_bytes"] == 0
    assert stats["resident_window_metadata"] == 0
    assert stats["resident_window_locators"] == 0
    assert stats["resident_chi_locations"] == 0


def test_open_context_population_is_globally_bounded_too():
    probe, _ = _manager()
    probe.begin_context("first")
    one_open_bytes = probe.resource_stats()["open_context_bytes"]

    manager, _ = _manager(max_store_bytes=one_open_bytes + 1024)
    manager.begin_context("first")
    first_owned_bytes = manager.resource_stats()["total_owned_bytes"]
    manager._max_store_bytes = first_owned_bytes
    with pytest.raises(WindowCapacityRefusal) as caught:
        manager.begin_context("second")
    assert caught.value.scope == "open_window_store"
    assert manager.open_context_ids() == ("first",)
    assert manager.resource_stats()["total_owned_bytes"] == first_owned_bytes


def test_section_physical_mode_history_refuses_before_tombstone_or_append():
    probe = Section("probe", max_mode_storage_bytes=1_000_000)
    first_idx = probe._append_new_mode(_dsf(1), 7, "first", 1)
    assert first_idx == 0
    one_mode_bytes = probe.mode_resource_snapshot()["logical_bytes"]

    section = Section("bounded", max_mode_storage_bytes=one_mode_bytes)
    assert section._append_new_mode(_dsf(1), 7, "first", 1) == 0
    before_modes = list(section.modes)
    before_alive = list(section._mode_alive)
    assert section._append_new_mode(_dsf(2), 8, "second", 2) is None
    assert section.modes == before_modes
    assert section._mode_alive == before_alive
    proof = section.last_mode_capacity_refusal
    assert isinstance(proof, SectionModeCapacityRefusal)
    assert proof.current_bytes == one_mode_bytes
    assert proof.attempted_bytes > proof.budget_bytes

    class Atlas:
        def record(self, *args, **kwargs):
            raise AssertionError("refused reinforcement reached Atlas")

    committed, mode_idx, _ = section.receive(
        _dsf(1), 7, "first", Atlas(), familiarity=0.5,
        engine_tick=10 ** 30)
    assert committed is False
    assert mode_idx is None
    assert section.mode_resource_snapshot()["logical_bytes"] == one_mode_bytes


def test_distinct_source_identity_population_has_typed_capacity_refusal():
    source_map = BoundedSourceMap(int, max_key_bytes=3)
    source_map["a"] += 1
    before = dict(source_map)
    with pytest.raises(SourceIdentityCapacityRefusal):
        source_map["b"] += 1
    assert dict(source_map) == before
    assert source_map.resource_snapshot()["key_bytes"] <= 3
