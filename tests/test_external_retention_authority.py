from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path
from typing import Any, Sequence

import pytest

from tools.enforce_guala_external_retention import (
    ExternalRetentionError,
    enforce_external_retention,
    load_required_s3_rules,
)


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "deploy" / "aws" / "guala-state-lifecycle.json"
DEPLOY = ROOT / "tools" / "deploy_dsf_ai.sh"


def _completed(
    arguments: Sequence[str],
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        list(arguments),
        returncode,
        stdout=stdout,
        stderr=stderr,
    )


class FakeAWS:
    def __init__(
        self,
        *,
        log_retention: int | None = None,
        s3_rules: list[dict[str, Any]] | None = None,
    ) -> None:
        self.log_retention = log_retention
        self.s3_rules = copy.deepcopy(s3_rules)
        self.calls: list[tuple[str, ...]] = []
        self.published_s3_rules: list[dict[str, Any]] | None = None
        self.ignore_log_publication = False
        self.drift_s3_readback = False
        self.denied_operations: set[tuple[str, str]] = set()

    def __call__(
        self,
        arguments: Sequence[str],
    ) -> subprocess.CompletedProcess[str]:
        command = tuple(arguments)
        self.calls.append(command)
        operation = command[1:3]
        if operation in self.denied_operations:
            return _completed(
                command,
                returncode=254,
                stderr="AccessDeniedException",
            )

        if operation == ("logs", "put-retention-policy"):
            if not self.ignore_log_publication:
                value_index = command.index("--retention-in-days") + 1
                self.log_retention = int(command[value_index])
            return _completed(command)

        if operation == ("logs", "describe-log-groups"):
            groups = []
            if self.log_retention is not None:
                group_index = command.index(
                    "--log-group-name-prefix"
                ) + 1
                groups.append({
                    "logGroupName": command[group_index],
                    "retentionInDays": self.log_retention,
                })
            return _completed(
                command,
                stdout=json.dumps({"logGroups": groups}),
            )

        if operation == (
            "s3api",
            "get-bucket-lifecycle-configuration",
        ):
            if self.s3_rules is None:
                return _completed(
                    command,
                    returncode=255,
                    stderr="NoSuchLifecycleConfiguration",
                )
            rules = copy.deepcopy(self.s3_rules)
            if self.drift_s3_readback and self.published_s3_rules is not None:
                rules[0]["Status"] = "Disabled"
            return _completed(command, stdout=json.dumps(rules))

        if operation == (
            "s3api",
            "put-bucket-lifecycle-configuration",
        ):
            value_index = command.index(
                "--lifecycle-configuration"
            ) + 1
            published = json.loads(command[value_index])
            self.published_s3_rules = copy.deepcopy(published["Rules"])
            self.s3_rules = copy.deepcopy(published["Rules"])
            return _completed(command)

        raise AssertionError(f"unexpected command: {command}")


def _enforce(fake: FakeAWS) -> dict[str, Any]:
    return enforce_external_retention(
        region="us-east-1",
        log_group="/ecs/dsf-ai",
        log_retention_days=30,
        bucket="dsf-ai-site-backups",
        s3_policy=POLICY,
        run=fake,
    )


def test_absent_policies_are_created_and_read_back_exactly() -> None:
    fake = FakeAWS()

    receipt = _enforce(fake)

    required = list(load_required_s3_rules(POLICY))
    assert fake.log_retention == 30
    assert fake.published_s3_rules == required
    assert receipt["cloudwatch_retention_days"] == 30
    assert receipt["required_s3_rule_ids"] == [
        rule["ID"] for rule in required
    ]
    assert [call[1:3] for call in fake.calls] == [
        ("logs", "put-retention-policy"),
        ("logs", "describe-log-groups"),
        ("s3api", "get-bucket-lifecycle-configuration"),
        ("s3api", "put-bucket-lifecycle-configuration"),
        ("s3api", "get-bucket-lifecycle-configuration"),
    ]


def test_exact_existing_policies_are_still_read_back() -> None:
    required = list(load_required_s3_rules(POLICY))
    fake = FakeAWS(log_retention=30, s3_rules=required)

    receipt = _enforce(fake)

    assert fake.published_s3_rules == required
    assert receipt["retained_unrelated_s3_rule_ids"] == []
    assert sum(
        call[1:3] == ("logs", "describe-log-groups")
        for call in fake.calls
    ) == 1
    assert sum(
        call[1:3]
        == ("s3api", "get-bucket-lifecycle-configuration")
        for call in fake.calls
    ) == 2


