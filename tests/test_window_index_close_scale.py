"""Closing a giant window must not stall the substrate (O(n^2) index scan).

Measured live 2026-07-15: one attending_audio episode close ran 5+ minutes
inside WindowManager._lock because _index_closed_window deduped with a
``location not in bucket`` list scan — O(entries x bucket).  The engine tick
loop, hot saves, autonomy, and conversation all queued behind it ("substrate
busy" on every turn).  The fix keeps a persistent per-chi seen-set (the same
dedup the WAL replay already used), making one close O(its own entries).
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dsf_ai_service.substrate.window_manager import WindowManager

TICK = [0]


def _manager(tmp_path):
    manager = WindowManager(
        atlas_record_fn=lambda *a, **kw: None,
        log_event_fn=lambda *a, **kw: None,
        get_tick_fn=lambda: TICK[0],
        atlas_windows={},
    )
    manager.configure_wal_under(str(tmp_path))
    return manager


def _seed_index_synthetically(manager, n_windows, entries_per_window, n_chis):
    """Grow the chi index to production density through the real index path."""
    for w in range(n_windows):
        record = {
            "window_id": f"win_{w:016x}_seedseedseedseed",
            "entries": [
                {"chi": i % n_chis, "entry_index": i}
                for i in range(entries_per_window)
            ],
        }
        with manager._lock:
            manager._index_closed_window(record)


def _close_real_window(manager, context_id, n_entries, n_chis):
    manager.begin_context(context_id, trigger_reason="sound",
                          context_detail={"experience_origin": "lived"})
    for i in range(n_entries):
        TICK[0] += 1
        manager.add_entry(
            modality="sound", section=f"audio_band_{i % 30}",
            motif_id=7, chi=(i % n_chis), tick=TICK[0],
            source_tag="attending_audio", trigger_reason="sound",
            context_id=context_id, salience=1.2, dwell_ticks=8,
        )
    start = time.monotonic()
    window_id = manager.end_context(context_id, "activity_ended")
    return window_id, time.monotonic() - start


def _oracle_index(records):
    """The old algorithm's OUTPUT (order-preserving first-occurrence dedup)."""
    index = {}
    for record in records:
        for entry in record.get("entries") or []:
            chi = int(entry["chi"])
            location = {"window_id": record["window_id"],
                        "entry_index": int(entry["entry_index"])}
            bucket = index.setdefault(chi, [])
            if location not in bucket:
                bucket.append(location)
    return index


def test_index_parity_with_old_algorithm(tmp_path):
    manager = _manager(tmp_path)
    ids = []
    for k in range(4):
        wid, _ = _close_real_window(manager, f"ctx:{k}", 40, 7)
        ids.append(wid)
    records = [manager.windows[w] for w in ids]
    assert manager.chi_index == _oracle_index(records)
    # And recall still routes through it.
    assert len(manager.lookup_chi(3)) > 0


def test_giant_window_close_is_not_quadratic(tmp_path):
    manager = _manager(tmp_path)
    # Production density: ~100k indexed entries concentrated in few chi
    # buckets (live state has ~950k across ~100 buckets; the old scan at THIS
    # reduced scale already costs tens of seconds, the fix well under one).
    _seed_index_synthetically(
        manager, n_windows=10, entries_per_window=10_000, n_chis=10)
    _, close_seconds = _close_real_window(manager, "ctx:giant", 5_000, 10)
    assert close_seconds < 5.0, (
        f"giant-window close took {close_seconds:.1f}s — the O(n^2) index "
        f"scan is back and will stall the whole substrate under _lock")
    # Dedup companion stayed consistent with the index it guards.
    total_indexed = sum(len(b) for b in manager._chi_index.values())
    total_seen = sum(len(s) for s in manager._chi_index_seen.values())
    assert total_indexed == total_seen


def test_seen_companion_survives_wal_restore(tmp_path):
    manager = _manager(tmp_path)
    _close_real_window(manager, "ctx:a", 60, 5)
    manifest = manager.snapshot_incremental()

    restored = _manager(tmp_path)
    restored.restore_persisted(manifest, str(tmp_path))
    assert restored.chi_index == manager.chi_index
    total_indexed = sum(len(b) for b in restored._chi_index.values())
    total_seen = sum(len(s) for s in restored._chi_index_seen.values())
    assert total_indexed == total_seen
    # A post-restore close keeps using the O(1) path correctly.
    wid, close_seconds = _close_real_window(restored, "ctx:b", 60, 5)
    assert wid in restored.windows
    assert close_seconds < 5.0
