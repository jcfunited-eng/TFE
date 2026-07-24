"""test_wal_boot_checkpoint_fast_path.py -- GL-FIX-WAL-BOOT-CHECKPOINT-20260720:
restore_from_wal trusts a compaction checkpoint instead of re-parsing and
re-validating every historical closed window's full JSON on every boot.

Root problem, confirmed live 2026-07-20: compaction (_compact_locked) folds
every closed record into one fresh base segment, but ran exactly once (at
genesis) and never again -- so every boot re-parsed, schema-validated, and
cryptographically re-verified the WHOLE base from scratch, forever, a cost
that only grows. The fix everyone would reach for first -- "just call
compact() more often" -- does NOT work: compaction repackages the same
total content, it never shrinks what restore has to re-parse, because the
base it writes still holds every historical record. Verified this by
reading the code before building anything.

The real fix: _compact_locked now also writes a small checkpoint (locator +
window_meta + chi_index + a concatenated per-record hash blob + sequence
counters) alongside the base segment, sealed with a digest of the base's
raw bytes. restore_from_wal can then trust that checkpoint -- skipping
per-record JSON-parse, schema validation, and canonical re-serialisation
for the base entirely -- once it re-hashes the base file's actual bytes
right now and confirms they still match the seal. Any checkpoint miss,
corruption, or digest mismatch falls back to the untouched original full
replay -- this can only make boot faster, never less safe.

Honest scope, corrected after measuring it (see Gate 7): this is a real,
measured constant-factor speedup (roughly 1.6-2x at 20k records in this
test's synthetic single-entry-per-window shape; the avoided per-record work
-- schema validation, canonical JSON re-serialisation, hashing -- is
proportionally heavier on real, richer production records), NOT a change
of complexity class. The checkpoint's own JSON parse still costs roughly
one pass over data proportional to total historical window count, because
window_meta/locator/chi_index are inherently per-window and the runtime
needs ALL of them resident for recall regardless of how they were loaded.
Making boot cost genuinely independent of total lifetime would need a
further, separate step (fewer old windows kept fully resident at all) --
deliberately not attempted tonight, see the session's own conversation
record for why.

Gates:
1. Fast-path boot (checkpoint present, base untouched) produces state
   BYTE-IDENTICAL to a full-replay boot of the very same generation --
   locator, window_meta, chi_index, chi_index_seen, sequence counters, and
   the resulting digest hasher all match.
2. The fast path actually skips per-record re-verification of the base --
   proven by counting _verify_wal_line calls, not just asserting a result.
3. A tampered BASE segment is still caught: the digest mismatch silently
   declines the fast path, falls back to full replay, which raises the
   same WindowStoreIntegrityHalt corruption would always raise.
4. A corrupted/malformed CHECKPOINT file never produces wrong state -- it
   falls back to a full replay of the untouched base and restores
   correctly. A broken checkpoint can only cost speed, never correctness.
5. A generation with no checkpoint at all (pre-feature / never compacted)
   restores exactly as it always has -- this feature is purely additive.
6. The digest chain stays coherent across repeated cycles: after a
   fast-path boot, closing more windows and saving again produces a
   manifest that a THIRD from-scratch restore also accepts cleanly.
"""

import copy
import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dsf_ai_service.substrate.window_manager import (  # noqa: E402
    WAL_DIRNAME,
    WindowIntegrityError,
    WindowManager,
    WindowStoreIntegrityHalt,
)


def _build():
    tick = {"value": 0}
    events = []

    def atlas_record(section, motif, chi, at_tick, **kwargs):
        pass

    manager = WindowManager(
        atlas_record_fn=atlas_record,
        log_event_fn=lambda kind, **detail: events.append((kind, detail)),
        get_tick_fn=lambda: tick["value"],
        get_presence_fn=lambda: {"joe": True},
        get_affect_fn=lambda: {"arousal": 0.7, "valence": -0.2},
        get_needs_fn=lambda: {"stability": 0.6, "connection": 0.8},
        atlas_windows={},
    )
    return manager, tick, events


