#!/usr/bin/env python3
"""Operator restore: bring a NAMED S3 backup of Guala's state onto disk.

GL-SPC-SUBSTRATE-TRUE-SINGLE-STACK-20260716-v3, Change 1, item 5
(hardened per adversarial review 2026-07-16).

THE ONLY sanctioned way to change the substrate's state vintage (P4: no
silent time travel).  This command:

  * runs ONLY while the service is STOPPED — enforced by an explicit
    operator confirmation flag PLUS the service-held heartbeat file
    (substrate.alive, rewritten every 5s while alive) PLUS a recent-write
    probe over the state dir, re-checked again immediately before the swap
    (TOCTOU guard);
  * restores exactly the backup the operator NAMES (never "the most
    recent" implicitly — use --list to see what exists);
  * downloads and verifies into a STAGING directory first — the live state
    dir is untouched until verification passes; the verify probe's WAL
    replay (and its generation pruning) runs against staging only;
  * swaps atomically-per-entry and NEVER deletes the only copy: the
    displaced state is preserved intact under pre_restore_<ts>/ inside the
    state dir (same filesystem, no cross-device surprises on the EFS
    mount).  Because the ENTIRE old state — including the whole
    guala_windows_wal/ directory — is displaced, no stale same-generation
    higher-index WAL segments can survive to chimera with the restored
    vintage;
  * warns loudly if the restored identity differs from the displaced one;
  * logs itself loudly: console, an ``operator_restore.json`` marker, and
    an ``operator_restore`` line appended to the restored events.log.

Usage:
    python -m tools.restore_from_s3 --list
    python -m tools.restore_from_s3 --backup guala/2026-07-15_04-10-00 \
        --state-dir /app/state --operator joe --i-stopped-the-service

Boot never calls this.  A wipe-recovery path must exist at every moment:
this command is that path (it precedes the deletion of the legacy
FORCE_S3_RESTORE plumbing).
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time

DEFAULT_BUCKET = "dsf-ai-site-backups"
DEFAULT_REGION = "us-east-1"
DEFAULT_HEARTBEAT = os.environ.get("SUBSTRATE_HEARTBEAT",
                                   "/shared/substrate.alive")
# Backups live under either the dated manual prefix (guala/<date>_...) or
# the automatic quiet-point prefix (guala/auto/<date>_<reason>).
LIST_PREFIXES = ("guala/",)

REQUIRED_STATE_FILES = (
    "guala_identity.json",
    "guala_core.json",
    "guala_needs.json",
    "guala_coordinator.json",
    "guala_atlas.json",
    "guala_sections.json",
    "guala_bucket.json",
)

# A running substrate rewrites substrate.alive every ~5s; anything younger
# than this is a live service.
HEARTBEAT_STALE_SECONDS = 60
# A running substrate also hot-saves every ~60s, but pause/sleep states can
# go minutes without writing — which is why the heartbeat above is the
# PRIMARY guard and this mtime probe is only a second, independent tripwire.
RECENT_WRITE_WINDOW_SECONDS = 180

STAGING_PREFIX = ".restore_staging_"
DISPLACED_PREFIX = "pre_restore_"


def _s3_client():
    import boto3

    return boto3.client("s3", region_name=DEFAULT_REGION)


def _list_backups(s3, bucket: str) -> list[str]:
    names: set[str] = set()
    paginator = s3.get_paginator("list_objects_v2")
    for prefix in LIST_PREFIXES:
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []) or []:
                key = obj["Key"]
                parts = key.split("/")
                # guala/<name>/file...  or  guala/auto/<name>/file...
                if len(parts) >= 3 and parts[1] == "auto":
                    names.add("/".join(parts[:3]))
                elif len(parts) >= 2 and "/" in key:
                    names.add("/".join(parts[:2]))
    return sorted(names)


def _is_restore_artifact(name: str) -> bool:
    return name.startswith(STAGING_PREFIX) or name.startswith(DISPLACED_PREFIX)


def _heartbeat_alive(heartbeat_path: str) -> tuple[bool, float]:
    try:
        age = time.time() - os.path.getmtime(heartbeat_path)
    except OSError:
        return False, float("inf")
    return age < HEARTBEAT_STALE_SECONDS, age


def _state_dir_recent_write(state_dir: str) -> tuple[bool, str, float]:
    """Newest mtime under the state dir, ignoring this tool's own artifacts."""
    newest_path, newest_mtime = "", 0.0
    if not os.path.isdir(state_dir):
        return False, "", 0.0
    for root, dirs, files in os.walk(state_dir):
        if root == state_dir:
            dirs[:] = [d for d in dirs if not _is_restore_artifact(d)]
        for name in files:
            if root == state_dir and name == "operator_restore.json":
                continue
            path = os.path.join(root, name)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            if mtime > newest_mtime:
                newest_mtime, newest_path = mtime, path
    age = time.time() - newest_mtime if newest_mtime else float("inf")
    return age < RECENT_WRITE_WINDOW_SECONDS, newest_path, age


