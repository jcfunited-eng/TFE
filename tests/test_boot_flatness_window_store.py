"""Boot-flatness proof for the disk-resident window store (P1).

GL-SPC-SUBSTRATE-TRUE Change 1, test item (a): generate synthetic WAL
volumes at 1x and 10x and assert

  * boot peak RSS stays within 5% between the two volumes (RAM must never
    scale with lifetime experience);
  * window CONTENT does not materialize at boot (no pending records, empty
    LRU cache);
  * the boot index scan reconstructs exactly the chi index the writing
    manager held (index equality).

Each boot runs in its own subprocess so ru_maxrss measures that boot alone.
Windows are deliberately content-heavy (~100KB each) so a resident-store
regression would blow the 5% envelope immediately, while the legitimate
index/locator/metadata growth stays well inside it.
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, REPO_ROOT)

from dsf_ai_service.substrate.window_manager import (  # noqa: E402
    WAL_DIRNAME,
    WindowManager,
)

WINDOWS_1X = 60
VOLUME_MULTIPLIER = 10
PAD_BYTES = 100_000
RSS_TOLERANCE = 0.05

_BOOT_SCRIPT = r"""
import hashlib, json, os, resource, sys
sys.path.insert(0, sys.argv[1])
from dsf_ai_service.substrate.window_manager import WindowManager

state_dir = sys.argv[2]
manifest = json.load(open(os.path.join(state_dir, "manifest.json")))
manager = WindowManager(
    atlas_record_fn=lambda *a, **kw: None,
    log_event_fn=lambda *a, **kw: None,
    get_tick_fn=lambda: 0,
    atlas_windows={},
)
manager.restore_from_wal(
    manifest, os.path.join(state_dir, sys.argv[3]))
peak_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
chi_checksum = hashlib.sha256(json.dumps(
    {str(chi): locations
     for chi, locations in sorted(manager._chi_index.items())},
    sort_keys=True, separators=(",", ":")).encode()).hexdigest()
print(json.dumps({
    "peak_kb": peak_kb,
    "windows": manager.closed_window_count(),
    "pending": len(manager._pending),
    "cache_entries": manager.cache_stats()["entries"],
    "cache_bytes": manager.cache_stats()["bytes"],
    "chi_checksum": chi_checksum,
}))
"""


def _chi_checksum(manager):
    return hashlib.sha256(json.dumps(
        {str(chi): locations
         for chi, locations in sorted(manager._chi_index.items())},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _build_volume(state_dir, n_windows):
    """Synthesize a WAL volume through the real close+compact path."""
    tick = {"value": 0}
    manager = WindowManager(
        atlas_record_fn=lambda *a, **kw: None,
        log_event_fn=lambda *a, **kw: None,
        get_tick_fn=lambda: tick["value"],
        atlas_windows={},
    )
    pad = "x" * PAD_BYTES
    for i in range(n_windows):
        context_id = f"ctx{i}"
        manager.begin_context(context_id, "input")
        for j in range(2):
            tick["value"] += 1
            manager.add_entry(
                modality="word", section="listen",
                motif_id=i * 10 + j, chi=2000 + (i % 29),
                tick=tick["value"], source_tag=f"w{j}",
                context_id=context_id, source="joe",
                episode_ref=f"episode:{context_id}",
                salience=1.0, dwell_ticks=2, note=pad,
            )
        manager.end_context(context_id, "context_complete")
    manager.configure_wal_under(state_dir)
    manifest = manager.snapshot_incremental()  # folds pending into a base
    with open(os.path.join(state_dir, "manifest.json"), "w") as handle:
        json.dump(manifest, handle)
    return manager


def _wal_bytes(state_dir):
    wal = os.path.join(state_dir, WAL_DIRNAME)
    return sum(os.path.getsize(os.path.join(wal, name))
               for name in os.listdir(wal))


def _boot_in_subprocess(state_dir):
    result = subprocess.run(
        [sys.executable, "-c", _BOOT_SCRIPT, REPO_ROOT, state_dir,
         WAL_DIRNAME],
        capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, (
        f"boot subprocess failed:\n{result.stdout}\n{result.stderr}")
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_boot_rss_flat_across_10x_volume(tmp_path):
    dir_1x = str(tmp_path / "vol1x")
    dir_10x = str(tmp_path / "vol10x")
    os.makedirs(dir_1x)
    os.makedirs(dir_10x)

    src_1x = _build_volume(dir_1x, WINDOWS_1X)
    src_10x = _build_volume(dir_10x, WINDOWS_1X * VOLUME_MULTIPLIER)

    # The volumes are genuinely an order of magnitude apart on disk.
    bytes_1x, bytes_10x = _wal_bytes(dir_1x), _wal_bytes(dir_10x)
    assert bytes_10x >= 9 * bytes_1x
    assert bytes_1x >= WINDOWS_1X * PAD_BYTES  # content-heavy as intended

    boot_1x = _boot_in_subprocess(dir_1x)
    boot_10x = _boot_in_subprocess(dir_10x)

    # Correctness: the scan saw every window and rebuilt the exact index.
    assert boot_1x["windows"] == WINDOWS_1X
    assert boot_10x["windows"] == WINDOWS_1X * VOLUME_MULTIPLIER
    assert boot_1x["chi_checksum"] == _chi_checksum(src_1x)
    assert boot_10x["chi_checksum"] == _chi_checksum(src_10x)

    # Content non-materialization: nothing resident after boot.
    for boot in (boot_1x, boot_10x):
        assert boot["pending"] == 0
        assert boot["cache_entries"] == 0
        assert boot["cache_bytes"] == 0

    # THE P1 proof: peak boot RSS flat within 5% across a 10x volume.
    peak_1x, peak_10x = boot_1x["peak_kb"], boot_10x["peak_kb"]
    delta = (peak_10x - peak_1x) / peak_1x
    print(f"\n[boot-flatness] 1x={peak_1x}KB 10x={peak_10x}KB "
          f"delta={delta * 100:.2f}% (wal 1x={bytes_1x / 1e6:.1f}MB "
          f"10x={bytes_10x / 1e6:.1f}MB)")
    assert delta <= RSS_TOLERANCE, (
        f"boot RSS grew {delta * 100:.1f}% across a 10x WAL volume — "
        f"window content (or an index that scales with content) is "
        f"materializing at boot again (P1 violation)")
