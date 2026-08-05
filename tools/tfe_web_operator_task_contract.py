#!/usr/bin/env python3
"""Apply and verify the TFE web operator-listening ECS contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


SECRET_NAMES = ("GUALA_OPERATOR_API_KEY", "CLERK_SECRET_KEY")
ENVIRONMENT_VALUES = (
    "GUALA_OPERATOR_API_ORIGIN",
    "GUALA_SELF_BODY_PORT_ID",
    "TFE_PUBLIC_BASE_URL",
)
SELF_BODY_PORT_ID = "guala.embodiment.w1"
_SECRET_ARN = re.compile(
    r"^arn:aws:secretsmanager:[a-z0-9-]+:[0-9]{12}:secret:"
    r"[A-Za-z0-9/_+=.@-]+$"
)


class OperatorTaskContractError(ValueError):
    """The proposed task definition is not safe for operator listening."""


def _origin(value: str, name: str) -> str:
    raw = str(value or "").strip()
    parsed = urlsplit(raw)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
        or parsed.hostname in {"0.0.0.0", "::", "[::]"}
    ):
        raise OperatorTaskContractError(
            f"{name} must be an exact https origin"
        )
    return f"https://{parsed.netloc}"


def _secret_arn(value: str, name: str) -> str:
    raw = str(value or "").strip()
    if not _SECRET_ARN.fullmatch(raw):
        raise OperatorTaskContractError(
            f"{name} must be a Secrets Manager ARN"
        )
    return raw


def _target_container(task_definition: dict[str, Any]) -> dict[str, Any]:
    containers = task_definition.get("containerDefinitions")
    if not isinstance(containers, list):
        raise OperatorTaskContractError(
            "task definition has no containerDefinitions"
        )
    matches = [
        item
        for item in containers
        if isinstance(item, dict) and item.get("name") == "tfe-web"
    ]
    if len(matches) != 1:
        raise OperatorTaskContractError(
            "task definition must contain exactly one tfe-web container"
        )
    return matches[0]


def _unique_named_records(
    value: Any,
    field_name: str,
) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise OperatorTaskContractError(f"{field_name} must be a list")
    records: list[dict[str, Any]] = []
    names: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            raise OperatorTaskContractError(
                f"{field_name} contains a non-object record"
            )
        name = item.get("name")
        if not isinstance(name, str) or not name:
            raise OperatorTaskContractError(
                f"{field_name} contains an invalid name"
            )
        if name in names:
            raise OperatorTaskContractError(
                f"{field_name} contains duplicate name {name}"
            )
        names.add(name)
        records.append(dict(item))
    return records


def apply_operator_contract(
    task_definition: dict[str, Any],
    *,
    operator_secret_arn: str,
    clerk_secret_arn: str,
    operator_api_origin: str,
    public_base_url: str,
) -> dict[str, Any]:
    if not isinstance(task_definition, dict):
        raise OperatorTaskContractError(
            "task definition must be a JSON object"
        )
    operator_secret = _secret_arn(
        operator_secret_arn,
        "GUALA operator secret",
    )
    clerk_secret = _secret_arn(clerk_secret_arn, "Clerk secret")
    operator_origin = _origin(
        operator_api_origin,
        "GUALA_OPERATOR_API_ORIGIN",
    )
    public_origin = _origin(public_base_url, "TFE_PUBLIC_BASE_URL")

    result = json.loads(json.dumps(task_definition))
    container = _target_container(result)
    environment = _unique_named_records(
        container.get("environment"),
        "environment",
    )
    secrets = _unique_named_records(container.get("secrets"), "secrets")

    protected_names = set(SECRET_NAMES) | set(ENVIRONMENT_VALUES)
    environment = [
        item
        for item in environment
        if item["name"] not in protected_names
    ]
    secrets = [
        item
        for item in secrets
        if item["name"] not in protected_names
    ]
    environment.extend(
        [
            {
                "name": "GUALA_OPERATOR_API_ORIGIN",
                "value": operator_origin,
            },
            {
                "name": "GUALA_SELF_BODY_PORT_ID",
                "value": SELF_BODY_PORT_ID,
            },
            {
                "name": "TFE_PUBLIC_BASE_URL",
                "value": public_origin,
            },
        ]
    )
    secrets.extend(
        [
            {
                "name": "GUALA_OPERATOR_API_KEY",
                "valueFrom": operator_secret,
            },
            {
                "name": "CLERK_SECRET_KEY",
                "valueFrom": clerk_secret,
            },
        ]
    )
    container["environment"] = sorted(
        environment,
        key=lambda item: item["name"],
    )
    container["secrets"] = sorted(
        secrets,
        key=lambda item: item["name"],
    )

    verify_operator_contract(
        result,
        operator_secret_arn=operator_secret,
        clerk_secret_arn=clerk_secret,
        operator_api_origin=operator_origin,
        public_base_url=public_origin,
    )
    return result


def verify_operator_contract(
    task_definition: dict[str, Any],
    *,
    operator_secret_arn: str,
    clerk_secret_arn: str,
    operator_api_origin: str,
    public_base_url: str,
) -> None:
    expected_secrets = {
        "GUALA_OPERATOR_API_KEY": _secret_arn(
            operator_secret_arn,
            "GUALA operator secret",
        ),
        "CLERK_SECRET_KEY": _secret_arn(
            clerk_secret_arn,
            "Clerk secret",
        ),
    }
    expected_environment = {
        "GUALA_OPERATOR_API_ORIGIN": _origin(
            operator_api_origin,
            "GUALA_OPERATOR_API_ORIGIN",
        ),
        "GUALA_SELF_BODY_PORT_ID": SELF_BODY_PORT_ID,
        "TFE_PUBLIC_BASE_URL": _origin(
            public_base_url,
            "TFE_PUBLIC_BASE_URL",
        ),
    }
    container = _target_container(task_definition)
    environment = _unique_named_records(
        container.get("environment"),
        "environment",
    )
    secrets = _unique_named_records(container.get("secrets"), "secrets")
    environment_by_name = {
        item["name"]: item
        for item in environment
    }
    secrets_by_name = {
        item["name"]: item
        for item in secrets
    }

    for name, expected in expected_environment.items():
        record = environment_by_name.get(name)
        if record != {"name": name, "value": expected}:
            raise OperatorTaskContractError(
                f"{name} environment mapping changed"
            )
        if name in secrets_by_name:
            raise OperatorTaskContractError(
                f"{name} must not be an ECS secret mapping"
            )

    for name, expected in expected_secrets.items():
        if name in environment_by_name:
            raise OperatorTaskContractError(
                f"{name} must not be plaintext environment"
            )
        record = secrets_by_name.get(name)
        if record != {"name": name, "valueFrom": expected}:
            raise OperatorTaskContractError(
                f"{name} ECS secret mapping changed"
            )


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise OperatorTaskContractError(
            f"task definition is unreadable: {path}"
        ) from error
    if not isinstance(value, dict):
        raise OperatorTaskContractError(
            "task definition must be a JSON object"
        )
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("apply", "verify"), required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--operator-secret-arn", required=True)
    parser.add_argument("--clerk-secret-arn", required=True)
    parser.add_argument("--operator-api-origin", required=True)
    parser.add_argument("--public-base-url", required=True)
    args = parser.parse_args()

    task_definition = _load(args.input)
    common = {
        "operator_secret_arn": args.operator_secret_arn,
        "clerk_secret_arn": args.clerk_secret_arn,
        "operator_api_origin": args.operator_api_origin,
        "public_base_url": args.public_base_url,
    }
    if args.mode == "verify":
        if args.output is not None:
            raise OperatorTaskContractError(
                "--output is forbidden in verify mode"
            )
        verify_operator_contract(task_definition, **common)
        return 0

    if args.output is None:
        raise OperatorTaskContractError(
            "--output is required in apply mode"
        )
    result = apply_operator_contract(task_definition, **common)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