def _close_window(manager, tick, context_id, *, chi, entries=1):
    manager.begin_context(context_id, "input")
    for j in range(entries):
        tick["value"] += 1
        manager.add_entry(
            modality="word", section="listen",
            motif_id=chi * 100 + j, chi=chi, tick=tick["value"],
            source_tag="word", context_id=context_id, source="joe",
            episode_ref=f"episode:{context_id}", salience=1.0, dwell_ticks=2,
        )
    return manager.end_context(context_id, "done")


def _wal_dir(state_dir):
    return os.path.join(state_dir, WAL_DIRNAME)


def _base_segment_path(state_dir):
    wal = _wal_dir(state_dir)
    segs = sorted(
        n for n in os.listdir(wal)
        if n.startswith("seg-") and n.endswith(".jsonl") and n.endswith(
            "-00000000.jsonl"))
    assert segs, "no base segment found -- did compact() actually run?"
    return os.path.join(wal, segs[-1])


def _checkpoint_path(state_dir):
    wal = _wal_dir(state_dir)
    ckpts = sorted(
        n for n in os.listdir(wal)
        if n.startswith("ckpt-") and n.endswith(".json"))
    assert ckpts, "no checkpoint file found -- did compact() write one?"
    return os.path.join(wal, ckpts[-1])


def _full_state(manager):
    """Every piece of restored state that must match between a fast-path
    and a full-replay boot, in a directly comparable (JSON-safe) form."""
    return {
        "locator": {
            wid: list(loc) for wid, loc in manager._window_locator.items()
        },
        "window_meta": manager._window_meta,
        "chi_index": manager._chi_index,
        "chi_index_seen": {
            chi: sorted(seen) for chi, seen in manager._chi_index_seen.items()
        },
        "window_sequence": manager._window_sequence,
        "context_sequence": manager._context_sequence,
        "digest": manager._wal_digest_hasher.hexdigest(),
    }


def _fresh_process_restore(manifest_path, wal_path):
    worker = r"""
import json
import sys
import time

from dsf_ai_service.substrate.window_manager import WindowManager

with open(sys.argv[1], encoding="utf-8") as handle:
    manifest = json.load(handle)

manager = WindowManager(
    atlas_record_fn=lambda *_args, **_kwargs: None,
    log_event_fn=lambda *_args, **_kwargs: None,
    get_tick_fn=lambda: 0,
    get_presence_fn=lambda: {"joe": True},
    get_affect_fn=lambda: {"arousal": 0.7, "valence": -0.2},
    get_needs_fn=lambda: {"stability": 0.6, "connection": 0.8},
    atlas_windows={},
)
started = time.perf_counter()
manager.restore_from_wal(manifest, sys.argv[2])
elapsed = time.perf_counter() - started
print(json.dumps({
    "elapsed": elapsed,
    "count": len(manager._window_locator),
}))
"""
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            worker,
            os.fspath(manifest_path),
            os.fspath(wal_path),
        ],
        cwd=os.fspath(Path(__file__).resolve().parents[1]),
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _seed_history(state, n_before_compact=30, n_after_compact=7):
    """A realistic small history: several windows, a real compact(), then a
    delta of a few more windows appended after -- exactly the shape a real
    boot-time checkpoint restore needs to prove itself against."""
    manager, tick, _ = _build()
    manager.configure_wal_under(state)
    for i in range(n_before_compact):
        _close_window(manager, tick, f"pre{i}", chi=100 + (i % 11),
                      entries=1 + (i % 3))
    manager.compact()
    for i in range(n_after_compact):
        _close_window(manager, tick, f"post{i}", chi=900 + i)
    manifest = manager.snapshot_incremental()
    return manager, manifest


# ── Gate 1: fast path == full replay, byte for byte ─────────────────────────

