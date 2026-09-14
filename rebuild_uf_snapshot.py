"""Authoritative UF snapshot rebuild with immutable generation publication."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import rebuild_uf_snapshot_legacy as _legacy
from snapshot_generation import (
    prepare_and_publish_generation,
    retain_bar_cache_export_without_mutable_snapshot_upload,
)
from snapshot_transport import normalize_snapshot_transport_artifacts


REFRESH_MODE_FULL = _legacy.REFRESH_MODE_FULL
REFRESH_MODE_TARGETED = _legacy.REFRESH_MODE_TARGETED
ACCUMULATE_MIN_BARS = _legacy.ACCUMULATE_MIN_BARS
REPORT_PATH = Path("uf_snapshot_rebuild_report.json")

# While this process rewrites, hides and republishes the bound artifacts, the
# serving container's health check (web/src/lib/runtime-health.ts) cannot see
# artifacts that match the active manifest. The hold names this process so the
# check can verify that a live rebuild owns them; it is removed on every exit
# path of rebuild_snapshot, success or failure.
GENERATION_HOLD_PATH = Path("uf_snapshot_generation.hold.json")
GENERATION_HOLD_SCHEMA = "tfe.snapshot-generation-hold.v1"

_legacy_rebuild_snapshot = _legacy.rebuild_snapshot
_legacy_upload = _legacy._upload_snapshot_to_s3


def _write_private_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    body = (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_report_atomic(report: dict[str, Any]) -> None:
    _write_private_json_atomic(REPORT_PATH, report)


def write_generation_hold(refresh_mode: str) -> dict[str, Any]:
    hold = {
        "schema": GENERATION_HOLD_SCHEMA,
        "pid": os.getpid(),
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "refresh_mode": refresh_mode,
        "run_id": str(os.environ.get("TFE_REFRESH_RUN_ID", "")).strip() or None,
    }
    _write_private_json_atomic(GENERATION_HOLD_PATH, hold)
    print(f"[UF-SNAPSHOT] Generation hold recorded: pid={hold['pid']} mode={refresh_mode}", flush=True)
    return hold


def clear_generation_hold() -> None:
    try:
        GENERATION_HOLD_PATH.unlink()
    except FileNotFoundError:
        return
    print("[UF-SNAPSHOT] Generation hold released.", flush=True)


def _write_normalized_envelope(rows: list[dict[str, Any]], generated_at_utc: str) -> None:
    _legacy._save_snapshot_envelope(rows, generated_at_utc=generated_at_utc)


def _record_publication_failure(error: Exception) -> None:
    try:
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    except Exception:
        report = {}
    if not isinstance(report, dict):
        report = {}
    report.update(
        status="publication_failed",
        publication_schema="tfe.snapshot-generation.v1",
        publication_error=f"{type(error).__name__}: {error}",
    )
    _write_report_atomic(report)


def rebuild_snapshot(
    refresh_mode: str = REFRESH_MODE_FULL,
    force_refresh_universe: bool = False,
    years_history: int = 5,
) -> dict[str, Any]:
    publication: dict[str, Any] = {}
    transport_normalization: dict[str, Any] = {}

    def publish_generation() -> None:
        nonlocal publication, transport_normalization
        retain_bar_cache_export_without_mutable_snapshot_upload(_legacy_upload)
        try:
            transport_normalization = normalize_snapshot_transport_artifacts(
                envelope_writer=_write_normalized_envelope
            )
            publication = prepare_and_publish_generation()
        except Exception as error:
            _record_publication_failure(error)
            raise

    write_generation_hold(refresh_mode)
    previous_upload = _legacy._upload_snapshot_to_s3
    _legacy._upload_snapshot_to_s3 = publish_generation
    try:
        report = _legacy_rebuild_snapshot(
            refresh_mode=refresh_mode,
            force_refresh_universe=force_refresh_universe,
            years_history=years_history,
        )
        if report.get("status") == "ok":
            if not publication:
                error = RuntimeError("snapshot generation completed without an immutable publication receipt")
                _record_publication_failure(error)
                raise error
            report.update(
                snapshot_publication_id=publication["publication_id"],
                snapshot_generation_id=publication["generation_id"],
                snapshot_payload_digest_sha256=publication["snapshot_payload_digest_sha256"],
                publication_schema="tfe.snapshot-generation.v1",
                transport_normalization=transport_normalization,
            )
        _write_report_atomic(report)
        return report
    finally:
        _legacy._upload_snapshot_to_s3 = previous_upload
        clear_generation_hold()


def main() -> int:
    previous_rebuild = _legacy.rebuild_snapshot
    _legacy.rebuild_snapshot = rebuild_snapshot
    try:
        _legacy.main()
    finally:
        _legacy.rebuild_snapshot = previous_rebuild
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
