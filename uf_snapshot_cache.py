"""
uf_snapshot_cache.py

Unified handler for:
- Loading UF snapshot from disk
- Filtering snapshot data
- Triggering full UF rebuild via rebuild_uf_snapshot.py
- Using unified market data service (Massive primary, Alpaca fallback)

This version:
- Removes Timespan (no longer valid)
- Uses only HistoryRequest
- Provides correct filtering for stock / etf / index / crypto
- Ensures compatibility with the corrected data layer
- Loads snapshot rows from SES envelope first (`uf_snapshot.ses.json`).
- No plaintext snapshot fallback path exists.
"""

from __future__ import annotations

import subprocess
import sys
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from ses_core import Envelope
from tfe_market_data_service import HistoryRequest
from tfe_market_data import get_unified_market_data
from tfe_ses_core_adapter import TenantIdentity, decrypt_blob, initialize_ses_core_for_env, make_domain
from aws_root_key_provider import AwsSecretsRootKeyProvider

SNAPSHOT_ENVELOPE_JSON = "uf_snapshot.ses.json"
SES_PURPOSE_PREFIX = "tfe-web"
SES_PURPOSE_SUFFIX = "uf-snapshot"
SES_ACTOR_ID = "web-snapshot-pipeline"
TENANT_ID = "tenant-tao"
TENANT_DISPLAY_NAME = "Tao Tenant"


def _init_web_ses_context() -> Tuple[Any, TenantIdentity]:
    environment = str(os.environ.get("TFE_ENV", "dev"))
    region = str(os.environ.get("TFE_REGION", os.environ.get("AWS_REGION", "local")))

    root_key_provider = None
    if environment.strip().lower() == "aws":
        root_key_provider = AwsSecretsRootKeyProvider.from_env()

    ctx = initialize_ses_core_for_env(
        environment=environment,
        region=region,
        purpose_prefix=SES_PURPOSE_PREFIX,
        root_key_provider=root_key_provider,
    )

    tenant = TenantIdentity(
        tenant_id=TENANT_ID,
        display_name=TENANT_DISPLAY_NAME,
        environment=environment,
        attributes={},
    )
    return ctx, tenant


def _load_snapshot_from_envelope() -> List[Dict[str, Any]]:
    if not os.path.exists(SNAPSHOT_ENVELOPE_JSON):
        return []

    try:
        with open(SNAPSHOT_ENVELOPE_JSON, "r", encoding="utf-8") as f:
            envelope_raw = f.read()

        envelope = Envelope.from_json(envelope_raw)
        ctx, tenant = _init_web_ses_context()
        domain = make_domain(ctx=ctx, purpose_suffix=SES_PURPOSE_SUFFIX, version="v1")
        payload = decrypt_blob(
            ctx=ctx,
            tenant=tenant,
            domain=domain,
            envelope=envelope,
            actor_id=SES_ACTOR_ID,
        )

        if isinstance(payload, dict):
            rows = payload.get("rows", [])
        elif isinstance(payload, list):
            rows = payload
        else:
            rows = []

        if not isinstance(rows, list):
            return []

        return [row for row in rows if isinstance(row, dict)]
    except Exception:
        return []


# -----------------------------------------------------------
# Load Snapshot
# -----------------------------------------------------------
def load_snapshot() -> List[Dict[str, Any]]:
    return _load_snapshot_from_envelope()


load_snapshot_raw = load_snapshot  # alias


# -----------------------------------------------------------
# Filtering
# -----------------------------------------------------------
def load_filtered_snapshot(
    min_price: float,
    max_price: float,
    asset_types: Tuple[str, ...],
) -> List[Dict[str, Any]]:
    rows = load_snapshot()
    out = []
    for r in rows:
        px = r.get("price")
        typ = r.get("asset_type")
        if px is None:
            continue
        if typ not in asset_types:
            continue
        if not (min_price <= px <= max_price):
            continue
        out.append(r)
    return out


def refresh_filtered_snapshot(asset_type, min_price: float, max_price: float):
    if isinstance(asset_type, str):
        asset_types = (asset_type,)
    else:
        asset_types = tuple(asset_type)
    return load_filtered_snapshot(min_price, max_price, asset_types)


# -----------------------------------------------------------
# Full Rebuild — calls external rebuild script
# -----------------------------------------------------------
def refresh_snapshot_full(asset_types: Tuple[str, ...] = ("stock", "etf")):
    print("[UF-SNAPSHOT] Calling rebuild script...")
    try:
        subprocess.run(
            [sys.executable, "rebuild_uf_snapshot.py"],
            check=True,
        )
    except Exception as exc:
        print(f"[UF-SNAPSHOT] rebuild script error: {exc}")


# -----------------------------------------------------------
# Price access for UI
# -----------------------------------------------------------
def get_last_price(symbol: str) -> Optional[float]:
    try:
        mds = get_unified_market_data()
        return mds.get_last_price(symbol)
    except Exception:
        return None