def _require_service_stopped(state_dir: str, heartbeat_path: str,
                             stage: str) -> None:
    """Both liveness guards; SystemExit if the service looks alive.

    ``stage`` labels the check ("pre-download" / "pre-swap") — the pre-swap
    re-check closes the TOCTOU window between verification and the swap.
    """
    alive, age = _heartbeat_alive(heartbeat_path)
    if alive:
        raise SystemExit(
            f"[restore] REFUSED ({stage}): heartbeat {heartbeat_path} was "
            f"written {age:.0f}s ago — the substrate service is ALIVE. "
            f"Stop the service and retry.")
    recent, newest_path, write_age = _state_dir_recent_write(state_dir)
    if recent:
        raise SystemExit(
            f"[restore] REFUSED ({stage}): {newest_path} was written "
            f"{write_age:.0f}s ago — the service still looks ALIVE. A "
            f"restore under a running substrate silently corrupts state. "
            f"Stop the service and retry.")


def _download_backup(s3, bucket: str, backup: str, target_dir: str) -> int:
    prefix = backup.rstrip("/") + "/"
    paginator = s3.get_paginator("list_objects_v2")
    count = 0
    found_any = False
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []) or []:
            found_any = True
            key = obj["Key"]
            rel = key[len(prefix):]
            if not rel:
                continue
            if "/" in rel:
                os.makedirs(
                    os.path.join(target_dir, os.path.dirname(rel)),
                    exist_ok=True)
            # The S3 mirror gzips plain-text state (guala_core.json.gz,
            # guala_windows_wal/seg-*.jsonl.gz); undo that so the local
            # state dir holds the exact plain filenames boot expects.
            if rel.endswith(".json.gz") or rel.endswith(".jsonl.gz"):
                local_path = os.path.join(target_dir, rel[:-3])
                body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
                with open(local_path, "wb") as handle:
                    handle.write(gzip.decompress(body))
            else:
                local_path = os.path.join(target_dir, rel)
                s3.download_file(bucket, key, local_path)
            count += 1
            print(f"[restore] {key} -> {local_path}")
    if not found_any:
        raise SystemExit(
            f"[restore] REFUSED: no objects under s3://{bucket}/{prefix} — "
            f"use --list to see available backups")
    return count


