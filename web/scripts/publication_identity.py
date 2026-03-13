#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict

PUBLICATION_SCHEMA_VERSION = "v1"
PUBLICATION_METADATA_KEYS = {
    "publication_schema_version",
    "publication_id",
    "refresh_run_id",
    "artifact_role",
    "artifact_digest_sha256",
    "source_snapshot_publication_id",
    "source_snapshot_digest_sha256",
    "source_snapshot_generated_at_utc",
    "source_snapshot",
    "publication_binding_status",
    "publication_binding_reason",
    "candidate_snapshot_publication_id",
    "candidate_snapshot_digest_sha256",
    "candidate_snapshot_generated_at_utc",
}


def _normalize_iso(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        from datetime import datetime, timezone

        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        return None


def _read_json(path: Path) -> Dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    normalized = raw.replace("NaN", "null").replace("Infinity", "null").replace("-null", "null")
    parsed = json.loads(normalized)
    if not isinstance(parsed, dict):
        raise RuntimeError(f"Expected JSON object at {path}.")
    return parsed


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _strip_publication_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for key, item in value.items():
            if key in PUBLICATION_METADATA_KEYS:
                continue
            out[key] = _strip_publication_metadata(item)
        return out
    if isinstance(value, list):
        return [_strip_publication_metadata(item) for item in value]
    return value


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _env_refresh_run_id() -> str | None:
    text = str(os.environ.get("TFE_REFRESH_RUN_ID", "")).strip()
    return text or None


def _derive_snapshot_metadata(snapshot_payload: Dict[str, Any]) -> Dict[str, Any]:
    generated_at_utc = _normalize_iso(snapshot_payload.get("generated_at_utc"))
    rows = snapshot_payload.get("rows") if isinstance(snapshot_payload.get("rows"), list) else []
    base_payload = {
        "generated_at_utc": generated_at_utc,
        "rows": rows,
    }
    artifact_digest = _canonical_sha256(base_payload)
    publication_id = str(snapshot_payload.get("publication_id") or "").strip() or f"snapshot_pub_v1_{artifact_digest[:24]}"
    refresh_run_id = str(snapshot_payload.get("refresh_run_id") or "").strip() or _env_refresh_run_id()
    return {
        "publication_schema_version": PUBLICATION_SCHEMA_VERSION,
        "publication_id": publication_id,
        "refresh_run_id": refresh_run_id,
        "artifact_role": "snapshot",
        "artifact_digest_sha256": artifact_digest,
        "generated_at_utc": generated_at_utc,
    }


def stamp_snapshot_artifact(snapshot_path: Path) -> Dict[str, Any]:
    snapshot_payload = _read_json(snapshot_path)
    metadata = _derive_snapshot_metadata(snapshot_payload)
    for key, value in metadata.items():
        snapshot_payload[key] = value
    _write_json(snapshot_path, snapshot_payload)
    return metadata


def _derive_quote_artifact_digest(quote_payload: Dict[str, Any]) -> str:
    stripped = _strip_publication_metadata(quote_payload)
    return _canonical_sha256(stripped)


def _quote_alignment_reason(
    source_snapshot_path_matches: bool,
    quote_generated_at_utc: str | None,
    snapshot_generated_at_utc: str | None,
) -> str:
    if not source_snapshot_path_matches:
        return "quote_source_snapshot_path_mismatch"
    if not quote_generated_at_utc:
        return "quote_generated_at_missing"
    if not snapshot_generated_at_utc:
        return "snapshot_generated_at_missing"
    if quote_generated_at_utc < snapshot_generated_at_utc:
        return "quote_generated_before_snapshot"
    return "aligned"


def stamp_quote_artifact(
    *,
    snapshot_path: Path,
    quote_path: Path,
    failures_path: Path | None = None,
    require_aligned: bool = False,
) -> Dict[str, Any]:
    snapshot_payload = _read_json(snapshot_path)
    snapshot_meta = _derive_snapshot_metadata(snapshot_payload)
    quote_payload = _read_json(quote_path)

    quote_generated_at_utc = _normalize_iso(quote_payload.get("generated_at_utc"))
    source_snapshot = str(quote_payload.get("source_snapshot") or "").strip()
    source_snapshot_path_matches = source_snapshot == str(snapshot_path)
    alignment_reason = _quote_alignment_reason(
        source_snapshot_path_matches=source_snapshot_path_matches,
        quote_generated_at_utc=quote_generated_at_utc,
        snapshot_generated_at_utc=snapshot_meta.get("generated_at_utc"),
    )
    aligned = alignment_reason == "aligned"
    quote_artifact_digest = _derive_quote_artifact_digest(quote_payload)

    stamped = dict(quote_payload)
    stamped["publication_schema_version"] = PUBLICATION_SCHEMA_VERSION
    stamped["artifact_role"] = "quote_cache"
    stamped["artifact_digest_sha256"] = quote_artifact_digest
    stamped["refresh_run_id"] = str(quote_payload.get("refresh_run_id") or "").strip() or snapshot_meta.get("refresh_run_id")
    stamped["source_snapshot"] = str(snapshot_path)
    stamped["candidate_snapshot_publication_id"] = snapshot_meta["publication_id"]
    stamped["candidate_snapshot_digest_sha256"] = snapshot_meta["artifact_digest_sha256"]
    stamped["candidate_snapshot_generated_at_utc"] = snapshot_meta["generated_at_utc"]
    stamped["publication_binding_status"] = "aligned" if aligned else "unbound"
    stamped["publication_binding_reason"] = alignment_reason

    if aligned:
        stamped["publication_id"] = snapshot_meta["publication_id"]
        stamped["source_snapshot_publication_id"] = snapshot_meta["publication_id"]
        stamped["source_snapshot_digest_sha256"] = snapshot_meta["artifact_digest_sha256"]
        stamped["source_snapshot_generated_at_utc"] = snapshot_meta["generated_at_utc"]
    else:
        stamped["publication_id"] = None
        stamped["source_snapshot_publication_id"] = None
        stamped["source_snapshot_digest_sha256"] = None
        stamped["source_snapshot_generated_at_utc"] = None

    _write_json(quote_path, stamped)

    if failures_path is not None and failures_path.exists():
        failures_payload = _read_json(failures_path)
        failures_payload["publication_schema_version"] = PUBLICATION_SCHEMA_VERSION
        failures_payload["artifact_role"] = "quote_cache_failures"
        failures_payload["refresh_run_id"] = stamped.get("refresh_run_id")
        failures_payload["publication_id"] = stamped.get("publication_id")
        failures_payload["source_snapshot_publication_id"] = stamped.get("source_snapshot_publication_id")
        failures_payload["publication_binding_status"] = stamped.get("publication_binding_status")
        failures_payload["publication_binding_reason"] = stamped.get("publication_binding_reason")
        _write_json(failures_path, failures_payload)

    if require_aligned and not aligned:
        raise RuntimeError(
            "Quote publication alignment failed after quote-cache build: "
            f"reason={alignment_reason}; snapshot_publication_id={snapshot_meta['publication_id']}"
        )

    return {
        "snapshot": snapshot_meta,
        "quote": {
            "generated_at_utc": quote_generated_at_utc,
            "artifact_digest_sha256": quote_artifact_digest,
            "publication_id": stamped.get("publication_id"),
            "source_snapshot_publication_id": stamped.get("source_snapshot_publication_id"),
            "refresh_run_id": stamped.get("refresh_run_id"),
            "publication_binding_status": stamped.get("publication_binding_status"),
            "publication_binding_reason": stamped.get("publication_binding_reason"),
            "source_snapshot_path_matches": source_snapshot_path_matches,
        },
    }


def stamp_active_snapshot_and_quote_artifacts(
    *,
    output_path: Path,
    failures_path: Path | None,
    snapshot_path: Path | None = None,
    require_aligned: bool = False,
) -> Dict[str, Any]:
    resolved_snapshot = snapshot_path or Path(__file__).resolve().parents[2] / "uf_snapshot.json"
    snapshot_meta = stamp_snapshot_artifact(resolved_snapshot)
    quote_meta = stamp_quote_artifact(
        snapshot_path=resolved_snapshot,
        quote_path=output_path,
        failures_path=failures_path,
        require_aligned=require_aligned,
    )
    return {
        "snapshot": snapshot_meta,
        "quote": quote_meta["quote"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", default=str(Path(__file__).resolve().parents[2] / "uf_snapshot.json"))
    parser.add_argument("--quote", default=str(Path(__file__).resolve().parents[2] / "web" / "data" / "screener-quote-cache.json"))
    parser.add_argument("--failures", default=str(Path(__file__).resolve().parents[2] / "web" / "data" / "screener-quote-cache.failures.json"))
    parser.add_argument("--require-aligned", action="store_true")
    args = parser.parse_args()

    result = stamp_active_snapshot_and_quote_artifacts(
        output_path=Path(args.quote).resolve(),
        failures_path=Path(args.failures).resolve() if str(args.failures).strip() else None,
        snapshot_path=Path(args.snapshot).resolve(),
        require_aligned=bool(args.require_aligned),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
