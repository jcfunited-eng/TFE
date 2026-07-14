"""Real, non-monkeypatched contracts for incremental (WAL) binding-window
persistence.

These exercise the actual WindowManager API end to end -- windows are opened,
entries added, and contexts closed through the real begin_context/add_entry/
end_context path; the WAL segments are the real files on disk; restore reads
those real files.  The central proof (test_full_round_trip_matches_legacy) is
that a WAL restore reconstructs byte-for-byte the same state the old
snapshot()/restore() round-trip produced for the same data.
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dsf_ai_service.substrate.window_manager import (  # noqa: E402
    WAL_DIRNAME,
    MANIFEST_FORMAT,
    WindowIntegrityError,
    WindowManager,
    _canonical_wal_bytes,
    _sha256_hex,
)


def _build(tmpdir=None, tick_value=0):
    tick = {"value": tick_value}
    events = []
    mirror = {}
    atlas_calls = []

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
    return manager, tick, events


def _build2():
    """Same as _build but returns (manager, events, tick) for assertions."""
    manager, tick, events = _build()
    return manager, events, tick


def _close_window(manager, tick, context_id, *, chi, entries=1, modality="word"):
    """Open a context, add ``entries`` word entries, close it -- real path."""
    manager.begin_context(context_id, "input")
    for j in range(entries):
        tick["value"] += 1
        manager.add_entry(
            modality=modality, section="listen",
            motif_id=chi * 100 + j, chi=chi, tick=tick["value"],
            source_tag="word", context_id=context_id, source="joe",
            episode_ref=f"episode:{context_id}", salience=1.0, dwell_ticks=2,
        )
    return manager.end_context(context_id, "done")


def _wal_dir(state_dir):
    return os.path.join(state_dir, WAL_DIRNAME)


def _count_wal_records(state_dir):
    """Count valid+partial newline-delimited records across all segments."""
    wal = _wal_dir(state_dir)
    total = 0
    for name in sorted(os.listdir(wal)):
        if not name.startswith("seg-") or not name.endswith(".jsonl"):
            continue
        with open(os.path.join(wal, name), "rb") as handle:
            content = handle.read()
        if not content:
            continue
        lines = content.split(b"\n")
        if content.endswith(b"\n"):
            lines = lines[:-1]
        total += len([line for line in lines if line])
    return total


# ── (a) Incremental append: new records only, old ones already durable ──────

def test_incremental_append_only_new_records(tmp_path):
    state = str(tmp_path)
    manager, tick, _ = _build()
    manager.configure_wal_under(state)

    n = 40
    for i in range(n):
        _close_window(manager, tick, f"ctx{i}", chi=1000 + i)

    manifest = manager.snapshot_incremental()
    assert manifest["format"] == MANIFEST_FORMAT
    assert manifest["wal_durable_count"] == n
    assert manifest["closed_window_count"] == n
    assert manifest["open_contexts"] == {}
    # Exactly n records physically on disk -- nothing re-written.
    assert _count_wal_records(state) == n

    # One more close appends exactly one record; the prior n are untouched.
    records_before = _count_wal_records(state)
    _close_window(manager, tick, "ctx_extra", chi=9999)
    records_after = _count_wal_records(state)
    assert records_after == records_before + 1

    manifest2 = manager.snapshot_incremental()
    assert manifest2["wal_durable_count"] == n + 1
    # The manifest is a real save payload: it must be strict-JSON encodable.
    json.dumps(manifest2, allow_nan=False)


# ── (b) THE correctness proof: WAL restore == legacy snapshot/restore ───────

@pytest.mark.parametrize("n_closed", [300, 1200])
def test_full_round_trip_matches_legacy(tmp_path, n_closed):
    state = str(tmp_path)
    src, tick, _ = _build()
    src.configure_wal_under(state)

    # A realistic mix: many closed windows (varied chi, some sharing a bucket,
    # multi-entry) plus a couple of still-open contexts.
    for i in range(n_closed):
        _close_window(src, tick, f"c{i}", chi=100 + (i % 37), entries=1 + (i % 3))
    # Leave two open contexts with entries in flight.
    for oc in ("open_a", "open_b"):
        src.begin_context(oc, "input")
        tick["value"] += 1
        src.add_entry(modality="word", section="listen", motif_id=7, chi=500,
                      tick=tick["value"], source_tag="word", context_id=oc,
                      source="joe", salience=0.5, dwell_ticks=1)

    # Reference: the exact state the OLD full snapshot captures.
    old_snapshot = src.snapshot()
    # New save payload (manifest) for the SAME state.
    manifest = src.snapshot_incremental()

    # Sanity: the legacy round-trip reproduces the reference exactly.
    legacy_target, _, _ = _build()
    legacy_target.restore(old_snapshot)
    assert legacy_target.snapshot() == old_snapshot

    # The real proof: restore purely from the WAL files on disk + manifest.
    restored, _, _ = _build()
    restored.restore_from_wal(manifest, _wal_dir(state))
    new_snapshot = restored.snapshot()

    assert new_snapshot["windows"] == old_snapshot["windows"]
    assert new_snapshot["chi_index"] == old_snapshot["chi_index"]
    assert new_snapshot["open_contexts"] == old_snapshot["open_contexts"]
    assert (new_snapshot["next_window_sequence"]
            == old_snapshot["next_window_sequence"])
    assert (new_snapshot["next_context_sequence"]
            == old_snapshot["next_context_sequence"])
    # Whole-structure identity.
    assert new_snapshot == old_snapshot

    # And recall behaves identically over a shared chi bucket.
    for chi in (100, 118, 136):
        assert restored.recall_snapshot([chi]) == src.recall_snapshot([chi])


# ── (c) Migration: legacy full snapshot -> WAL base -> WAL restore ──────────

def test_migration_from_legacy_full_snapshot(tmp_path):
    state = str(tmp_path)
    # Produce a genuine OLD-format full snapshot from a separate manager.
    legacy_src, tick, _ = _build()
    for i in range(150):
        _close_window(legacy_src, tick, f"L{i}", chi=200 + (i % 11))
    legacy_snapshot = legacy_src.snapshot()
    assert "windows" in legacy_snapshot and "format" not in legacy_snapshot

    # Boot a fresh manager that finds only the legacy snapshot (no WAL yet).
    migrated, _, _ = _build()
    migrated.restore_persisted(legacy_snapshot, state)  # dispatch -> legacy path
    assert migrated.snapshot() == legacy_snapshot
    # No WAL segments exist yet; the store is flagged for a fold-into-base.
    assert _count_wal_records(state) == 0

    # First save folds the migrated store into a real WAL base + manifest.
    manifest = migrated.snapshot_incremental()
    assert manifest["format"] == MANIFEST_FORMAT
    assert manifest["wal_durable_count"] == 150
    assert _count_wal_records(state) == 150  # base segment written for real

    # A later boot restores from the WAL, losslessly, via the dispatcher.
    rebooted, _, _ = _build()
    rebooted.restore_persisted(manifest, state)
    assert rebooted.snapshot() == legacy_snapshot


# ── (d) Crash safety: torn trailing record, recovery, interior corruption ───

def _valid_record_line(record):
    rh = _sha256_hex(_canonical_wal_bytes(record))
    return _canonical_wal_bytes({"record": record, "sha256": rh}) + b"\n"


def _active_segment_path(state_dir):
    wal = _wal_dir(state_dir)
    segs = sorted(n for n in os.listdir(wal)
                  if n.startswith("seg-") and n.endswith(".jsonl"))
    return os.path.join(wal, segs[-1])


def test_torn_trailing_record_is_discarded(tmp_path):
    state = str(tmp_path)
    manager, tick, _ = _build()
    manager.configure_wal_under(state)
    n = 25
    for i in range(n):
        _close_window(manager, tick, f"t{i}", chi=300 + i)
    manifest = manager.snapshot_incremental()
    assert manifest["wal_durable_count"] == n

    # Simulate a crash mid-append: a truncated JSON fragment, no newline.
    with open(_active_segment_path(state), "ab") as handle:
        handle.write(b'{"record": {"window_id": "win_partial')  # torn

    restored, restored_events, _ = _build2()
    restored.restore_from_wal(manifest, _wal_dir(state))
    assert len(restored.snapshot()["windows"]) == n  # torn record dropped
    torn = [d for k, d in restored_events if k == "window_state_restored_wal"]
    assert torn and torn[0]["torn_discarded"] == 1 and torn[0]["recovered"] == 0


def test_post_manifest_record_is_recovered(tmp_path):
    state = str(tmp_path)
    manager, tick, _ = _build()
    manager.configure_wal_under(state)
    n = 25
    for i in range(n):
        _close_window(manager, tick, f"r{i}", chi=400 + i)
    manifest = manager.snapshot_incremental()  # durable_count == n

    # A window closes AFTER the manifest was written but before a crash: it is
    # durably appended to the WAL and must be recovered (less loss than the
    # old full-save-only model).
    _close_window(manager, tick, "r_late", chi=4999)

    restored, restored_events, _ = _build2()
    restored.restore_from_wal(manifest, _wal_dir(state))
    assert len(restored.snapshot()["windows"]) == n + 1
    info = [d for k, d in restored_events if k == "window_state_restored_wal"][0]
    assert info["durable_count"] == n and info["recovered"] == 1


def test_interior_corruption_is_rejected(tmp_path):
    state = str(tmp_path)
    manager, tick, _ = _build()
    manager.configure_wal_under(state)
    for i in range(10):
        _close_window(manager, tick, f"i{i}", chi=600 + i)
    manifest = manager.snapshot_incremental()

    # Corrupt an interior (non-trailing) record: flip its stored hash, then
    # append a valid trailing record so the corruption is NOT the last line.
    seg = _active_segment_path(state)
    with open(seg, "rb") as handle:
        lines = handle.read().split(b"\n")
    # lines[-1] is "" (trailing newline). Corrupt the first real record.
    bad = json.loads(lines[0])
    bad["sha256"] = "0" * 64
    lines[0] = json.dumps(bad).encode()
    with open(seg, "wb") as handle:
        handle.write(b"\n".join(lines))

    restored, _, _ = _build2()
    with pytest.raises(WindowIntegrityError):
        restored.restore_from_wal(manifest, _wal_dir(state))


def test_digest_mismatch_is_rejected(tmp_path):
    """A durable record silently swapped for other valid bytes is caught by the
    manifest's cumulative digest (the generation-binding guarantee)."""
    state = str(tmp_path)
    manager, tick, _ = _build()
    manager.configure_wal_under(state)
    for i in range(8):
        _close_window(manager, tick, f"d{i}", chi=700 + i)
    manifest = manager.snapshot_incremental()
    manifest = dict(manifest)
    manifest["wal_digest"] = "f" * 64  # wrong digest
    restored, _, _ = _build2()
    with pytest.raises(WindowIntegrityError):
        restored.restore_from_wal(manifest, _wal_dir(state))


