#!/usr/bin/env python3
"""Verify post-deploy runtime serving health without publication-ID authority."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path_str: str) -> Any:
    path = Path(path_str)
    return json.loads(path.read_text(encoding="utf-8"))


def as_record(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def first_record(value: Any) -> dict[str, Any]:
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    return as_record(value)


def text_or_none(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def append_reason(reasons: list[str], condition: bool, reason: str) -> None:
    if not condition:
        reasons.append(reason)


def is_blocked(payload: dict[str, Any]) -> bool:
    return payload.get("blocked") is True or text_or_none(payload.get("status")) == "blocked"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-row", required=True, help="JSON file containing the active runtime_refresh_runs row.")
    parser.add_argument("--recommendations", required=True, help="Recommendations API JSON capture.")
    parser.add_argument("--portfolio", required=True, help="Portfolio API JSON capture.")
    parser.add_argument("--admin", required=True, help="Admin system-status API JSON capture.")
    args = parser.parse_args()

    db_row = first_record(load_json(args.db_row))
    recommendations = as_record(load_json(args.recommendations))
    portfolio = as_record(load_json(args.portfolio))
    admin = as_record(load_json(args.admin))

    admin_refresh_policy = as_record(admin.get("refreshPolicy"))
    admin_canonical_policy = as_record(admin_refresh_policy.get("canonicalServingPolicy"))

    db_run_id = text_or_none(db_row.get("run_id"))
    db_generated_at = text_or_none(db_row.get("generated_at_utc")) or text_or_none(db_row.get("bundle_generated_at_utc"))
    recommendations_blocked = is_blocked(recommendations)
    portfolio_blocked = is_blocked(portfolio)

    reasons: list[str] = []
    warnings: list[str] = []

    append_reason(reasons, db_run_id is not None, "db_run_id_missing")
    append_reason(reasons, db_generated_at is not None, "db_generated_at_missing")
    append_reason(reasons, not recommendations_blocked, "recommendations_blocked")
    append_reason(reasons, not portfolio_blocked, "portfolio_blocked")
    append_reason(reasons, admin_refresh_policy.get("healthy") is True, "admin_refresh_policy_not_healthy")
    append_reason(reasons, admin_canonical_policy.get("allowed") is True, "admin_runtime_serving_not_allowed")

    if text_or_none(recommendations.get("snapshot_publication_id")) == "BYPASS_ACTIVE":
        warnings.append("recommendations_publication_contract_bypassed")
    if text_or_none(portfolio.get("snapshot_publication_id")) == "BYPASS_ACTIVE":
        warnings.append("portfolio_publication_contract_bypassed")
    if text_or_none(admin_canonical_policy.get("snapshot_publication_id")) == "BYPASS_ACTIVE":
        warnings.append("admin_publication_contract_bypassed")

    result = {
        "status": "pass" if not reasons else "fail",
        "reasons": reasons,
        "warnings": warnings,
        "expected_runtime_serving": {
          "run_id": db_run_id,
          "generated_at_utc": db_generated_at,
          "mode": "bypass_active",
        },
        "observed": {
            "recommendations": {
                "run_id": text_or_none(recommendations.get("run_id")),
                "generated_at_utc": text_or_none(recommendations.get("generated_at_utc")),
                "blocked": recommendations_blocked,
                "snapshot_publication_id": text_or_none(recommendations.get("snapshot_publication_id")),
            },
            "portfolio": {
                "run_id": text_or_none(portfolio.get("run_id")),
                "generated_at_utc": text_or_none(portfolio.get("generated_at_utc")),
                "blocked": portfolio_blocked,
                "snapshot_publication_id": text_or_none(portfolio.get("snapshot_publication_id")),
            },
            "admin": {
                "refresh_policy_healthy": admin_refresh_policy.get("healthy"),
                "serving_policy_allowed": admin_canonical_policy.get("allowed"),
                "run_id": text_or_none(admin_canonical_policy.get("run_id")),
                "snapshot_publication_id": text_or_none(admin_canonical_policy.get("snapshot_publication_id")),
            },
        },
    }

    sys.stdout.write(json.dumps(result, indent=2) + "\n")
    return 0 if not reasons else 1


if __name__ == "__main__":
    raise SystemExit(main())