def _verify_restored_state(staged_dir: str) -> dict:
    """Integrity verification against the STAGING dir only (never the live
    state dir — the WAL probe replays and prunes generations in place).
    Raises SystemExit on failure."""
    report: dict = {}
    # 1. Identity parses.
    identity_path = os.path.join(staged_dir, "guala_identity.json")
    if not os.path.exists(identity_path):
        raise SystemExit("[restore] VERIFY FAILED: guala_identity.json absent")
    with open(identity_path) as handle:
        identity = json.load(handle)
    if not identity.get("guala_identity"):
        raise SystemExit(
            "[restore] VERIFY FAILED: guala_identity.json lacks an identity")
    report["identity"] = identity["guala_identity"]

    # 2. Required state files present + parse as JSON.
    missing = [name for name in REQUIRED_STATE_FILES
               if not os.path.exists(os.path.join(staged_dir, name))]
    if missing:
        raise SystemExit(
            f"[restore] VERIFY FAILED: backup is missing required state "
            f"files {missing} — refusing to install a partial vintage")
    for name in REQUIRED_STATE_FILES:
        with open(os.path.join(staged_dir, name)) as handle:
            json.load(handle)
    report["state_files"] = list(REQUIRED_STATE_FILES)

    # 3. Binding-window WAL replays clean (hash + durable-prefix digest) —
    #    the exact verification the boot index scan performs.
    windows_path = os.path.join(staged_dir, "guala_windows.json")
    if os.path.exists(windows_path):
        sys.path.insert(0, os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))
        from dsf_ai_service.substrate.window_manager import WindowManager

        with open(windows_path) as handle:
            raw = json.load(handle)
        payload = raw.get("data") if isinstance(raw, dict) and "data" in raw \
            and "guala_identity" in raw else raw
        probe = WindowManager(
            atlas_record_fn=lambda *a, **kw: None,
            log_event_fn=lambda *a, **kw: None,
            get_tick_fn=lambda: 0,
            atlas_windows={},
        )
        probe.restore_persisted(payload, staged_dir)
        report["windows"] = {
            "closed_window_count": probe.closed_window_count(),
            "chi_buckets": len(probe.chi_index),
        }
        print(f"[restore] WAL verified (in staging): "
              f"{report['windows']['closed_window_count']} closed windows, "
              f"{report['windows']['chi_buckets']} chi buckets")
    else:
        report["windows"] = None
        print("[restore] note: backup carries no guala_windows.json "
              "(pre-window vintage); window memory will be empty")
    return report


def _warn_on_identity_change(state_dir: str, staged_identity: str) -> None:
    current_path = os.path.join(state_dir, "guala_identity.json")
    try:
        with open(current_path) as handle:
            current = json.load(handle).get("guala_identity")
    except (OSError, json.JSONDecodeError):
        return
    if current and current != staged_identity:
        print("!" * 68)
        print(f"[restore] IDENTITY CHANGE: on-disk identity {current[:8]}.. "
              f"will be DISPLACED by backup identity {staged_identity[:8]}..")
        print(f"[restore] The displaced state is preserved under "
              f"{DISPLACED_PREFIX}<ts>/ — nothing is deleted.")
        print("!" * 68)


