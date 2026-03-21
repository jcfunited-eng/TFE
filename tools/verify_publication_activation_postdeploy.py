#!/usr/bin/env python3
"""Verify post-deploy publication activation using captured JSON artifacts."""

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


def bool_or_none(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def append_reason(reasons: list[str], condition: bool, reason: str) -> None:
    if not condition:
        reasons.append(reason)


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
    admin_serving_bundle = as_record(admin.get("servingBundle"))

    db_run_id = text_or_none(db_row.get("run_id"))
    db_generated_at = text_or_none(db_row.get("bundle_generated_at_utc")) or text_or_none(db_row.get("generated_at_utc"))
    db_validation = text_or_none(db_row.get("validation_status"))
    db_snapshot_pub = text_or_none(db_row.get("snapshot_publication_id"))
    db_quote_pub = text_or_none(db_row.get("quote_publication_id"))
    db_quote_binding = text_or_none(db_row.get("quote_binding_status"))
    db_is_active = bool_or_none(db_row.get("is_active_publication"))

    reasons: list[str] = []

    append_reason(reasons, db_is_active is True, "db_row_not_marked_active_publication")
    append_reason(reasons, db_validation == "pass", "db_validation_status_not_pass")
    append_reason(reasons, db_snapshot_pub is not None, "db_snapshot_publication_id_missing")
    append_reason(reasons, db_quote_pub is not None, "db_quote_publication_id_missing")
    append_reason(reasons, db_quote_binding == "aligned", "db_quote_binding_status_not_aligned")
    append_reason(reasons, db_run_id is not None, "db_run_id_missing")
    append_reason(reasons, db_generated_at is not None, "db_generated_at_missing")

    rec_blocked = recommendations.get("blocked") is True or recommendations.get("status") == "blocked"
    port_blocked = portfolio.get("blocked") is True or portfolio.get("status") == "blocked"
    rec_stale = as_record(recommendations.get("freshness")).get("stale") is True
    port_stale = as_record(portfolio.get("freshness")).get("stale") is True

    append_reason(reasons, not rec_blocked, "recommendations_blocked")
    append_reason(reasons, not port_blocked, "portfolio_blocked")
    append_reason(reasons, not rec_stale, "recommendations_stale")
    append_reason(reasons, not port_stale, "portfolio_stale")

    append_reason(reasons, text_or_none(recommendations.get("run_id")) == db_run_id, "recommendations_run_id_mismatch")
    append_reason(reasons, text_or_none(portfolio.get("run_id")) == db_run_id, "portfolio_run_id_mismatch")
    append_reason(reasons, text_or_none(recommendations.get("validation_status")) == db_validation, "recommendations_validation_status_mismatch")
    append_reason(reasons, text_or_none(portfolio.get("validation_status")) == db_validation, "portfolio_validation_status_mismatch")
    append_reason(reasons, text_or_none(recommendations.get("snapshot_publication_id")) == db_snapshot_pub, "recommendations_snapshot_publication_id_mismatch")
    append_reason(reasons, text_or_none(portfolio.get("snapshot_publication_id")) == db_snapshot_pub, "portfolio_snapshot_publication_id_mismatch")
    append_reason(reasons, text_or_none(recommendations.get("quote_publication_id")) == db_quote_pub, "recommendations_quote_publication_id_mismatch")
    append_reason(reasons, text_or_none(portfolio.get("quote_publication_id")) == db_quote_pub, "portfolio_quote_publication_id_mismatch")
    append_reason(reasons, text_or_none(recommendations.get("quote_binding_status")) == db_quote_binding, "recommendations_quote_binding_status_mismatch")
    append_reason(reasons, text_or_none(portfolio.get("quote_binding_status")) == db_quote_binding, "portfolio_quote_binding_status_mismatch")
    append_reason(reasons, text_or_none(recommendations.get("generated_at_utc")) == db_generated_at, "recommendations_generated_at_mismatch")
    append_reason(reasons, text_or_none(portfolio.get("generated_at_utc")) == db_generated_at, "portfolio_generated_at_mismatch")

    append_reason(reasons, admin_refresh_policy.get("healthy") is True, "admin_refresh_policy_not_healthy")
    append_reason(reasons, admin_canonical_policy.get("allowed") is True, "admin_canonical_serving_policy_blocked")
    append_reason(reasons, text_or_none(admin_canonical_policy.get("validation_status")) == db_validation, "admin_validation_status_mismatch")
    append_reason(reasons, text_or_none(admin_canonical_policy.get("snapshot_publication_id")) == db_snapshot_pub, "admin_snapshot_publication_id_mismatch")
    append_reason(reasons, text_or_none(admin_canonical_policy.get("quote_publication_id")) == db_quote_pub, "admin_quote_publication_id_mismatch")
    append_reason(reasons, text_or_none(admin_canonical_policy.get("quote_binding_status")) == db_quote_binding, "admin_quote_binding_status_mismatch")
    append_reason(reasons, text_or_none(as_record(admin_canonical_policy.get("runIds")).get("snapshot_run_id")) == db_run_id, "admin_snapshot_run_id_mismatch")
    append_reason(reasons, text_or_none(admin_serving_bundle.get("runId")) == db_run_id, "admin_serving_bundle_run_id_mismatch")

    result = {
      "status": "pass" if not reasons else "fail",
      "reasons": reasons,
      "expected_active_publication": {
        "run_id": db_run_id,
        "generated_at_utc": db_generated_at,
        "validation_status": db_validation,
        "snapshot_publication_id": db_snapshot_pub,
        "quote_publication_id": db_quote_pub,
        "quote_binding_status": db_quote_binding,
      },
      "observed": {
        "recommendations": {
          "run_id": text_or_none(recommendations.get("run_id")),
          "generated_at_utc": text_or_none(recommendations.get("generated_at_utc")),
          "validation_status": text_or_none(recommendations.get("validation_status")),
          "snapshot_publication_id": text_or_none(recommendations.get("snapshot_publication_id")),
          "quote_publication_id": text_or_none(recommendations.get("quote_publication_id")),
          "quote_binding_status": text_or_none(recommendations.get("quote_binding_status")),
          "blocked": rec_blocked,
          "stale": rec_stale,
        },
        "portfolio": {
          "run_id": text_or_none(portfolio.get("run_id")),
          "generated_at_utc": text_or_none(portfolio.get("generated_at_utc")),
          "validation_status": text_or_none(portfolio.get("validation_status")),
          "snapshot_publication_id": text_or_none(portfolio.get("snapshot_publication_id")),
          "quote_publication_id": text_or_none(portfolio.get("quote_publication_id")),
          "quote_binding_status": text_or_none(portfolio.get("quote_binding_status")),
          "blocked": port_blocked,
          "stale": port_stale,
        },
        "admin": {
          "refresh_policy_healthy": admin_refresh_policy.get("healthy"),
          "serving_policy_allowed": admin_canonical_policy.get("allowed"),
          "snapshot_run_id": text_or_none(as_record(admin_canonical_policy.get("runIds")).get("snapshot_run_id")),
          "serving_bundle_run_id": text_or_none(admin_serving_bundle.get("runId")),
          "validation_status": text_or_none(admin_canonical_policy.get("validation_status")),
          "snapshot_publication_id": text_or_none(admin_canonical_policy.get("snapshot_publication_id")),
          "quote_publication_id": text_or_none(admin_canonical_policy.get("quote_publication_id")),
          "quote_binding_status": text_or_none(admin_canonical_policy.get("quote_binding_status")),
        },
      },
    }

    sys.stdout.write(json.dumps(result, indent=2) + "\n")
    return 0 if not reasons else 1


if __name__ == "__main__":
    raise SystemExit(main())
