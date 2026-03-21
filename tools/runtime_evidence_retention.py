#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STAMPED_DIR_RE = re.compile(r"^(?P<prefix>.+)-(?P<stamp>\d{8}T\d{6}Z)$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _collect(runtime_dir: Path, include_prefixes: set[str] | None) -> tuple[dict[str, list[dict[str, str]]], list[str]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    unmatched_dirs: list[str] = []

    for child in sorted(runtime_dir.iterdir(), key=lambda p: p.name):
        if not child.is_dir():
            continue
        match = STAMPED_DIR_RE.match(child.name)
        if not match:
            unmatched_dirs.append(child.name)
            continue

        prefix = str(match.group("prefix"))
        stamp = str(match.group("stamp"))
        if include_prefixes and prefix not in include_prefixes:
            continue

        groups[prefix].append(
            {
                "name": child.name,
                "stamp": stamp,
                "path": str(child),
            }
        )

    for prefix in list(groups.keys()):
        groups[prefix] = sorted(groups[prefix], key=lambda row: row["stamp"], reverse=True)

    return groups, unmatched_dirs


def _build_plan(groups: dict[str, list[dict[str, str]]], keep_per_prefix: int) -> tuple[list[dict[str, str]], dict[str, Any]]:
    plan: list[dict[str, str]] = []
    by_prefix: dict[str, Any] = {}

    for prefix in sorted(groups.keys()):
        rows = groups[prefix]
        keep_rows = rows[:keep_per_prefix]
        move_rows = rows[keep_per_prefix:]

        by_prefix[prefix] = {
            "total": len(rows),
            "kept": [row["name"] for row in keep_rows],
            "to_archive": [row["name"] for row in move_rows],
        }

        for row in move_rows:
            plan.append(
                {
                    "prefix": prefix,
                    "name": row["name"],
                    "source": row["path"],
                }
            )

    return plan, by_prefix


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Archive old runtime evidence directories by stamped prefix.")
    parser.add_argument("--runtime-dir", default="backups/runtime", help="Runtime evidence root directory.")
    parser.add_argument("--keep-per-prefix", type=int, default=3, help="How many newest stamped dirs to keep per prefix.")
    parser.add_argument(
        "--include-prefix",
        action="append",
        default=[],
        help="Optional stamped prefix to include. Can be set multiple times.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply archive moves. Without this flag, script prints a dry-run plan only.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    runtime_dir = Path(args.runtime_dir).resolve()
    keep_per_prefix = int(args.keep_per_prefix)
    include_prefixes = {str(x).strip() for x in args.include_prefix if str(x).strip()}

    if keep_per_prefix < 1:
        print(json.dumps({"status": "fail", "reason": "keep_per_prefix_must_be_positive"}, indent=2))
        return 1

    if not runtime_dir.is_dir():
        print(
            json.dumps(
                {
                    "status": "fail",
                    "reason": "runtime_dir_missing",
                    "runtime_dir": str(runtime_dir),
                },
                indent=2,
            )
        )
        return 1

    groups, unmatched_dirs = _collect(runtime_dir, include_prefixes if include_prefixes else None)
    plan, by_prefix = _build_plan(groups, keep_per_prefix)

    archive_root = runtime_dir / "_archive"
    archive_dir = archive_root / f"prune-{_utc_stamp()}"
    moved: list[dict[str, str]] = []

    if args.apply and plan:
        archive_dir.mkdir(parents=True, exist_ok=True)
        for row in plan:
            source = Path(row["source"])
            target = archive_dir / row["name"]
            if target.exists():
                print(
                    json.dumps(
                        {
                            "status": "fail",
                            "reason": "archive_target_exists",
                            "target": str(target),
                        },
                        indent=2,
                    )
                )
                return 1
            shutil.move(str(source), str(target))
            moved.append(
                {
                    "prefix": row["prefix"],
                    "name": row["name"],
                    "source": str(source),
                    "target": str(target),
                }
            )

    summary_dir = runtime_dir / f"retention-{_utc_stamp()}"
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / "summary.json"

    summary: dict[str, Any] = {
        "status": "pass",
        "generated_at_utc": _utc_now(),
        "runtime_dir": str(runtime_dir),
        "keep_per_prefix": keep_per_prefix,
        "apply": bool(args.apply),
        "dry_run": not bool(args.apply),
        "include_prefixes": sorted(include_prefixes),
        "matched_prefix_count": len(groups),
        "candidate_dir_count": sum(len(rows) for rows in groups.values()),
        "move_count": len(plan),
        "moved_count": len(moved),
        "archive_dir": str(archive_dir) if args.apply and plan else None,
        "summary_path": str(summary_path),
        "prefixes": by_prefix,
        "unmatched_top_level_dirs_count": len(unmatched_dirs),
        "unmatched_top_level_dirs_sample": unmatched_dirs[:50],
        "moved": moved,
        "planned_moves": plan,
    }

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