@pytest.mark.parametrize(
    "document",
    [
        '{"Rules":[{"ID":"same","Filter":{},"Status":"Enabled",'
        '"Expiration":{"Days":1}},{"ID":"same","Filter":{},'
        '"Status":"Enabled","Expiration":{"Days":2}}]}',
        '{"Rules":[{"ID":"forever","Filter":{},"Status":"Enabled"}]}',
        '{"Rules":[{"ID":"float","Filter":{},"Status":"Enabled",'
        '"Expiration":{"Days":1.5}}]}',
        '{"Rules":[],"Rules":[]}',
    ],
)
def test_malformed_reviewed_policy_halts_before_aws(
    tmp_path: Path,
    document: str,
) -> None:
    policy = tmp_path / "malformed.json"
    policy.write_text(document, encoding="utf-8")
    fake = FakeAWS()

    with pytest.raises(ExternalRetentionError):
        enforce_external_retention(
            region="us-east-1",
            log_group="/ecs/dsf-ai",
            log_retention_days=30,
            bucket="dsf-ai-site-backups",
            s3_policy=policy,
            run=fake,
        )

    assert fake.calls == []


def test_cloudwatch_readback_drift_halts_before_s3_mutation() -> None:
    fake = FakeAWS()
    fake.ignore_log_publication = True

    with pytest.raises(
        ExternalRetentionError,
        match="CloudWatch log group retention differs",
    ):
        _enforce(fake)

    assert all(call[1] != "s3api" for call in fake.calls)


def test_s3_readback_drift_halts() -> None:
    fake = FakeAWS()
    fake.drift_s3_readback = True

    with pytest.raises(
        ExternalRetentionError,
        match="S3 lifecycle readback differs",
    ):
        _enforce(fake)


def test_missing_aws_authority_halts() -> None:
    fake = FakeAWS()
    fake.denied_operations.add(("logs", "put-retention-policy"))

    with pytest.raises(
        ExternalRetentionError,
        match="CloudWatch retention publication failed",
    ):
        _enforce(fake)

    assert len(fake.calls) == 1


def test_unrelated_lifecycle_rules_are_retained_exactly() -> None:
    unrelated = {
        "ID": "independent-retention-owner",
        "Filter": {"Prefix": "other-system/"},
        "Status": "Enabled",
        "Expiration": {"Days": 91},
    }
    stale_reviewed_rule = {
        "ID": "guala-abort-incomplete-multipart-1d",
        "Filter": {},
        "Status": "Enabled",
        "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 9},
    }
    fake = FakeAWS(
        log_retention=14,
        s3_rules=[unrelated, stale_reviewed_rule],
    )

    receipt = _enforce(fake)

    assert fake.published_s3_rules is not None
    assert fake.published_s3_rules[0] == unrelated
    assert fake.published_s3_rules[0] is not unrelated
    assert receipt["retained_unrelated_s3_rule_ids"] == [
        "independent-retention-owner"
    ]
    required = {
        rule["ID"]: rule for rule in load_required_s3_rules(POLICY)
    }
    published = {
        rule["ID"]: rule for rule in fake.published_s3_rules
    }
    assert published[
        "guala-abort-incomplete-multipart-1d"
    ] == required["guala-abort-incomplete-multipart-1d"]


def test_deploy_has_no_external_retention_mutation_authority() -> None:
    script = DEPLOY.read_text(encoding="utf-8")
    manifest = json.loads(
        (
            ROOT / "deploy" / "guala_release_manifest.json"
        ).read_text(encoding="utf-8")
    )
    build_control = next(
        category
        for category in manifest["categories"]
        if category["name"] == "build_control"
    )

    assert "enforce_guala_external_retention.py" not in script
    assert "put-retention-policy" not in script
    assert "put-bucket-lifecycle-configuration" not in script
    assert "deploy/aws/guala-state-lifecycle.json" not in build_control["files"]
    assert "tools/enforce_guala_external_retention.py" not in build_control["files"]
