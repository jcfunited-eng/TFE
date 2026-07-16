"""Torn WAL tail must self-heal at boot, not brick the SECOND boot.

Review blocker 1 (2026-07-16), reproduced end-to-end: a SIGKILL mid-append
leaves a torn half-line at the tail of the active segment.  Boot 1 correctly
discarded it — but left the bytes on disk; new closes then open a FRESH
segment (by design, so they never merge with the torn tail), which makes the
torn line an INTERIOR corruption for boot 2: a permanent named halt for what
was one crash mid-append.  (The old unconditional cold-lane compact used to
accidentally rewrite it away; Change 1 removed that.)

Fix under test: restore_from_wal truncates the discarded torn bytes off the
segment (they were never counted durable — counters/digest only advance
after fsync — so the manifest is untouched) and emits a loud
``window_wal_torn_truncated`` event.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dsf_ai_service.substrate.window_manager import (  # noqa: E402
    WAL_DIRNAME,
    WindowManager,
)


def _build():
    tick = {"value": 0}
    events = []
    manager = WindowManager(
        atlas_record_fn=lambda *a, **kw: None,
        log_event_fn=lambda kind, **detail: events.append((kind, detail)),
        get_tick_fn=lambda: tick["value"],
        atlas_windows={},
    )
    return manager, tick, events


def _close_window(manager, tick, context_id, *, chi):
    manager.begin_context(context_id, "input")
    tick["value"] += 1
    manager.add_entry(
        modality="word", section="listen", motif_id=chi, chi=chi,
        tick=tick["value"], source_tag="w", context_id=context_id,
        source="joe", episode_ref=f"episode:{context_id}")
    return manager.end_context(context_id, "done")


def _wal_dir(state_dir):
    return os.path.join(state_dir, WAL_DIRNAME)


def _last_segment(state_dir):
    wal = _wal_dir(state_dir)
    segs = sorted(n for n in os.listdir(wal)
                  if n.startswith("seg-") and n.endswith(".jsonl"))
    return os.path.join(wal, segs[-1])


TORN_BYTES = b'{"record": {"window_id": "win_sigkill_mid_append'


def test_two_boots_across_a_torn_tail(tmp_path):
    state = str(tmp_path)

    # Live process: closes windows, saves a manifest, then dies mid-append.
    manager, tick, _ = _build()
    manager.configure_wal_under(state)
    n = 12
    for i in range(n):
        _close_window(manager, tick, f"c{i}", chi=700 + i)
    manifest = manager.snapshot_incremental()
    seg = _last_segment(state)
    clean_size = os.path.getsize(seg)
    with open(seg, "ab") as handle:
        handle.write(TORN_BYTES)  # SIGKILL: no newline, no fsync accounting

    # BOOT 1: torn record discarded AND truncated off, loudly.
    boot1, _, events1 = _build()
    boot1.restore_from_wal(manifest, _wal_dir(state))
    assert boot1.closed_window_count() == n
    restored = [d for k, d in events1 if k == "window_state_restored_wal"]
    assert restored and restored[0]["torn_discarded"] == 1
    truncated = [d for k, d in events1 if k == "window_wal_torn_truncated"]
    assert truncated and truncated[0]["bytes_removed"] == len(TORN_BYTES)
    assert os.path.getsize(seg) == clean_size  # bytes really gone

    # Life goes on: a new close lands in a FRESH segment (unchanged design),
    # making the healed segment an interior one for the next boot.
    late = _close_window(boot1, tick, "late", chi=9999)
    manifest2 = boot1.snapshot_incremental()
    assert manifest2["wal_durable_count"] == n + 1

    # BOOT 2: the reviewer's bricking scenario — must now succeed.
    boot2, _, events2 = _build()
    boot2.restore_from_wal(manifest2, _wal_dir(state))
    assert boot2.closed_window_count() == n + 1
    assert boot2.closed_window(late) is not None
    # And nothing was torn this time.
    restored2 = [d for k, d in events2 if k == "window_state_restored_wal"]
    assert restored2 and restored2[0]["torn_discarded"] == 0


def test_torn_tail_truncation_preserves_every_durable_record(tmp_path):
    state = str(tmp_path)
    manager, tick, _ = _build()
    manager.configure_wal_under(state)
    ids = [_close_window(manager, tick, f"k{i}", chi=800 + i)
           for i in range(6)]
    manifest = manager.snapshot_incremental()
    reference = {wid: manager.closed_window(wid) for wid in ids}
    with open(_last_segment(state), "ab") as handle:
        handle.write(b"\x00\x01torn")

    booted, _, _ = _build()
    booted.restore_from_wal(manifest, _wal_dir(state))
    for wid in ids:
        assert booted.closed_window(wid) == reference[wid]
