#!/usr/bin/env python3
"""
ses_web_blob.py

SES-Core envelope bridge for Next.js web routes.

Encrypt mode:
  - Reads plaintext JSON from --input-path
  - Wraps it in an SES-Core envelope
  - Writes envelope JSON to --output-path (0600)

Decrypt mode:
  - Reads envelope JSON from --input-path
  - Decrypts it via SES-Core
  - Writes plaintext JSON to --output-path
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ses_core import Envelope  # type: ignore
from tfe_ses_core_adapter import (  # type: ignore
    TenantIdentity,
    decrypt_blob,
    encrypt_blob,
    initialize_ses_core_for_env,
    make_domain,
    record_custody_event,
)
from aws_root_key_provider import AwsSecretsRootKeyProvider  # type: ignore

TENANT_ID = "tenant-tao"
TENANT_DISPLAY_NAME = "Tao Tenant"
PURPOSE_PREFIX = "tfe-web"
PRIVATE_FILE_MODE = 0o600


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_private_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, PRIVATE_FILE_MODE)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    try:
        os.chmod(path, PRIVATE_FILE_MODE)
    except Exception:
        # Best effort for restricted filesystems.
        pass


def _make_tenant(environment: str) -> TenantIdentity:
    return TenantIdentity(
        tenant_id=TENANT_ID,
        display_name=TENANT_DISPLAY_NAME,
        environment=environment,
        attributes={},
    )


def _initialize_ctx(environment: str, region: str):
    env_flag = str(environment).lower()
    root_key_provider = None

    if env_flag == "aws":
        root_key_provider = AwsSecretsRootKeyProvider.from_env()

    return initialize_ses_core_for_env(
        environment=environment,
        region=region,
        purpose_prefix=PURPOSE_PREFIX,
        root_key_provider=root_key_provider,
    )


def _parse_payload_json(path: Path) -> Any:
    raw = _read_text(path)
    return json.loads(raw)


def _to_json_safe(value: Any) -> Any:
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        return None

    if isinstance(value, dict):
        return {str(k): _to_json_safe(v) for k, v in value.items()}

    if isinstance(value, list):
        return [_to_json_safe(v) for v in value]

    return value


def _encrypt(args: argparse.Namespace) -> None:
    environment = str(args.environment)
    region = str(args.region)
    purpose_suffix = str(args.purpose_suffix)
    actor_id = str(args.actor_id)
    asset_id = str(args.asset_id)
    input_path = Path(str(args.input_path)).resolve()
    output_path = Path(str(args.output_path)).resolve()

    value = _parse_payload_json(input_path)
    payload: Mapping[str, Any] = {
        "kind": "json",
        "value": _to_json_safe(value),
    }

    ctx = _initialize_ctx(environment=environment, region=region)
    tenant = _make_tenant(environment=environment)
    domain = make_domain(ctx=ctx, purpose_suffix=purpose_suffix, version="v1")

    envelope = encrypt_blob(
        ctx=ctx,
        tenant=tenant,
        domain=domain,
        payload=payload,
        actor_id=actor_id,
    )

    _write_private_text(output_path, envelope.to_json())

    record_custody_event(
        ctx=ctx,
        tenant_id=tenant.tenant_id,
        actor_id=actor_id,
        asset_id=asset_id,
        action="tfe.web.encrypt",
        payload={
            "purpose": domain.purpose,
            "version": domain.version,
            "output_path": str(output_path),
        },
    )


def _decrypt(args: argparse.Namespace) -> None:
    environment = str(args.environment)
    region = str(args.region)
    purpose_suffix = str(args.purpose_suffix)
    actor_id = str(args.actor_id)
    asset_id = str(args.asset_id)
    input_path = Path(str(args.input_path)).resolve()
    output_path = Path(str(args.output_path)).resolve()

    envelope_raw = _read_text(input_path)
    envelope = Envelope.from_json(envelope_raw)

    ctx = _initialize_ctx(environment=environment, region=region)
    tenant = _make_tenant(environment=environment)
    domain = make_domain(ctx=ctx, purpose_suffix=purpose_suffix, version="v1")

    payload = decrypt_blob(
        ctx=ctx,
        tenant=tenant,
        domain=domain,
        envelope=envelope,
        actor_id=actor_id,
    )

    if isinstance(payload, dict) and "value" in payload:
        value = payload["value"]
    else:
        value = payload

    safe_value = _to_json_safe(value)
    _write_private_text(output_path, json.dumps(safe_value, ensure_ascii=False, separators=(",", ":")))

    record_custody_event(
        ctx=ctx,
        tenant_id=tenant.tenant_id,
        actor_id=actor_id,
        asset_id=asset_id,
        action="tfe.web.decrypt",
        payload={
            "purpose": domain.purpose,
            "version": domain.version,
            "input_path": str(input_path),
        },
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SES-Core bridge for web UF data paths")
    parser.add_argument("mode", choices=["encrypt", "decrypt"], help="Operation mode")
    parser.add_argument("--purpose-suffix", required=True, help="SES domain purpose suffix")
    parser.add_argument("--actor-id", required=True, help="Actor id for associated metadata")
    parser.add_argument("--asset-id", required=True, help="Asset id for custody record")
    parser.add_argument("--input-path", required=True, help="Input file path")
    parser.add_argument("--output-path", required=True, help="Output file path")
    parser.add_argument("--environment", default=os.environ.get("TFE_ENV", "dev"), help="SES environment")
    parser.add_argument("--region", default=os.environ.get("TFE_REGION", "local"), help="SES region")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    try:
        if args.mode == "encrypt":
            _encrypt(args)
        else:
            _decrypt(args)
        return 0
    except Exception as exc:
        print(f"[ses_web_blob] ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
