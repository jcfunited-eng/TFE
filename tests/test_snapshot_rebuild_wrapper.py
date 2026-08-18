from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path

import pytest


legacy = types.ModuleType("rebuild_uf_snapshot_legacy")
legacy.REFRESH_MODE_FULL = "full_universe"
legacy.REFRESH_MODE_TARGETED = "targeted_pfsc"
legacy.ACCUMULATE_MIN_BARS = 514
legacy._upload_snapshot_to_s3 = lambda: None
legacy.rebuild_snapshot = lambda **kwargs: {}
legacy.main = lambda: None
previous_legacy = sys.modules.get("rebuild_uf_snapshot_legacy")
previous_wrapper = sys.modules.get("rebuild_uf_snapshot")
try:
    sys.modules["rebuild_uf_snapshot_legacy"] = legacy
    sys.modules.pop("rebuild_uf_snapshot", None)
    rebuild_uf_snapshot = importlib.import_module("rebuild_uf_snapshot")
finally:
    sys.modules.pop("rebuild_uf_snapshot", None)
    if previous_wrapper is not None:
        sys.modules["rebuild_uf_snapshot"] = previous_wrapper
    if previous_legacy is None:
        sys.modules.pop("rebuild_uf_snapshot_legacy", None)
    else:
        sys.modules["rebuild_uf_snapshot_legacy"] = previous_legacy


def source_report() -> dict[str, object]:
    return {
        "status": "ok",
        "rows_written": 1,
        "generated_at_utc": "2026-08-18T00:00:00Z",
    }


def fake_legacy_rebuild(**kwargs: object) -> dict[str, object]:
    del kwargs
    Path("uf_snapshot.json").write_text('{"rows":[{"ticker":"A"}],"generated_at_utc":"2026-08-18T00:00:00Z"}', encoding="utf-8")
    Path("uf_snapshot.ses.json").write_text('{"encrypted":true}', encoding="utf-8")
    Path("uf_snapshot_rebuild_report.json").write_text(json.dumps(source_report()), encoding="utf-8")
    rebuild_uf_snapshot._legacy._upload_snapshot_to_s3()
    return source_report()


def receipt() -> dict[str, str]:
    return {
        "publication_id": "snapshot_pub_v2_test",
        "generation_id": "snapshot_pub_v2_test",
        "snapshot_payload_digest_sha256": "a" * 64,
        "manifest_key": "runtime-refresh-checkpoints/generations/snapshot_pub_v2_test/manifest.json",
        "manifest_sha256": "b" * 64,
    }


def test_wrapper_disables_mutable_upload_and_returns_generation_receipt(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    mutable_visibility: list[bool] = []

    def bar_cache_lane() -> None:
        mutable_visibility.append(Path("uf_snapshot.json").exists())

    def publish() -> dict[str, str]:
        assert Path("uf_snapshot.json").exists()
        return receipt()

    monkeypatch.setattr(rebuild_uf_snapshot, "_legacy_rebuild_snapshot", fake_legacy_rebuild)
    monkeypatch.setattr(rebuild_uf_snapshot, "_legacy_upload", bar_cache_lane)
    monkeypatch.setattr(rebuild_uf_snapshot, "prepare_and_publish_generation", publish)

    report = rebuild_uf_snapshot.rebuild_snapshot()

    assert mutable_visibility == [False]
    assert report["snapshot_generation_id"] == "snapshot_pub_v2_test"
    persisted = json.loads(Path("uf_snapshot_rebuild_report.json").read_text(encoding="utf-8"))
    assert persisted["snapshot_publication_id"] == "snapshot_pub_v2_test"
    assert "snapshot_manifest_sha256" not in persisted


def test_wrapper_records_publication_failure_and_raises(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(rebuild_uf_snapshot, "_legacy_rebuild_snapshot", fake_legacy_rebuild)
    monkeypatch.setattr(rebuild_uf_snapshot, "_legacy_upload", lambda: None)

    def fail_publish() -> dict[str, str]:
        raise RuntimeError("S3 unavailable")

    monkeypatch.setattr(rebuild_uf_snapshot, "prepare_and_publish_generation", fail_publish)

    with pytest.raises(RuntimeError, match="S3 unavailable"):
        rebuild_uf_snapshot.rebuild_snapshot()

    persisted = json.loads(Path("uf_snapshot_rebuild_report.json").read_text(encoding="utf-8"))
    assert persisted["status"] == "publication_failed"
    assert "S3 unavailable" in persisted["publication_error"]
