"""Operator-restore safety contracts (review blocker 2, 2026-07-16) — no AWS.

Pins the properties that keep the restore command from destroying the only
copy of the substrate's state:

  * liveness guards: a fresh service heartbeat OR recent state-dir writes
    refuse the restore (the heartbeat is the primary guard — a paused/
    sleeping substrate writes no state for minutes while very much alive);
  * the guard ignores the tool's own artifacts (staging/, pre_restore_/,
    marker) so the TOCTOU re-check after download cannot self-trip;
  * verification runs against the STAGING dir only — the live state dir's
    WAL is untouched by the probe;
  * the swap displaces the ENTIRE old state (including the whole WAL dir —
    no stale same-generation segments can chimera with the restored one)
    into pre_restore_<ts>/, installs the staged state, and deletes nothing;
  * a partial staged vintage refuses to install.
"""

import json
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import restore_from_s3 as tool  # noqa: E402
from dsf_ai_service.substrate.window_manager import (  # noqa: E402
    WAL_DIRNAME,
    WindowManager,
)


def _age(path, seconds):
    stamp = time.time() - seconds
    os.utime(path, (stamp, stamp))


def _make_state(state_dir, *, marker="OLD", age_seconds=3600):
    """A minimal plausible state dir with a WAL segment; aged as requested."""
    os.makedirs(state_dir, exist_ok=True)
    for name in tool.REQUIRED_STATE_FILES:
        with open(os.path.join(state_dir, name), "w") as handle:
            json.dump({"guala_identity": f"identity-{marker}",
                       "data": marker}, handle)
    wal = os.path.join(state_dir, WAL_DIRNAME)
    os.makedirs(wal, exist_ok=True)
    seg = os.path.join(wal, "seg-00000007-00000003.jsonl")
    with open(seg, "w") as handle:
        handle.write("")
    for root, _dirs, files in os.walk(state_dir):
        for name in files:
            _age(os.path.join(root, name), age_seconds)
    return seg


# ── liveness guards ──────────────────────────────────────────────────────────

def test_fresh_heartbeat_refuses(tmp_path):
    state = str(tmp_path / "state")
    _make_state(state)
    heartbeat = str(tmp_path / "substrate.alive")
    with open(heartbeat, "w") as handle:
        handle.write("alive")
    with pytest.raises(SystemExit, match="heartbeat"):
        tool._require_service_stopped(state, heartbeat, "pre-download")


def test_stale_heartbeat_and_old_state_pass(tmp_path):
    state = str(tmp_path / "state")
    _make_state(state)
    heartbeat = str(tmp_path / "substrate.alive")
    with open(heartbeat, "w") as handle:
        handle.write("alive")
    _age(heartbeat, tool.HEARTBEAT_STALE_SECONDS + 30)
    tool._require_service_stopped(state, heartbeat, "pre-download")


def test_missing_heartbeat_falls_back_to_mtime_guard(tmp_path):
    state = str(tmp_path / "state")
    _make_state(state, age_seconds=0)  # fresh writes: service looks alive
    with pytest.raises(SystemExit, match="looks ALIVE"):
        tool._require_service_stopped(
            state, str(tmp_path / "no.alive"), "pre-swap")


def test_mtime_guard_ignores_the_tools_own_artifacts(tmp_path):
    state = str(tmp_path / "state")
    _make_state(state)
    # The TOCTOU re-check runs right after WE wrote gigabytes into staging —
    # our own writes (and prior displaced copies) must not self-trip it.
    staging = os.path.join(state, f"{tool.STAGING_PREFIX}20260716T000000Z")
    displaced = os.path.join(state, f"{tool.DISPLACED_PREFIX}20260101T000000Z")
    for directory in (staging, displaced):
        os.makedirs(directory)
        with open(os.path.join(directory, "fresh.json"), "w") as handle:
            handle.write("{}")
    tool._require_service_stopped(
        state, str(tmp_path / "no.alive"), "pre-swap")


# ── verify: staging only, partial vintage refused ────────────────────────────

