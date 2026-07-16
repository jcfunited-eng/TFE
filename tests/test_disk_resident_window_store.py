"""Disk-resident closed-window store contracts (GL-SPC-SUBSTRATE-TRUE Change 1).

Covers spec test item (b) and (c):
  * fetch-on-demand correctness for every read surface (lookup_chi,
    recall_snapshot, closed_window, the legacy ``windows`` mapping) against
    an in-RAM oracle built through the same real close path;
  * LRU content cache: byte budget honored, eviction evicts, evicted
    content still fetches correctly from disk;
  * detached-copy semantics: mutating any returned record never corrupts
    canonical memory;
  * locator validity after compaction: compaction rewrites segment files,
    so the locator must be rebuilt — every window stays fetchable, from the
    new generation's files;
  * named loud halt (WindowStoreIntegrityHalt) when a located record is
    corrupted on disk — never a silent miss (P4);
  * boot index scan (restore_from_wal) does not materialize content: no
    pending records, empty cache, until a read is actually asked for.
"""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dsf_ai_service.substrate.window_manager import (  # noqa: E402
    WAL_DIRNAME,
    WindowManager,
    WindowStoreIntegrityHalt,
)


def _build(cache_mb=None):
    if cache_mb is not None:
        os.environ["GUALA_WINDOW_CACHE_MB"] = str(cache_mb)
    else:
        os.environ.pop("GUALA_WINDOW_CACHE_MB", None)
    tick = {"value": 0}
    events = []
    manager = WindowManager(
        atlas_record_fn=lambda *a, **kw: None,
        log_event_fn=lambda kind, **detail: events.append((kind, detail)),
        get_tick_fn=lambda: tick["value"],
        atlas_windows={},
    )
    return manager, tick, events


def _close_window(manager, tick, context_id, *, chi, entries=1, pad=""):
    manager.begin_context(context_id, "input")
    for j in range(entries):
        tick["value"] += 1
        manager.add_entry(
            modality="word", section="listen",
            motif_id=chi * 100 + j, chi=chi, tick=tick["value"],
            source_tag=f"w{j}", context_id=context_id, source="joe",
            episode_ref=f"episode:{context_id}", salience=1.0,
            dwell_ticks=2, note=pad,
        )
    return manager.end_context(context_id, "done")


def _wal_dir(state_dir):
    return os.path.join(state_dir, WAL_DIRNAME)


def _populate(manager, tick, n, *, pad=""):
    """Close n windows through the real path; return {window_id: chi}."""
    ids = {}
    for i in range(n):
        chi = 1000 + (i % 13)
        wid = _close_window(manager, tick, f"ctx{i}", chi=chi,
                            entries=1 + (i % 2), pad=pad)
        ids[wid] = chi
    return ids


# ── (b) fetch-on-demand correctness against an oracle ───────────────────────

def test_all_read_surfaces_serve_identical_content_from_disk(tmp_path):
    state = str(tmp_path)
    src, tick, _ = _build()
    src.configure_wal_under(state)
    ids = _populate(src, tick, 60)
    manifest = src.snapshot_incremental()
    oracle = src.snapshot()["windows"]  # materialized reference

    # A fresh manager boots purely from the index scan (no content).
    booted, _, _ = _build()
    booted.restore_from_wal(manifest, _wal_dir(state))

    # closed_window per id.
    for wid, record in oracle.items():
        assert booted.closed_window(wid) == record
    # legacy windows mapping surface.
    assert set(booted.windows) == set(oracle)
    assert len(booted.windows) == len(oracle)
    for wid in oracle:
        assert wid in booted.windows
        assert booted.windows[wid] == oracle[wid]
    # lookup_chi + recall_snapshot parity with the source manager.
    for chi in sorted(set(ids.values())):
        assert booted.lookup_chi(chi) == src.lookup_chi(chi)
    all_chis = sorted(set(ids.values()))
    assert booted.recall_snapshot(all_chis) == src.recall_snapshot(all_chis)
    # unknown id: honest miss.
    assert booted.closed_window("win_does_not_exist") is None