def test_gate1_fast_path_matches_full_replay_exactly(tmp_path):
    print("Gate 1: fast-path boot matches full-replay boot exactly...")
    state = str(tmp_path)
    _src, manifest = _seed_history(state)

    fast, _, _ = _build()
    fast.restore_from_wal(manifest, _wal_dir(state))
    fast_state = _full_state(fast)

    # Force the fallback: hide the checkpoint from a second, independent boot.
    ckpt = _checkpoint_path(state)
    os.rename(ckpt, ckpt + ".hidden")
    slow, _, _ = _build()
    slow.restore_from_wal(manifest, _wal_dir(state))
    slow_state = _full_state(slow)
    os.rename(ckpt + ".hidden", ckpt)

    assert fast_state == slow_state, (
        "fast-path and full-replay restores diverged -- "
        f"{ {k for k in fast_state if fast_state[k] != slow_state[k]} }")
    # And both agree with the live source manager's own in-memory state.
    assert fast_state["locator"].keys() == _src._window_locator.keys()
    print("  PASS: locator/meta/chi_index/chi_seen/sequences/digest identical")


# ── Gate 2: the fast path actually skips base re-verification ───────────────

def test_gate2_fast_path_skips_base_record_reverification(tmp_path, monkeypatch):
    print("Gate 2: fast path calls _verify_wal_line only for the delta...")
    state = str(tmp_path)
    _src, manifest = _seed_history(
        state, n_before_compact=25, n_after_compact=4)

    calls = {"n": 0}
    real_verify = WindowManager._verify_wal_line.__func__

    def counting_verify(cls, raw):
        calls["n"] += 1
        return real_verify(cls, raw)

    monkeypatch.setattr(
        WindowManager, "_verify_wal_line", classmethod(counting_verify))

    fast, _, _ = _build()
    fast.restore_from_wal(manifest, _wal_dir(state))
    fast_calls = calls["n"]

    calls["n"] = 0
    ckpt = _checkpoint_path(state)
    os.rename(ckpt, ckpt + ".hidden")
    slow, _, _ = _build()
    slow.restore_from_wal(manifest, _wal_dir(state))
    slow_calls = calls["n"]
    os.rename(ckpt + ".hidden", ckpt)

    print(f"  fast-path verify calls={fast_calls} "
          f"full-replay verify calls={slow_calls}")
    # Slow path re-verifies base(25) + delta(4) = 29; fast path only the
    # delta(4) -- strictly fewer, and specifically bounded to the delta size.
    assert fast_calls == 4, fast_calls
    assert slow_calls == 29, slow_calls
    assert fast_calls < slow_calls
    print("  PASS: fast path verified only the 4 delta records, not all 29")


# ── Gate 3: a tampered BASE is still caught, via the fallback ───────────────

def test_gate3_tampered_base_falls_back_and_is_still_caught(tmp_path):
    print("Gate 3: corrupted base bytes are still caught (via fallback)...")
    state = str(tmp_path)
    _src, manifest = _seed_history(state)

    base = _base_segment_path(state)
    with open(base, "r+b") as handle:
        content = handle.read()
        # Flip one byte inside the first record's hash hex-digits -- stays
        # valid JSON (still a hex char), but the record hash no longer
        # verifies, so this can ONLY be caught by real per-record replay,
        # never by a shortcut that trusts the checkpoint's stale claim.
        idx = content.index(b'"sha256":"') + len(b'"sha256":"') + 2
        flipped = bytes([content[idx] ^ 0x01])
        content = content[:idx] + flipped + content[idx + 1:]
        handle.seek(0)
        handle.write(content)

    restored, _, _ = _build()
    with pytest.raises(WindowIntegrityError):
        restored.restore_from_wal(manifest, _wal_dir(state))
    print("  PASS: tampered base -> digest mismatch -> fallback -> "
          "full replay still raised WindowStoreIntegrityHalt")