def _stage_real_backup(staging_dir):
    """Build a verifiable staged vintage through the real WindowManager."""
    os.makedirs(staging_dir, exist_ok=True)
    tick = {"value": 0}
    manager = WindowManager(
        atlas_record_fn=lambda *a, **kw: None,
        log_event_fn=lambda *a, **kw: None,
        get_tick_fn=lambda: tick["value"],
        atlas_windows={},
    )
    manager.begin_context("ctx", "input")
    tick["value"] += 1
    manager.add_entry(modality="word", section="listen", motif_id=1, chi=5,
                      tick=tick["value"], source_tag="w", context_id="ctx")
    manager.end_context("ctx", "done")
    manager.configure_wal_under(staging_dir)
    manifest = manager.snapshot_incremental()
    for name in tool.REQUIRED_STATE_FILES:
        with open(os.path.join(staging_dir, name), "w") as handle:
            json.dump({"guala_identity": "identity-NEW"}, handle)
    with open(os.path.join(staging_dir, "guala_windows.json"), "w") as handle:
        json.dump(manifest, handle)


def test_verify_runs_against_staging_and_leaves_live_dir_alone(tmp_path):
    state = str(tmp_path / "state")
    live_seg = _make_state(state)
    live_before = sorted(os.listdir(os.path.join(state, WAL_DIRNAME)))
    staging = os.path.join(state, f"{tool.STAGING_PREFIX}t")
    _stage_real_backup(staging)

    report = tool._verify_restored_state(staging)
    assert report["identity"] == "identity-NEW"
    assert report["windows"]["closed_window_count"] == 1
    # The live dir's WAL was not replayed, pruned, or otherwise touched.
    assert sorted(os.listdir(os.path.join(state, WAL_DIRNAME))) == live_before
    assert os.path.exists(live_seg)


def test_partial_staged_vintage_is_refused(tmp_path):
    staging = str(tmp_path / "staging")
    _stage_real_backup(staging)
    os.remove(os.path.join(staging, "guala_atlas.json"))
    with pytest.raises(SystemExit, match="missing required state"):
        tool._verify_restored_state(staging)


# ── swap: displaces everything, deletes nothing ──────────────────────────────

def test_swap_preserves_displaced_state_and_installs_staged(tmp_path):
    state = str(tmp_path / "state")
    _make_state(state, marker="OLD")
    old_names = set(os.listdir(state))
    staging = os.path.join(state, f"{tool.STAGING_PREFIX}20260716T010203Z")
    _stage_real_backup(staging)
    staged_names = set(os.listdir(staging))

    displaced_dir = tool._swap_staging_into_place(
        state, staging, "20260716T010203Z")

    # Every displaced entry is preserved, byte-for-byte reachable.
    assert set(os.listdir(displaced_dir)) == old_names
    with open(os.path.join(displaced_dir, "guala_core.json")) as handle:
        assert json.load(handle)["guala_identity"] == "identity-OLD"
    # The old WAL dir moved WHOLESALE — no stale segment left at top level.
    assert os.path.exists(
        os.path.join(displaced_dir, WAL_DIRNAME,
                     "seg-00000007-00000003.jsonl"))
    # The staged vintage now IS the state dir (plus the displaced dir).
    now = set(os.listdir(state))
    assert staged_names <= now
    assert os.path.basename(displaced_dir) in now
    assert not os.path.exists(staging)
    with open(os.path.join(state, "guala_core.json")) as handle:
        assert json.load(handle)["guala_identity"] == "identity-NEW"
    # And the restored vintage boots clean through the real index scan.
    probe = WindowManager(
        atlas_record_fn=lambda *a, **kw: None,
        log_event_fn=lambda *a, **kw: None,
        get_tick_fn=lambda: 0,
        atlas_windows={},
    )
    with open(os.path.join(state, "guala_windows.json")) as handle:
        probe.restore_persisted(json.load(handle), state)
    assert probe.closed_window_count() == 1


def test_swap_keeps_prior_displaced_copies(tmp_path):
    state = str(tmp_path / "state")
    _make_state(state)
    earlier = os.path.join(state, f"{tool.DISPLACED_PREFIX}20260101T000000Z")
    os.makedirs(earlier)
    with open(os.path.join(earlier, "keep.json"), "w") as handle:
        handle.write("{}")
    staging = os.path.join(state, f"{tool.STAGING_PREFIX}t2")
    _stage_real_backup(staging)

    tool._swap_staging_into_place(state, staging, "t2")
    assert os.path.exists(os.path.join(earlier, "keep.json"))