def test_boot_scan_materializes_no_content(tmp_path):
    state = str(tmp_path)
    src, tick, _ = _build()
    src.configure_wal_under(state)
    _populate(src, tick, 40, pad="x" * 2000)
    manifest = src.snapshot_incremental()

    booted, _, _ = _build()
    booted.restore_from_wal(manifest, _wal_dir(state))
    # Index + locator + metadata exist; content does not.
    assert booted.closed_window_count() == 40
    assert len(booted._window_locator) == 40
    assert len(booted._window_meta) == 40
    assert booted._pending == {}
    assert booted.cache_stats()["entries"] == 0
    assert booted.cache_stats()["bytes"] == 0
    # First real read faults content in.
    wid = next(iter(booted.windows))
    assert booted.windows[wid]["window_id"] == wid
    assert booted.cache_stats()["entries"] == 1


def test_scan_metadata_matches_records(tmp_path):
    state = str(tmp_path)
    src, tick, _ = _build()
    src.configure_wal_under(state)
    src.begin_context("meta_ctx", "input",
                      context_detail={"experience_origin": "emulated"})
    tick["value"] += 1
    src.add_entry(modality="word", section="listen", motif_id=1, chi=77,
                  tick=tick["value"], source_tag="hello",
                  context_id="meta_ctx")
    tick["value"] += 1
    src.add_entry(modality="sight", section="sight", motif_id=2, chi=78,
                  tick=tick["value"], source_tag="pic",
                  context_id="meta_ctx")
    wid = src.end_context("meta_ctx", "context_complete")
    manifest = src.snapshot_incremental()

    booted, _, _ = _build()
    booted.restore_from_wal(manifest, _wal_dir(state))
    meta = booted.window_metadata(wid)
    assert meta["close_reason"] == "context_complete"
    assert meta["experience_origin"] == "emulated"
    assert meta["modalities"] == ("word", "sight")
    # P1: a COUNT, never the resident word list (review 2026-07-16).
    assert meta["word_count"] == 1
    assert "words" not in meta
    assert meta["entry_count"] == 2
    assert meta["content_released"] is False
    assert meta["reinforcement_count"] == 1
    assert isinstance(meta["affect_snapshot"], dict)
    assert meta["last_fetched_tick"] is None
    # Fetch recency is recorded (fade-policy input).
    booted.closed_window(wid)
    assert booted.window_metadata(wid)["last_fetched_tick"] is not None


def test_detached_copies_cannot_corrupt_canonical_memory(tmp_path):
    state = str(tmp_path)
    manager, tick, _ = _build()
    manager.configure_wal_under(state)
    wid = _close_window(manager, tick, "detach", chi=500, entries=2)

    frozen = manager.closed_window(wid)
    reference = json.loads(json.dumps(frozen))

    # Vandalize every surface's returned copy.
    got = manager.closed_window(wid)
    got["entries"].clear()
    got["close_reason"] = "vandalized"
    via_mapping = manager.windows[wid]
    via_mapping["entries"].append({"fake": True})
    via_chi = manager.lookup_chi(500)[0]
    via_chi["window_id"] = "win_corrupted"
    via_recall = manager.recall_snapshot([500])[0]
    via_recall["entries"][0]["provenance"]["source"] = "attacker"

    assert manager.closed_window(wid) == reference
    assert manager.windows[wid] == reference
    assert manager.lookup_chi(500)[0] == reference
    assert manager.recall_snapshot([500])[0] == reference


# ── (b) LRU cache: budget, eviction, correctness after eviction ─────────────
# The budget accounts ESTIMATED RESIDENT bytes: each cached record costs
# serialized_length x CACHE_RESIDENT_MULTIPLIER (parsed dicts occupy ~5x
# their canonical JSON; review 2026-07-16).  A ~4KB padded record therefore
# costs ~22KB of budget.

def test_lru_cache_respects_byte_budget_and_still_serves(tmp_path):
    state = str(tmp_path)
    # ~64KB budget; each padded record costs ~22KB accounted, so ~2-3 fit.
    manager, tick, _ = _build(cache_mb=0.0625)
    manager.configure_wal_under(state)
    ids = list(_populate(manager, tick, 50, pad="y" * 4000))
    budget = manager.cache_stats()["budget_bytes"]
    assert budget == int(0.0625 * 1024 * 1024)

    for wid in ids:  # touch everything
        assert manager.closed_window(wid)["window_id"] == wid
    stats = manager.cache_stats()
    assert stats["bytes"] <= budget
    assert 0 < stats["entries"] < 50  # eviction actually happened

    # Every window — cached or evicted — still reads back identically.
    reference = {wid: manager.closed_window(wid) for wid in ids}
    for wid in ids:
        assert manager.closed_window(wid) == reference[wid]


