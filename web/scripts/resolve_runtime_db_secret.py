#!/usr/bin/env python3

import json
import os
import subprocess
import sys


def fetch_secret_via_boto3(secret_id: str, region: str) -> str:
    import boto3  # type: ignore

    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_id)
    secret_string = response.get("SecretString")
    if not isinstance(secret_string, str) or len(secret_string) == 0:
      raise RuntimeError("secret_string_missing")
    return secret_string


def fetch_secret_via_aws_cli(secret_id: str, region: str) -> str:
    completed = subprocess.run(
        [
            "aws",
            "secretsmanager",
            "get-secret-value",
            "--secret-id",
            secret_id,
            "--region",
            region,
            "--query",
            "SecretString",
            "--output",
            "text",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "aws_cli_secret_fetch_failed").strip())
    secret_string = completed.stdout
    if not isinstance(secret_string, str) or len(secret_string.strip()) == 0:
        raise RuntimeError("secret_string_missing")
    return secret_string.strip()


def main() -> int:
    secret_id = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TFE_RUNTIME_DB_SECRET_ARN", "")).strip()
    if not secret_id:
        print("missing_secret_arn", file=sys.stderr)
        return 1

    region = (
        os.environ.get("AWS_REGION", "").strip()
        or os.environ.get("TFE_REGION", "").strip()
        or "us-east-1"
    )

    try:
        secret_string = fetch_secret_via_boto3(secret_id, region)
    except ModuleNotFoundError:
        try:
            secret_string = fetch_secret_via_aws_cli(secret_id, region)
        except Exception as exc:  # pragma: no cover - surfaced directly
            print(f"secret_fetch_failed:{exc}", file=sys.stderr)
            return 1
    except Exception as exc:  # pragma: no cover - surfaced directly
        print(f"secret_fetch_failed:{exc}", file=sys.stderr)
        return 1

    try:
        payload = json.loads(secret_string)
    except json.JSONDecodeError as exc:
        print(f"secret_json_invalid:{exc}", file=sys.stderr)
        return 1

    username = payload.get("username")
    password = payload.get("password")
    if not isinstance(username, str) or len(username) == 0:
        print("secret_username_missing", file=sys.stderr)
        return 1
    if not isinstance(password, str) or len(password) == 0:
        print("secret_password_missing", file=sys.stderr)
        return 1

    print(json.dumps({"username": username, "password": password}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