# ── (e) Timing: incremental save is proportional to new records, not history ─

def test_incremental_save_is_fast_against_large_history(tmp_path):
    state = str(tmp_path)
    manager, tick, _ = _build()
    # Build a large durable history efficiently: close windows with the WAL not
    # yet configured (no per-record fsync), each with a unique chi so indexing
    # stays O(1), then fold the whole store into one base with compact().
    n = 50_000
    for i in range(n):
        _close_window(manager, tick, f"h{i}", chi=i)  # unique chi per window
    manager.configure_wal_under(state)
    manager.compact()  # one-time cold fold -> durable base of 50k records

    # Old full-snapshot cost (O(history): deepcopy + revalidate + serialise).
    t0 = time.perf_counter()
    old = manager.snapshot()
    t_old = time.perf_counter() - t0
    assert len(old["windows"]) == n

    # A few genuinely new closures (durably appended).
    for i in range(5):
        _close_window(manager, tick, f"new{i}", chi=10_000_000 + i)

    # New incremental save cost (should be ~O(open contexts), not O(history)).
    t1 = time.perf_counter()
    manifest = manager.snapshot_incremental()
    t_new = time.perf_counter() - t1
    assert manifest["wal_durable_count"] == n + 5

    # The whole point: incremental is dramatically cheaper than the full path.
    print(f"\n[wal-timing] history={n} full_snapshot={t_old*1000:.1f}ms "
          f"incremental_save={t_new*1000:.1f}ms speedup={t_old/max(t_new,1e-9):.0f}x")
    assert t_new < t_old / 10.0
    assert t_new < 0.05  # absolute: a manifest save is a few ms, not seconds

    # And it is still a correct, restorable generation.
    restored, _, _ = _build2()
    restored.restore_from_wal(manifest, _wal_dir(state))
    assert len(restored.snapshot()["windows"]) == n + 5
