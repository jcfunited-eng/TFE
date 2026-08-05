#!/usr/bin/env python3
"""Apply and verify Guala's exact external retention authorities."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
from pathlib import Path
from typing import Any, Callable, Sequence


class ExternalRetentionError(RuntimeError):
    """The reviewed external retention policy is absent or changed."""


def _reject_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ExternalRetentionError(
                f"duplicate JSON key in retention authority: {key}"
            )
        result[key] = value
    return result


def _strict_json(raw: str, *, description: str) -> Any:
    try:
        return json.loads(
            raw,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON constant {value}")
            ),
        )
    except (json.JSONDecodeError, ValueError) as error:
        raise ExternalRetentionError(
            f"{description} is not strict JSON: {error}"
        ) from error


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _positive_integer(value: object, description: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
    ):
        raise ExternalRetentionError(
            f"{description} must be a positive integer"
        )
    return value


def load_required_s3_rules(path: Path) -> tuple[dict[str, Any], ...]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ExternalRetentionError(
            f"reviewed S3 lifecycle cannot be read: {error}"
        ) from error
    value = _strict_json(raw, description="reviewed S3 lifecycle")
    if not isinstance(value, dict) or set(value) != {"Rules"}:
        raise ExternalRetentionError(
            "reviewed S3 lifecycle must contain exactly Rules"
        )
    rules = value["Rules"]
    if not isinstance(rules, list) or not rules:
        raise ExternalRetentionError(
            "reviewed S3 lifecycle Rules must be a non-empty array"
        )
    required: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for rule in rules:
        if (
            not isinstance(rule, dict)
            or not isinstance(rule.get("ID"), str)
            or not rule["ID"]
            or rule.get("Status") != "Enabled"
            or not isinstance(rule.get("Filter"), dict)
        ):
            raise ExternalRetentionError(
                "reviewed S3 lifecycle rule identity, status, or filter "
                "is invalid"
            )
        identifier = rule["ID"]
        if identifier in identifiers:
            raise ExternalRetentionError(
                f"duplicate reviewed S3 lifecycle rule ID: {identifier}"
            )
        identifiers.add(identifier)
        finite_authority = False
        expiration = rule.get("Expiration")
        if expiration is not None:
            if not isinstance(expiration, dict) or set(expiration) != {"Days"}:
                raise ExternalRetentionError(
                    f"reviewed rule {identifier} has invalid Expiration"
                )
            _positive_integer(
                expiration["Days"],
                f"reviewed rule {identifier} expiration days",
            )
            finite_authority = True
        noncurrent = rule.get("NoncurrentVersionExpiration")
        if noncurrent is not None:
            if (
                not isinstance(noncurrent, dict)
                or set(noncurrent) != {"NoncurrentDays"}
            ):
                raise ExternalRetentionError(
                    f"reviewed rule {identifier} has invalid "
                    "NoncurrentVersionExpiration"
                )
            _positive_integer(
                noncurrent["NoncurrentDays"],
                f"reviewed rule {identifier} noncurrent days",
            )
            finite_authority = True
        multipart = rule.get("AbortIncompleteMultipartUpload")
        if multipart is not None:
            if (
                not isinstance(multipart, dict)
                or set(multipart) != {"DaysAfterInitiation"}
            ):
                raise ExternalRetentionError(
                    f"reviewed rule {identifier} has invalid "
                    "AbortIncompleteMultipartUpload"
                )
            _positive_integer(
                multipart["DaysAfterInitiation"],
                f"reviewed rule {identifier} multipart days",
            )
            finite_authority = True
        allowed = {
            "ID",
            "Filter",
            "Status",
            "Expiration",
            "NoncurrentVersionExpiration",
            "AbortIncompleteMultipartUpload",
        }
        if set(rule) - allowed or not finite_authority:
            raise ExternalRetentionError(
                f"reviewed rule {identifier} is not an exact finite "
                "retention authority"
            )
        required.append(copy.deepcopy(rule))
    return tuple(required)


def merge_required_s3_rules(
    current_rules: Sequence[dict[str, Any]],
    required_rules: Sequence[dict[str, Any]],
) -> tuple[dict[str, Any], ...]:
    if not isinstance(current_rules, (list, tuple)):
        raise ExternalRetentionError(
            "current S3 lifecycle rules are not an array"
        )
    current_ids: set[str] = set()
    retained: list[dict[str, Any]] = []
    required_ids = {rule["ID"] for rule in required_rules}
    for rule in current_rules:
        if (
            not isinstance(rule, dict)
            or not isinstance(rule.get("ID"), str)
            or not rule["ID"]
        ):
            raise ExternalRetentionError(
                "current S3 lifecycle contains an unidentified rule"
            )
        identifier = rule["ID"]
        if identifier in current_ids:
            raise ExternalRetentionError(
                f"current S3 lifecycle duplicates rule ID: {identifier}"
            )
        current_ids.add(identifier)
        if identifier not in required_ids:
            retained.append(copy.deepcopy(rule))
    return tuple([*retained, *copy.deepcopy(list(required_rules))])


RunCLI = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


def _default_run(arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(arguments),
        check=False,
        capture_output=True,
        text=True,
    )


def _aws_json(
    arguments: Sequence[str],
    *,
    run: RunCLI,
    description: str,
    absent_is_empty: bool = False,
) -> Any:
    completed = run(arguments)
    if completed.returncode != 0:
        diagnostic = (completed.stderr or completed.stdout or "").strip()
        if absent_is_empty and (
            "NoSuchLifecycleConfiguration" in diagnostic
            or "NoSuchConfiguration" in diagnostic
        ):
            return []
        raise ExternalRetentionError(
            f"{description} failed: {diagnostic or completed.returncode}"
        )
    return _strict_json(
        completed.stdout,
        description=f"{description} response",
    )


def _aws_mutation(
    arguments: Sequence[str],
    *,
    run: RunCLI,
    description: str,
) -> None:
    completed = run(arguments)
    if completed.returncode != 0:
        diagnostic = (completed.stderr or completed.stdout or "").strip()
        raise ExternalRetentionError(
            f"{description} failed: {diagnostic or completed.returncode}"
        )


def enforce_external_retention(
    *,
    region: str,
    log_group: str,
    log_retention_days: int,
    bucket: str,
    s3_policy: Path,
    run: RunCLI = _default_run,
) -> dict[str, Any]:
    if not all(
        isinstance(value, str) and value and value == value.strip()
        for value in (region, log_group, bucket)
    ):
        raise ExternalRetentionError(
            "region, log group, and bucket must be explicit"
        )
    retention_days = _positive_integer(
        log_retention_days,
        "CloudWatch retention days",
    )
    required_rules = load_required_s3_rules(s3_policy)

    _aws_mutation(
        (
            "aws",
            "logs",
            "put-retention-policy",
            "--region",
            region,
            "--log-group-name",
            log_group,
            "--retention-in-days",
            str(retention_days),
        ),
        run=run,
        description="CloudWatch retention publication",
    )
    log_groups = _aws_json(
        (
            "aws",
            "logs",
            "describe-log-groups",
            "--region",
            region,
            "--log-group-name-prefix",
            log_group,
            "--output",
            "json",
        ),
        run=run,
        description="CloudWatch retention readback",
    )
    if not isinstance(log_groups, dict):
        raise ExternalRetentionError(
            "CloudWatch retention readback is not an object"
        )
    exact_groups = [
        item
        for item in log_groups.get("logGroups", [])
        if isinstance(item, dict)
        and item.get("logGroupName") == log_group
    ]
    if (
        len(exact_groups) != 1
        or exact_groups[0].get("retentionInDays") != retention_days
    ):
        raise ExternalRetentionError(
            "CloudWatch log group retention differs from reviewed authority"
        )

    current_rules = _aws_json(
        (
            "aws",
            "s3api",
            "get-bucket-lifecycle-configuration",
            "--region",
            region,
            "--bucket",
            bucket,
            "--query",
            "Rules",
            "--output",
            "json",
        ),
        run=run,
        description="S3 lifecycle discovery",
        absent_is_empty=True,
    )
    merged_rules = merge_required_s3_rules(
        current_rules,
        required_rules,
    )
    policy_argument = _canonical_json({"Rules": list(merged_rules)})
    _aws_mutation(
        (
            "aws",
            "s3api",
            "put-bucket-lifecycle-configuration",
            "--region",
            region,
            "--bucket",
            bucket,
            "--lifecycle-configuration",
            policy_argument,
        ),
        run=run,
        description="S3 lifecycle publication",
    )
    readback = _aws_json(
        (
            "aws",
            "s3api",
            "get-bucket-lifecycle-configuration",
            "--region",
            region,
            "--bucket",
            bucket,
            "--query",
            "Rules",
            "--output",
            "json",
        ),
        run=run,
        description="S3 lifecycle readback",
    )
    if (
        not isinstance(readback, list)
        or _canonical_json(readback)
        != _canonical_json(list(merged_rules))
    ):
        raise ExternalRetentionError(
            "S3 lifecycle readback differs from the exact merged authority"
        )
    return {
        "bucket": bucket,
        "cloudwatch_log_group": log_group,
        "cloudwatch_retention_days": retention_days,
        "required_s3_rule_ids": [
            rule["ID"] for rule in required_rules
        ],
        "retained_unrelated_s3_rule_ids": [
            rule["ID"]
            for rule in merged_rules
            if rule["ID"] not in {
                required["ID"] for required in required_rules
            }
        ],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", required=True)
    parser.add_argument("--log-group", required=True)
    parser.add_argument("--log-retention-days", required=True, type=int)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--s3-policy", required=True, type=Path)
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    try:
        result = enforce_external_retention(
            region=arguments.region,
            log_group=arguments.log_group,
            log_retention_days=arguments.log_retention_days,
            bucket=arguments.bucket,
            s3_policy=arguments.s3_policy,
        )
    except ExternalRetentionError as error:
        print(f"ERROR: {error}", flush=True)
        return 1
    print(_canonical_json(result), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
