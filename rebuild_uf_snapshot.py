"""Authoritative UF snapshot rebuild with immutable generation publication."""

from __future__ import annotations

import json
import os
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

_legacy_rebuild_snapshot = _legacy.rebuild_snapshot
_legacy_upload = _legacy._upload_snapshot_to_s3


def _write_report_atomic(report: dict[str, Any]) -> None:
    temporary = REPORT_PATH.with_name(f".{REPORT_PATH.name}.{os.getpid()}.tmp")
    body = (json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, REPORT_PATH)
        os.chmod(REPORT_PATH, 0o600)
    finally:
        if temporary.exists():
            temporary.unlink()


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

    previous_upload = _legacy._upload_snapshot_to_s3
    _legacy._upload_snapshot_to_s3 = publish_generation
    try:
        report = _legacy_rebuild_snapshot(
            refresh_mode=refresh_mode,
            force_refresh_universe=force_refresh_universe,
            years_history=years_history,
        )
    finally:
        _legacy._upload_snapshot_to_s3 = previous_upload

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
