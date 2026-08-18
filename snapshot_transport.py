"""Strict JSON transport normalization for UF snapshot publication artifacts."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Callable


EnvelopeWriter = Callable[[list[dict[str, Any]], str], None]


def _json_private_atomic(path: Path, payload: object, *, pretty: bool) -> None:
    body = json.dumps(
        payload,
        indent=2 if pretty else None,
        sort_keys=True,
        separators=None if pretty else (",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(body + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        if temporary.exists():
            temporary.unlink()


def _normalize_nonfinite_values(value: object, *, path: str) -> tuple[object, list[str]]:
    if isinstance(value, float) and not math.isfinite(value):
        return None, [path]
    if isinstance(value, list):
        normalized: list[object] = []
        locations: list[str] = []
        for index, item in enumerate(value):
            clean, found = _normalize_nonfinite_values(item, path=f"{path}[{index}]")
            normalized.append(clean)
            locations.extend(found)
        return normalized, locations
    if isinstance(value, dict):
        normalized_dict: dict[str, object] = {}
        locations = []
        for key, item in value.items():
            clean, found = _normalize_nonfinite_values(item, path=f"{path}.{key}")
            normalized_dict[str(key)] = clean
            locations.extend(found)
        return normalized_dict, locations
    return value, []


def normalize_snapshot_transport_artifacts(
    *,
    envelope_writer: EnvelopeWriter,
    snapshot_path: Path = Path("uf_snapshot.json"),
    report_path: Path = Path("uf_snapshot_rebuild_report.json"),
) -> dict[str, Any]:
    """Map non-finite missing values to null and rebind the encrypted payload."""
    snapshot_raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if not isinstance(snapshot_raw, dict):
        raise ValueError("snapshot transport artifact must be one JSON object")
    normalized, locations = _normalize_nonfinite_values(snapshot_raw, path="root")
    if not isinstance(normalized, dict):
        raise ValueError("normalized snapshot transport artifact must be one JSON object")
    rows = normalized.get("rows")
    generated_at = str(normalized.get("generated_at_utc") or "").strip()
    if not isinstance(rows, list) or not rows or not generated_at:
        raise ValueError("snapshot transport artifact requires generated_at_utc and non-empty rows")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("snapshot transport rows must be JSON objects")

    # Prove strict serialization before replacing either bound representation.
    json.dumps(normalized, allow_nan=False)
    typed_rows = [dict(row) for row in rows]
    if locations:
        envelope_writer(typed_rows, generated_at)
    _json_private_atomic(snapshot_path, normalized, pretty=False)

    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise ValueError("snapshot rebuild report must be one JSON object")
    transport_receipt = {
        "schema": "tfe.snapshot-transport-normalization.v1",
        "nonfinite_values_normalized_to_null": len(locations),
        "locations": locations,
    }
    report["transport_normalization"] = transport_receipt
    _json_private_atomic(report_path, report, pretty=True)
    return transport_receipt