def _swap_staging_into_place(state_dir: str, staging_dir: str,
                             ts_label: str) -> str:
    """Displace the ENTIRE current state into pre_restore_<ts>/ then move the
    staged entries in.  Same filesystem (staging lives inside state_dir), so
    every move is an atomic rename; the displaced copy is never deleted.
    Displacing the whole guala_windows_wal/ directory also guarantees no
    stale same-generation segment can interleave with the restored WAL."""
    displaced_dir = os.path.join(state_dir, f"{DISPLACED_PREFIX}{ts_label}")
    os.makedirs(displaced_dir)
    staging_name = os.path.basename(staging_dir)
    for name in os.listdir(state_dir):
        if name == staging_name or _is_restore_artifact(name):
            continue
        os.rename(os.path.join(state_dir, name),
                  os.path.join(displaced_dir, name))
    for name in os.listdir(staging_dir):
        os.rename(os.path.join(staging_dir, name),
                  os.path.join(state_dir, name))
    os.rmdir(staging_dir)
    # Commit the directory entries (EFS/NFS discipline).
    fd = os.open(state_dir, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return displaced_dir


def _log_operator_action(state_dir: str, backup: str, operator: str,
                         file_count: int, report: dict,
                         displaced_dir: str) -> None:
    record = {
        "event": "operator_restore",
        "backup": backup,
        "operator": operator,
        "files_restored": file_count,
        "verified": report,
        "displaced_state": displaced_dir,
        "wall_clock": time.time(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "command": " ".join(sys.argv),
    }
    marker_path = os.path.join(state_dir, "operator_restore.json")
    with open(marker_path, "w") as handle:
        json.dump(record, handle, indent=1)
    # Loud line in the substrate's own event log too.
    events_path = os.path.join(state_dir, "events.log")
    try:
        with open(events_path, "a") as handle:
            handle.write(json.dumps({"kind": "operator_restore",
                                     "detail": record}) + "\n")
    except OSError as error:
        print(f"[restore] note: could not append to events.log: {error}")
    print(f"[restore] OPERATOR ACTION LOGGED: {marker_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Restore a NAMED S3 backup to the Guala state dir "
                    "(operator action; service must be STOPPED).")
    parser.add_argument("--list", action="store_true",
                        help="list available backup names and exit")
    parser.add_argument("--backup",
                        help="exact backup name to restore, e.g. "
                             "guala/2026-07-15_04-10-00 or "
                             "guala/auto/2026-07-15_09-00-00_backstop")
    parser.add_argument("--state-dir",
                        default=os.environ.get("GUALA_STATE_DIR"),
                        help="ABSOLUTE state directory (default: "
                             "$GUALA_STATE_DIR; required if unset — no "
                             "silent relative default)")
    parser.add_argument("--heartbeat-path", default=DEFAULT_HEARTBEAT,
                        help="service-held heartbeat file "
                             "(default: $SUBSTRATE_HEARTBEAT or "
                             "/shared/substrate.alive)")
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--operator", default=os.environ.get("USER", "unknown"),
                        help="who is performing this restore (logged)")
    parser.add_argument("--i-stopped-the-service", action="store_true",
                        help="explicit confirmation that the substrate "
                             "service is STOPPED (required to restore)")
    args = parser.parse_args()

    if args.list:
        s3 = _s3_client()
        for name in _list_backups(s3, args.bucket):
            print(name)
        return
    if not args.backup:
        parser.error("--backup <name> is required (or --list)")
    if not args.state_dir:
        parser.error("--state-dir is required (or set GUALA_STATE_DIR); "
                     "a relative default would restore into whatever "
                     "directory this happens to run from")
    if not os.path.isabs(args.state_dir):
        parser.error(f"--state-dir must be absolute, got {args.state_dir!r}")
    if not args.i_stopped_the_service:
        raise SystemExit(
            "[restore] REFUSED: restore may only run while the service is "
            "STOPPED. Stop it, then re-run with --i-stopped-the-service.")

    _require_service_stopped(args.state_dir, args.heartbeat_path,
                             "pre-download")

    ts_label = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    staging_dir = os.path.join(args.state_dir, f"{STAGING_PREFIX}{ts_label}")

    print("=" * 68)
    print(f"[restore] OPERATOR RESTORE — explicit state-vintage change (P4)")
    print(f"[restore] backup   : s3://{args.bucket}/{args.backup}")
    print(f"[restore] state dir: {args.state_dir}")
    print(f"[restore] staging  : {staging_dir}")
    print(f"[restore] operator : {args.operator}")
    print("=" * 68)

    os.makedirs(args.state_dir, exist_ok=True)
    os.makedirs(staging_dir)
    s3 = _s3_client()
    file_count = _download_backup(s3, args.bucket, args.backup, staging_dir)
    report = _verify_restored_state(staging_dir)
    _warn_on_identity_change(args.state_dir, report["identity"])

    # TOCTOU guard: the download/verify took real time — re-prove the
    # service is still stopped immediately before touching the live dir.
    _require_service_stopped(args.state_dir, args.heartbeat_path, "pre-swap")

    displaced_dir = _swap_staging_into_place(
        args.state_dir, staging_dir, ts_label)
    _log_operator_action(args.state_dir, args.backup, args.operator,
                         file_count, report, displaced_dir)
    print(f"[restore] DONE: {file_count} files restored and verified. "
          f"Displaced state preserved at {displaced_dir} (operator cleans "
          f"up after confirming the new vintage boots). Start the service "
          f"to boot on this vintage.")


if __name__ == "__main__":
    main()