def test_lru_evicts_least_recently_used_first(tmp_path):
    state = str(tmp_path)
    # ~100KB budget / ~22KB accounted cost each: fits ~4 padded records.
    manager, tick, _ = _build(cache_mb=0.1)
    manager.configure_wal_under(state)
    ids = list(_populate(manager, tick, 8, pad="z" * 4000))

    for wid in ids:
        manager.closed_window(wid)
    with manager._cache_lock:
        cached_order = list(manager._content_cache)
    # The most recently fetched ids are the ones retained.
    assert cached_order == ids[-len(cached_order):]

    # Re-touch the oldest retained id, then fetch one more evicted id:
    # the re-touched one must survive over the untouched next-oldest.
    survivor = cached_order[0]
    manager.closed_window(survivor)
    evicted_target = ids[0]
    manager.closed_window(evicted_target)
    with manager._cache_lock:
        assert survivor in manager._content_cache


def test_oversized_record_is_served_without_caching(tmp_path):
    state = str(tmp_path)
    manager, tick, _ = _build(cache_mb=0.001)  # ~1KB budget
    manager.configure_wal_under(state)
    wid = _close_window(manager, tick, "big", chi=9, pad="w" * 8000)
    record = manager.closed_window(wid)
    assert record["window_id"] == wid
    assert manager.cache_stats()["entries"] == 0  # bigger than whole budget


# ── (c) locator validity after compaction ────────────────────────────────────

def test_locator_rebuilds_on_compaction_and_content_survives(tmp_path):
    state = str(tmp_path)
    manager, tick, _ = _build()
    manager.configure_wal_under(state)
    ids = list(_populate(manager, tick, 30))
    reference = {wid: manager.closed_window(wid) for wid in ids}
    old_locations = dict(manager._window_locator)

    result = manager.compact()
    assert result["records"] == 30

    new_locations = dict(manager._window_locator)
    assert set(new_locations) == set(old_locations)
    # Compaction rewrote segment files: every locator entry moved.
    assert all(new_locations[wid].path != old_locations[wid].path
               for wid in ids)
    assert all(new_locations[wid].path == result["path"] for wid in ids)
    # And every window still reads back identically from the new files.
    manager._cache_clear()
    for wid in ids:
        assert manager.closed_window(wid) == reference[wid]
    # Post-compact closes keep working and land in the new generation.
    late = _close_window(manager, tick, "late", chi=4242)
    assert manager.closed_window(late)["window_id"] == late

    # A reboot from the post-compact manifest sees the same store.
    manifest = manager.snapshot_incremental()
    booted, _, _ = _build()
    booted.restore_from_wal(manifest, _wal_dir(state))
    for wid in ids:
        assert booted.closed_window(wid) == reference[wid]
    assert booted.closed_window(late) is not None


def test_pending_windows_fold_into_base_on_first_save(tmp_path):
    state = str(tmp_path)
    manager, tick, _ = _build()
    # Closes BEFORE the WAL is configured park in _pending (readable).
    ids = list(_populate(manager, tick, 5))
    assert set(manager._pending) == set(ids)
    for wid in ids:
        assert manager.closed_window(wid)["window_id"] == wid

    manager.configure_wal_under(state)
    manifest = manager.snapshot_incremental()  # divergence -> fold-into-base
    assert manifest["wal_durable_count"] == 5
    assert manager._pending == {}
    assert set(manager._window_locator) == set(ids)
    for wid in ids:
        assert manager.closed_window(wid)["window_id"] == wid


# ── P4: corruption at fetch is a NAMED loud halt, never a silent miss ───────

def test_corrupted_located_record_halts_loudly(tmp_path):
    state = str(tmp_path)
    manager, tick, _ = _build()
    manager.configure_wal_under(state)
    wid = _close_window(manager, tick, "corrupt_me", chi=321)
    location = manager._window_locator[wid]
    manager._cache_clear()

    with open(location.path, "r+b") as handle:
        handle.seek(location.offset + 20)
        handle.write(b"XXXX")

    with pytest.raises(WindowStoreIntegrityHalt):
        manager.closed_window(wid)
    with pytest.raises(WindowStoreIntegrityHalt):
        manager.lookup_chi(321)