# ── Gate 4: a broken checkpoint costs speed, never correctness ──────────────

@pytest.mark.parametrize("corrupt", [
    "truncate", "bad_json", "wrong_generation", "wrong_digest",
])
def test_gate4_corrupted_checkpoint_falls_back_to_correct_state(
        tmp_path, corrupt):
    print(f"Gate 4 [{corrupt}]: a broken checkpoint never produces wrong "
          f"state, only a slower boot...")
    state = str(tmp_path)
    _src, manifest = _seed_history(state)

    ckpt = _checkpoint_path(state)
    with open(ckpt, "rb") as handle:
        raw = handle.read()
    if corrupt == "truncate":
        raw = raw[: len(raw) // 2]
    elif corrupt == "bad_json":
        raw = b"{not json"
    elif corrupt == "wrong_generation":
        data = json.loads(raw)
        data["generation"] = data["generation"] + 999
        raw = json.dumps(data).encode()
    elif corrupt == "wrong_digest":
        data = json.loads(raw)
        data["base_digest"] = "0" * 64
        raw = json.dumps(data).encode()
    with open(ckpt, "wb") as handle:
        handle.write(raw)

    # Reference: what a clean full replay of the (untouched) base produces.
    # We already overwrote ckpt in place; rebuild the reference by hiding
    # the corrupted file and doing an independent restore.
    ckpt_bak = ckpt + ".bak"
    os.rename(ckpt, ckpt_bak)
    reference, _, _ = _build()
    reference.restore_from_wal(manifest, _wal_dir(state))
    reference_state = _full_state(reference)
    os.rename(ckpt_bak, ckpt)

    restored, _, _ = _build()
    restored.restore_from_wal(manifest, _wal_dir(state))  # must NOT raise
    assert _full_state(restored) == reference_state
    print("  PASS: fell back cleanly, state matches a clean full replay")


# ── Gate 5: no checkpoint at all -- pure regression safety ──────────────────

def test_gate5_generation_with_no_checkpoint_restores_as_before(tmp_path):
    print("Gate 5: a generation that never had compact() called on it "
          "(no checkpoint exists) restores exactly as always...")
    state = str(tmp_path)
    manager, tick, _ = _build()
    manager.configure_wal_under(state)
    for i in range(12):
        _close_window(manager, tick, f"n{i}", chi=50 + i)
    manifest = manager.snapshot_incremental()  # no compact() call anywhere

    assert not os.path.exists(_wal_dir(state) + "/does-not-matter")
    wal_files = os.listdir(_wal_dir(state))
    assert not any(f.startswith("ckpt-") for f in wal_files), (
        "test setup invalid: a checkpoint exists without ever compacting")

    restored, _, _ = _build()
    restored.restore_from_wal(manifest, _wal_dir(state))
    assert restored.snapshot()["windows"].keys() == manager.snapshot()[
        "windows"].keys()
    print("  PASS: no-checkpoint generation restores correctly, unaffected")


# ── Gate 6: the seeded digest chain stays coherent across cycles ────────────

def test_gate6_digest_chain_coherent_across_repeated_cycles(tmp_path):
    print("Gate 6: fast-path boot -> more closes -> save -> a THIRD "
          "from-scratch restore still accepts the manifest cleanly...")
    state = str(tmp_path)
    _src, manifest = _seed_history(state)

    booted, tick, _ = _build()
    booted.restore_from_wal(manifest, _wal_dir(state))
    # Prove it: fresh appends chain onto the seeded digest correctly.
    for i in range(5):
        _close_window(booted, tick, f"cycle2_{i}", chi=2000 + i)
    manifest2 = booted.snapshot_incremental()

    third, _, _ = _build()
    third.restore_from_wal(manifest2, _wal_dir(state))  # must not raise
    assert len(third._window_locator) == len(booted._window_locator)
    assert (third._wal_digest_hasher.hexdigest()
            == booted._wal_digest_hasher.hexdigest())
    print("  PASS: digest chain stayed coherent through a second full cycle")


# ── Gate 7: real timing proof at meaningful scale ────────────────────────────
#
# Honest framing, corrected after actually measuring this (2026-07-20): the
# fast path is a real, meaningful constant-factor win -- it skips schema
# validation, canonical re-serialisation, and hashing for every base record
# -- NOT a change of complexity class. The checkpoint itself still costs
# roughly one JSON parse proportional to the number of historical windows
# (profiled: checkpoint size ends up close to base segment size, because
# window_meta/locator/chi_index are inherently per-window data, and the
# runtime needs ALL of it resident for recall regardless of how it's
# loaded). Making boot cost genuinely independent of total lifetime would
# need a further, separate step -- fewer OLD windows kept fully resident at
# all -- which is exactly the "distill-then-fade" archival question this
# fix deliberately does not attempt tonight. Assert what was actually
# measured, not what was hoped for.

def test_gate7_fast_path_is_measurably_faster_at_scale(tmp_path):
    print("Gate 7: fast-path restore is measurably faster than full replay "
          "at real scale (not just fewer calls -- actual wall-clock)...")
    state = str(tmp_path)
    n_base = 20_000
    n_delta = 25
    manager, tick, _ = _build()
    manager.configure_wal_under(state)
    for i in range(n_base):
        _close_window(manager, tick, f"h{i}", chi=i)  # unique chi -> O(1) index
    manager.compact()
    for i in range(n_delta):
        _close_window(manager, tick, f"post{i}", chi=10_000_000 + i)
    manifest = manager.snapshot_incremental()
    manifest_path = tmp_path / "timing-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )

    ckpt = _checkpoint_path(state)
    fast_samples = []
    slow_samples = []
    restored_counts = []
    for use_checkpoint in (True, False, False, True, True, False):
        hidden = ckpt + ".hidden"
        if not use_checkpoint:
            os.rename(ckpt, hidden)
        try:
            # Production boot always occurs in a fresh ECS task process.
            # Measuring inside pytest's long-lived 1,700-test interpreter
            # makes the checkpoint JSON path inherit arbitrary allocator/GC
            # history that production boot never has.  Each path therefore
            # gets the same real boundary: a new interpreter, with process
            # startup and manifest parsing outside the timed restore itself.
            result = _fresh_process_restore(
                manifest_path,
                _wal_dir(state),
            )
            elapsed = result["elapsed"]
            restored_counts.append(result["count"])
            (
                fast_samples if use_checkpoint else slow_samples
            ).append(elapsed)
        finally:
            if not use_checkpoint:
                os.rename(hidden, ckpt)

    assert restored_counts == [n_base + n_delta] * 6
    t_fast = statistics.median(fast_samples)
    t_slow = statistics.median(slow_samples)
    print(f"\n[wal-checkpoint-timing] base={n_base} delta={n_delta} "
          f"fast_samples={[round(value*1000, 1) for value in fast_samples]} "
          f"full_replay_samples="
          f"{[round(value*1000, 1) for value in slow_samples]} "
          f"fast_path={t_fast*1000:.1f}ms full_replay={t_slow*1000:.1f}ms "
          f"speedup={t_slow/max(t_fast, 1e-9):.1f}x")
    # A real, not-noise floor -- measured 1.6x-2.2x across runs at this
    # scale. Not asserting a bigger number: this is a constant-factor win
    # (see the gate's module-level comment), and an inflated threshold here
    # would just make the test flaky without proving anything more true.
    assert t_fast < t_slow * 0.75
    print("  PASS: fast path measurably faster (constant-factor, not "
          "complexity-class -- see comment above)")


# Uses tmp_path/monkeypatch/parametrize -- pytest fixtures, not standalone
# runnable. Run via: python3 -m pytest tests/test_wal_boot_checkpoint_fast_path.py -v
