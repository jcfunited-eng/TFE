#!/usr/bin/env python3
"""
Freeze a deterministic full-universe replay dataset for policy learning/evaluation.

Source universe:
- uf_snapshot.ses.json envelope rows (ticker + asset_type), with optional
  SES envelope decrypt only.

Output:
- single JSON file with:
  - generated_at_utc
  - years
  - source_snapshot_path
  - symbols: {SYMBOL: {asset_type, ts_ms, close}}
  - spy: {ts_ms, close}
  - errors: [{symbol, error}]

Determinism:
- symbols are deduplicated and sorted before fetch.
- payload is emitted with sorted symbol keys.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

from aws_root_key_provider import AwsSecretsRootKeyProvider
from ses_core import Envelope
from tfe_market_data_service import HistoryRequest, Timespan
from tfe_ses_core_adapter import TenantIdentity, decrypt_blob, initialize_ses_core_for_env, make_domain
from unified_market_data_service import get_unified_market_data


DEFAULT_YEARS = 5
DEFAULT_SNAPSHOT = Path("uf_snapshot.ses.json")
DEFAULT_SAVE_EVERY = 25
SES_PURPOSE_PREFIX = "tfe-web"
SES_PURPOSE_SUFFIX = "uf-snapshot"
SES_ACTOR_ID = "web-snapshot-pipeline"
TENANT_ID = "tenant-tao"
TENANT_DISPLAY_NAME = "Tao Tenant"


def _now_utc_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


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


def _load_rows_from_envelope(snapshot_path: Path) -> List[Dict[str, Any]]:
    with snapshot_path.open("r", encoding="utf-8") as f:
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


def _load_snapshot_symbols(snapshot_path: Path) -> List[Tuple[str, str]]:
    if not snapshot_path.exists():
        raise FileNotFoundError(f"Snapshot file not found: {snapshot_path}")

    payload_rows = _load_rows_from_envelope(snapshot_path)

    pairs: List[Tuple[str, str]] = []
    seen = set()

    for row in payload_rows:
        if not isinstance(row, dict):
            continue
        raw_symbol = str(row.get("ticker", "")).strip().upper()
        if not raw_symbol:
            continue
        raw_asset = str(row.get("asset_type", "unknown")).strip().lower()
        key = (raw_symbol, raw_asset)
        if key in seen:
            continue
        seen.add(key)
        pairs.append(key)

    pairs.sort(key=lambda x: (x[0], x[1]))
    return pairs


def _bars_to_series_payload(bars: List[Any]) -> Dict[str, List[float]]:
    ts: List[int] = []
    close: List[float] = []

    for bar in bars:
        try:
            t_val = int(bar.timestamp.timestamp() * 1000)
            c_val = float(bar.close)
            if c_val <= 0.0:
                continue
        except Exception:
            continue

        ts.append(t_val)
        close.append(c_val)

    return {"ts_ms": ts, "close": close}


def _fetch_history_series(symbol: str, years: int) -> Dict[str, List[float]]:
    client = get_unified_market_data()

    end = datetime.utcnow()
    start = end - timedelta(days=int(years) * 365)

    req = HistoryRequest(
        symbol=symbol,
        timespan=Timespan.DAY,
        multiplier=1,
        start=start,
        end=end,
        adjusted=True,
        limit=None,
    )

    result = client.get_history(req)
    bars = getattr(result, "bars", []) or []
    bars_sorted = sorted(bars, key=lambda b: b.timestamp)

    return _bars_to_series_payload(bars_sorted)


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2))
    tmp_path.replace(path)


def _build_payload_template(years: int, snapshot_path: Path) -> Dict[str, Any]:
    return {
        "generated_at_utc": _now_utc_iso(),
        "years": int(years),
        "source_snapshot_path": str(snapshot_path),
        "symbols": {},
        "spy": {},
        "errors": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze deterministic full-universe dataset from uf_snapshot symbols.")
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS)
    parser.add_argument("--snapshot", type=str, default=str(DEFAULT_SNAPSHOT))
    parser.add_argument("--output", type=str, required=True)
    parser.add_argument("--save-every", type=int, default=DEFAULT_SAVE_EVERY)
    parser.add_argument("--max-symbols", type=int, default=0)
    args = parser.parse_args()

    years = int(args.years)
    snapshot_path = Path(args.snapshot)
    output_path = Path(args.output)
    save_every = max(1, int(args.save_every))
    max_symbols = int(args.max_symbols)

    symbol_pairs = _load_snapshot_symbols(snapshot_path)
    if max_symbols > 0:
        symbol_pairs = symbol_pairs[:max_symbols]

    payload = _build_payload_template(years=years, snapshot_path=snapshot_path)

    total = len(symbol_pairs)
    for idx, (symbol, asset_type) in enumerate(symbol_pairs, start=1):
        print(f"[{idx}/{total}] fetch {symbol} ({asset_type})")
        try:
            series = _fetch_history_series(symbol=symbol, years=years)
            payload["symbols"][symbol] = {
                "asset_type": asset_type,
                "ts_ms": series["ts_ms"],
                "close": series["close"],
            }
        except Exception as exc:
            payload["errors"].append(
                {
                    "symbol": symbol,
                    "asset_type": asset_type,
                    "error": str(exc),
                }
            )
            payload["symbols"][symbol] = {
                "asset_type": asset_type,
                "ts_ms": [],
                "close": [],
            }

        if idx == 1 or (idx % save_every == 0):
            payload["generated_at_utc"] = _now_utc_iso()
            payload["symbols"] = dict(sorted(payload["symbols"].items(), key=lambda item: item[0]))
            _write_json(output_path, payload)

    print("[SPY] fetch benchmark")
    try:
        payload["spy"] = _fetch_history_series(symbol="SPY", years=years)
    except Exception as exc:
        payload["errors"].append({"symbol": "SPY", "asset_type": "index", "error": str(exc)})
        payload["spy"] = {"ts_ms": [], "close": []}

    payload["generated_at_utc"] = _now_utc_iso()
    payload["symbols"] = dict(sorted(payload["symbols"].items(), key=lambda item: item[0]))
    _write_json(output_path, payload)

    print(output_path)
    print(f"symbols={len(payload['symbols'])} errors={len(payload['errors'])}")


if __name__ == "__main__":
    main()
