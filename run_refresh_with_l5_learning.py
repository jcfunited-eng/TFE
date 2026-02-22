#!/usr/bin/env python3
"""
Run UF snapshot refresh and then run L5 policy learning pipeline.

This wrapper is the production entrypoint for admin refresh jobs so policy
learning is automatically executed after refresh without manual one-off steps.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from l5_policy_learning_pipeline import run_l5_policy_learning
from rebuild_uf_snapshot import (
    REFRESH_MODE_FULL,
    REFRESH_MODE_TARGETED,
    rebuild_snapshot,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh UF snapshot and run L5 policy learning.")
    parser.add_argument(
        "--refresh-mode",
        choices=[REFRESH_MODE_FULL, REFRESH_MODE_TARGETED],
        default=REFRESH_MODE_FULL,
    )
    parser.add_argument(
        "--targeted-refresh",
        action="store_true",
        help="Shortcut for --refresh-mode targeted_pfsc.",
    )
    parser.add_argument(
        "--force-refresh-universe",
        action="store_true",
        help="Refresh universe caches from Massive before rebuild.",
    )
    parser.add_argument(
        "--years-history",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--skip-l5-learning",
        action="store_true",
        help="Run refresh only and skip policy learning pipeline.",
    )
    parser.add_argument(
        "--run-l5-on-targeted",
        action="store_true",
        help="Also run L5 learning after targeted refresh mode.",
    )
    return parser.parse_args()


def _resolve_latest_anomaly_policy_path() -> Path | None:
    env_path = str(os.environ.get("TFE_POLICY_ANOMALY_POLICY", "")).strip()
    if env_path:
        p = Path(env_path)
        if p.exists() and p.is_file():
            return p

    candidates = sorted(
        Path("backups").glob("pscf-policy-anomaly-watch-*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    for candidate in candidates:
        # Exclude report artifacts; we need policy artifacts with cells.
        if "-report-" in candidate.name:
            continue
        return candidate

    return None


def _ensure_learning_env() -> None:
    resolved = _resolve_latest_anomaly_policy_path()
    if resolved is not None:
        os.environ["TFE_POLICY_ANOMALY_POLICY"] = str(resolved)


def main() -> int:
    args = _parse_args()

    mode = str(args.refresh_mode)
    if bool(args.targeted_refresh):
        mode = REFRESH_MODE_TARGETED

    report = rebuild_snapshot(
        refresh_mode=mode,
        force_refresh_universe=bool(args.force_refresh_universe),
        years_history=int(args.years_history),
    )

    print("[REFRESH+L5] Refresh report:")
    print(json.dumps(report, indent=2))

    if bool(args.skip_l5_learning):
        print("[REFRESH+L5] L5 learning skipped by flag.")
        return 0

    should_run_l5 = mode == REFRESH_MODE_FULL or bool(args.run_l5_on_targeted)
    if not should_run_l5:
        print("[REFRESH+L5] L5 learning not run for targeted mode unless --run-l5-on-targeted is set.")
        return 0

    _ensure_learning_env()

    result = run_l5_policy_learning(trigger=f"refresh:{mode}")

    print("[REFRESH+L5] L5 learning report:")
    print(json.dumps(result.report, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
