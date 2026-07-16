#!/usr/bin/env python3
"""Operator restore: bring a NAMED S3 backup of Guala's state onto disk.

GL-SPC-SUBSTRATE-TRUE-SINGLE-STACK-20260716-v3, Change 1, item 5.

THE ONLY sanctioned way to change the substrate's state vintage (P4: no
silent time travel).  This command:

  * runs ONLY while the service is STOPPED (it refuses if the state dir
    shows recent write activity, and requires an explicit operator
    confirmation flag);
  * restores exactly the backup the operator NAMES (never "the most
    recent" implicitly — use --list to see what exists);
  * verifies integrity after download: identity file parses, required
    state files are present, and the binding-window WAL replays clean
    (per-record hash + durable-prefix digest — the same verification the
    boot index scan performs);
  * logs itself loudly: console, an ``operator_restore.json`` marker in
    the state dir, and an ``operator_restore`` line appended to the
    substrate's events.log.

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

# A running substrate hot-saves every ~60s. If anything under the state dir
# was written this recently, the service is almost certainly still running.
RECENT_WRITE_WINDOW_SECONDS = 180


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


def _state_dir_recent_write(state_dir: str) -> tuple[bool, str, float]:
    """Newest mtime under the state dir (files only, one level of subdirs)."""
    newest_path, newest_mtime = "", 0.0
    if not os.path.isdir(state_dir):
        return False, "", 0.0
    for root, _dirs, files in os.walk(state_dir):
        for name in files:
            path = os.path.join(root, name)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            if mtime > newest_mtime:
                newest_mtime, newest_path = mtime, path
    age = time.time() - newest_mtime if newest_mtime else float("inf")
    return age < RECENT_WRITE_WINDOW_SECONDS, newest_path, age


def _download_backup(s3, bucket: str, backup: str, state_dir: str) -> int:
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
                    os.path.join(state_dir, os.path.dirname(rel)),
                    exist_ok=True)
            # The S3 mirror gzips plain-text state (guala_core.json.gz,
            # guala_windows_wal/seg-*.jsonl.gz); undo that so the local
            # state dir holds the exact plain filenames boot expects.
            if rel.endswith(".json.gz") or rel.endswith(".jsonl.gz"):
                local_path = os.path.join(state_dir, rel[:-3])
                body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
                with open(local_path, "wb") as handle:
                    handle.write(gzip.decompress(body))
            else:
                local_path = os.path.join(state_dir, rel)
                s3.download_file(bucket, key, local_path)
            count += 1
            print(f"[restore] {key} -> {local_path}")
    if not found_any:
        raise SystemExit(
            f"[restore] REFUSED: no objects under s3://{bucket}/{prefix} — "
            f"use --list to see available backups")
    return count


def _verify_restored_state(state_dir: str) -> dict:
    """Post-download integrity verification. Raises SystemExit on failure."""
    report: dict = {}
    # 1. Identity parses.
    identity_path = os.path.join(state_dir, "guala_identity.json")
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
               if not os.path.exists(os.path.join(state_dir, name))]
    if missing:
        raise SystemExit(
            f"[restore] VERIFY FAILED: backup is missing required state "
            f"files {missing} — refusing to leave a partial vintage")
    for name in REQUIRED_STATE_FILES:
        with open(os.path.join(state_dir, name)) as handle:
            json.load(handle)
    report["state_files"] = list(REQUIRED_STATE_FILES)

    # 3. Binding-window WAL replays clean (hash + durable-prefix digest) —
    #    the exact verification the boot index scan performs.
    windows_path = os.path.join(state_dir, "guala_windows.json")
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
        probe.restore_persisted(payload, state_dir)
        report["windows"] = {
            "closed_window_count": probe.closed_window_count(),
            "chi_buckets": len(probe.chi_index),
        }
        print(f"[restore] WAL verified: "
              f"{report['windows']['closed_window_count']} closed windows, "
              f"{report['windows']['chi_buckets']} chi buckets")
    else:
        report["windows"] = None
        print("[restore] note: backup carries no guala_windows.json "
              "(pre-window vintage); window memory will be empty")
    return report


def _log_operator_action(state_dir: str, backup: str, operator: str,
                         file_count: int, report: dict) -> None:
    record = {
        "event": "operator_restore",
        "backup": backup,
        "operator": operator,
        "files_restored": file_count,
        "verified": report,
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
    parser.add_argument("--state-dir", default=os.environ.get(
        "GUALA_STATE_DIR", "state"))
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--operator", default=os.environ.get("USER", "unknown"),
                        help="who is performing this restore (logged)")
    parser.add_argument("--i-stopped-the-service", action="store_true",
                        help="explicit confirmation that the substrate "
                             "service is STOPPED (required to restore)")
    args = parser.parse_args()

    s3 = _s3_client()
    if args.list:
        for name in _list_backups(s3, args.bucket):
            print(name)
        return
    if not args.backup:
        parser.error("--backup <name> is required (or --list)")
    if not args.i_stopped_the_service:
        raise SystemExit(
            "[restore] REFUSED: restore may only run while the service is "
            "STOPPED. Stop it, then re-run with --i-stopped-the-service.")

    recent, newest_path, age = _state_dir_recent_write(args.state_dir)
    if recent:
        raise SystemExit(
            f"[restore] REFUSED: {newest_path} was written {age:.0f}s ago — "
            f"the service still looks ALIVE. A restore under a running "
            f"substrate silently corrupts state. Stop the service and retry.")

    print("=" * 68)
    print(f"[restore] OPERATOR RESTORE — explicit state-vintage change (P4)")
    print(f"[restore] backup   : s3://{args.bucket}/{args.backup}")
    print(f"[restore] state dir: {args.state_dir}")
    print(f"[restore] operator : {args.operator}")
    print("=" * 68)

    os.makedirs(args.state_dir, exist_ok=True)
    file_count = _download_backup(s3, args.bucket, args.backup, args.state_dir)
    report = _verify_restored_state(args.state_dir)
    _log_operator_action(
        args.state_dir, args.backup, args.operator, file_count, report)
    print(f"[restore] DONE: {file_count} files restored and verified. "
          f"Start the service to boot on this vintage.")


if __name__ == "__main__":
    main()
